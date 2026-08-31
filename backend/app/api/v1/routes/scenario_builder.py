"""Stage S6 Scenario Builder & Digital Twin World REST API Routes.

Provides versioned digital-twin scenario creation, validation, duplication, export, and import endpoints.
"""

import hashlib
import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.scenario_world import PersistentScenarioEntity, PersistentSimulationWorld, PersistentWorldObject
from app.models.hardware_registry import PersistentVehicle
from app.schemas.scenario_world import (
    ScenarioCreate,
    ScenarioResponse,
    ScenarioValidationDiagnostic,
    ScenarioExportPackage,
    SimulationWorldSpec,
    WorldObjectSpec,
)
from app.simulation.core.scenario_validator import ScenarioValidationEngine
from app.simulation.core.world_generator import GazeboWorldGenerator
from app.core.telemetry import SCENARIOS_CREATED_TOTAL

router = APIRouter(prefix="/scenario-builder", tags=["Scenario Builder"])


def _to_scenario_response(scen: PersistentScenarioEntity) -> ScenarioResponse:
    return ScenarioResponse(
        id=scen.id,
        project_id=scen.project_id,
        name=scen.name,
        description=scen.description,
        vehicle_id=scen.vehicle_id,
        simulator=scen.simulator,
        autopilot=scen.autopilot,
        world_id=scen.world_id,
        environment_config=scen.environment_config_json,
        physics_config=scen.physics_config_json,
        weather_config=scen.weather_config_json,
        spawn_config=scen.spawn_config_json,
        random_seed=scen.random_seed,
        configuration_version=scen.configuration_version,
        created_at=scen.created_at.isoformat(),
        updated_at=scen.updated_at.isoformat(),
    )


@router.post("", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario_builder(payload: ScenarioCreate, db: Session = Depends(get_db)):
    """POST /api/v1/scenario-builder - Create a new first-class versioned digital twin scenario."""
    diag = ScenarioValidationEngine.validate_scenario_payload(payload, db)
    if not diag.valid:
        raise HTTPException(status_code=400, detail={"message": "Scenario validation failed", "errors": diag.errors})

    SCENARIOS_CREATED_TOTAL.inc()
    scen_id = f"scen-{uuid.uuid4().hex[:8]}"
    entity = PersistentScenarioEntity(
        id=scen_id,
        project_id=payload.project_id,
        name=payload.name,
        description=payload.description,
        vehicle_id=payload.vehicle_id,
        simulator=payload.simulator,
        autopilot=payload.autopilot,
        world_id=payload.world_id,
        environment_config_json=payload.environment_config.model_dump(),
        physics_config_json=payload.physics_config.model_dump(),
        weather_config_json=payload.weather_config.model_dump(),
        spawn_config_json=payload.spawn_config.model_dump(),
        random_seed=payload.random_seed,
        configuration_version=1,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return _to_scenario_response(entity)


@router.get("", response_model=List[ScenarioResponse])
def list_scenario_builder(db: Session = Depends(get_db)):
    """GET /api/v1/scenario-builder - List registered digital twin scenarios."""
    scenarios = db.scalars(select(PersistentScenarioEntity)).all()
    return [_to_scenario_response(s) for s in scenarios]


@router.post("/validate", response_model=ScenarioValidationDiagnostic)
def validate_scenario_builder(payload: ScenarioCreate, db: Session = Depends(get_db)):
    """POST /api/v1/scenario-builder/validate - Validate scenario configuration without persisting."""
    return ScenarioValidationEngine.validate_scenario_payload(payload, db)


@router.post("/{scenario_id}/duplicate", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def duplicate_scenario_builder(scenario_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/scenario-builder/{id}/duplicate - Duplicate an existing scenario with version increment."""
    original = db.get(PersistentScenarioEntity, scenario_id)
    if not original:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    new_id = f"scen-{uuid.uuid4().hex[:8]}"
    duplicated = PersistentScenarioEntity(
        id=new_id,
        project_id=original.project_id,
        name=f"{original.name} (Copy)",
        description=original.description,
        vehicle_id=original.vehicle_id,
        simulator=original.simulator,
        autopilot=original.autopilot,
        world_id=original.world_id,
        environment_config_json=original.environment_config_json,
        physics_config_json=original.physics_config_json,
        weather_config_json=original.weather_config_json,
        spawn_config_json=original.spawn_config_json,
        random_seed=original.random_seed,
        configuration_version=1,
    )
    db.add(duplicated)
    db.commit()
    db.refresh(duplicated)
    return _to_scenario_response(duplicated)


@router.post("/{scenario_id}/export", response_model=ScenarioExportPackage)
def export_scenario_builder(scenario_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/scenario-builder/{id}/export - Export scenario package to aeroguard-scenario.json format."""
    scen = db.get(PersistentScenarioEntity, scenario_id)
    if not scen:
        raise HTTPException(status_code=404, detail=f"Scenario '{scenario_id}' not found")

    world = db.get(PersistentSimulationWorld, scen.world_id)
    world_objects = [
        WorldObjectSpec(
            id=o.id,
            object_type=o.object_type,
            position=o.position_json,
            orientation=o.orientation_json,
            scale=o.scale_json,
            collision_enabled=o.collision_enabled,
            visual_enabled=o.visual_enabled,
        )
        for o in (world.objects if world else [])
    ]
    world_spec = SimulationWorldSpec(
        id=world.id if world else "world-default",
        project_id=world.project_id if world else "proj-default-01",
        name=world.name if world else "Default World",
        world_type=world.world_type if world else "FLAT_GROUND",
        description=world.description if world else None,
        objects=world_objects,
    )

    scen_resp = _to_scenario_response(scen)
    pkg_str = scen_resp.model_dump_json() + world_spec.model_dump_json()
    manifest_hash = hashlib.sha256(pkg_str.encode("utf-8")).hexdigest()

    return ScenarioExportPackage(
        scenario=scen_resp,
        vehicle_reference_id=scen.vehicle_id,
        world_spec=world_spec,
        hash_manifest={"scenario_hash": manifest_hash},
    )


@router.post("/import", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def import_scenario_builder(package: ScenarioExportPackage, db: Session = Depends(get_db)):
    """POST /api/v1/scenario-builder/import - Securely import an aeroguard-scenario.json package."""
    vehicle = db.get(PersistentVehicle, package.vehicle_reference_id)
    if not vehicle:
        raise HTTPException(status_code=400, detail=f"Import vehicle reference '{package.vehicle_reference_id}' not found")

    world = db.get(PersistentSimulationWorld, package.world_spec.id) if package.world_spec.id else None
    if not world:
        world = PersistentSimulationWorld(
            id=package.world_spec.id or f"world-{uuid.uuid4().hex[:8]}",
            project_id=package.world_spec.project_id,
            name=package.world_spec.name,
            world_type=package.world_spec.world_type,
            description=package.world_spec.description,
        )
        db.add(world)
        db.commit()

    scen_id = f"scen-{uuid.uuid4().hex[:8]}"
    imported = PersistentScenarioEntity(
        id=scen_id,
        project_id=package.scenario.project_id,
        name=package.scenario.name,
        description=package.scenario.description,
        vehicle_id=package.vehicle_reference_id,
        simulator=package.scenario.simulator,
        autopilot=package.scenario.autopilot,
        world_id=world.id,
        environment_config_json=package.scenario.environment_config.model_dump(),
        physics_config_json=package.scenario.physics_config.model_dump(),
        weather_config_json=package.scenario.weather_config.model_dump(),
        spawn_config_json=package.scenario.spawn_config.model_dump(),
        random_seed=package.scenario.random_seed,
        configuration_version=package.scenario.configuration_version,
    )
    db.add(imported)
    db.commit()
    db.refresh(imported)
    return _to_scenario_response(imported)
