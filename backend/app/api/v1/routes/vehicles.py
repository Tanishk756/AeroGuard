"""Stage S4 Vehicle Management REST API Routes.

Provides Vehicle assembly CRUD, deterministic hardware compatibility validation,
and seamless "Simulate This Vehicle" scenario generation.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.models.simulation_platform import PersistentSimulationScenario
from app.schemas.hardware_registry import (
    VehicleCompatibilityDiagnostic,
    VehicleCreate,
    VehicleResponse,
)
from app.schemas.simulation_platform import SimulationScenarioResponse
from app.simulation.core.compatibility import HardwareCompatibilityEngine
from app.simulation.core.vehicle_calculator import VehicleCalculator
from app.simulation.core.vehicle_compiler import VehicleAssemblyCompiler, CompiledVehicleModel
from app.simulation.core.sdf_generator import GazeboVehicleGenerator
from app.core.telemetry import (
    VEHICLE_CREATION_TOTAL,
    VEHICLE_COMPILE_TOTAL,
    VEHICLE_COMPILE_FAILURES_TOTAL,
)

router = APIRouter(prefix="/vehicles", tags=["vehicles"])


def _fetch_and_validate_hardware(payload: VehicleCreate, db: Session):
    """Utility to fetch all component entities referenced in vehicle payload."""
    frame = db.get(PersistentHardwareComponent, payload.frame_id)
    motor = db.get(PersistentHardwareComponent, payload.motor_id)
    esc = db.get(PersistentHardwareComponent, payload.esc_id)
    propeller = db.get(PersistentHardwareComponent, payload.propeller_id)
    battery = db.get(PersistentHardwareComponent, payload.battery_id)
    fc = db.get(PersistentHardwareComponent, payload.flight_controller_id)
    gps = db.get(PersistentHardwareComponent, payload.gps_id) if payload.gps_id else None

    missing = []
    if not frame: missing.append("frame_id")
    if not motor: missing.append("motor_id")
    if not esc: missing.append("esc_id")
    if not propeller: missing.append("propeller_id")
    if not battery: missing.append("battery_id")
    if not fc: missing.append("flight_controller_id")

    if missing:
        raise HTTPException(status_code=400, detail=f"Referenced hardware component IDs not found: {', '.join(missing)}")

    return frame, motor, esc, propeller, battery, fc, gps


def _build_vehicle_response(vehicle: PersistentVehicle, db: Session) -> VehicleResponse:
    """Build response model including compatibility diagnostic."""
    diag = HardwareCompatibilityEngine.validate_vehicle_assembly(
        vehicle.frame, vehicle.motor, vehicle.esc, vehicle.propeller, vehicle.battery, vehicle.flight_controller, vehicle.gps, vehicle_id=vehicle.id
    )

    return VehicleResponse(
        id=vehicle.id,
        project_id=vehicle.project_id,
        name=vehicle.name,
        vehicle_type=vehicle.vehicle_type,
        frame_id=vehicle.frame_id,
        motor_id=vehicle.motor_id,
        esc_id=vehicle.esc_id,
        propeller_id=vehicle.propeller_id,
        battery_id=vehicle.battery_id,
        flight_controller_id=vehicle.flight_controller_id,
        gps_id=vehicle.gps_id,
        total_mass_g=vehicle.total_mass_g,
        estimated_hover_throttle=vehicle.estimated_hover_throttle,
        thrust_to_weight_ratio=vehicle.thrust_to_weight_ratio,
        compatibility=diag,
        created_at=vehicle.created_at,
        updated_at=vehicle.updated_at,
    )


@router.get("", response_model=List[VehicleResponse])
def list_vehicles(project_id: Optional[str] = None, db: Session = Depends(get_db)):
    """GET /api/v1/vehicles - List assembled vehicle configurations."""
    query = select(PersistentVehicle)
    if project_id:
        query = query.where(PersistentVehicle.project_id == project_id)
    vehicles = db.scalars(query.order_by(PersistentVehicle.created_at.desc())).all()
    return [_build_vehicle_response(v, db) for v in vehicles]


@router.get("/{vehicle_id}", response_model=VehicleResponse)
def get_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/vehicles/{id} - Get vehicle configuration by ID."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")
    return _build_vehicle_response(vehicle, db)


@router.post("", response_model=VehicleResponse, status_code=status.HTTP_201_CREATED)
def create_vehicle(payload: VehicleCreate, db: Session = Depends(get_db)):
    """POST /api/v1/vehicles - Assemble new vehicle digital twin configuration."""
    frame, motor, esc, propeller, battery, fc, gps = _fetch_and_validate_hardware(payload, db)

    # Validate compatibility before creation
    diag = HardwareCompatibilityEngine.validate_vehicle_assembly(frame, motor, esc, propeller, battery, fc, gps)
    if not diag.compatible:
        raise HTTPException(
            status_code=422,
            detail=f"Incompatible vehicle hardware assembly: {'; '.join(diag.errors)}",
        )

    metrics = VehicleCalculator.calculate_vehicle_metrics(frame, motor, esc, propeller, battery, fc, gps)

    vehicle = PersistentVehicle(
        id=str(uuid.uuid4()),
        project_id=payload.project_id,
        name=payload.name,
        vehicle_type=payload.vehicle_type,
        frame_id=payload.frame_id,
        motor_id=payload.motor_id,
        esc_id=payload.esc_id,
        propeller_id=payload.propeller_id,
        battery_id=payload.battery_id,
        flight_controller_id=payload.flight_controller_id,
        gps_id=payload.gps_id,
        total_mass_g=metrics["total_mass_g"],
        estimated_hover_throttle=metrics["estimated_hover_throttle"],
        thrust_to_weight_ratio=metrics["thrust_to_weight_ratio"],
    )

    db.add(vehicle)
    db.commit()
    db.refresh(vehicle)
    VEHICLE_CREATION_TOTAL.inc()

    return _build_vehicle_response(vehicle, db)


@router.post("/{vehicle_id}/validate", response_model=VehicleCompatibilityDiagnostic)
def validate_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/vehicles/{id}/validate - Run deterministic compatibility validation."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    return HardwareCompatibilityEngine.validate_vehicle_assembly(
        vehicle.frame, vehicle.motor, vehicle.esc, vehicle.propeller, vehicle.battery, vehicle.flight_controller, vehicle.gps, vehicle_id=vehicle.id
    )


@router.post("/{vehicle_id}/compile", response_model=CompiledVehicleModel)
def compile_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/vehicles/{id}/compile - Compile persistent vehicle into deterministic physical model."""
    VEHICLE_COMPILE_TOTAL.inc()
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        VEHICLE_COMPILE_FAILURES_TOTAL.inc()
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    return VehicleAssemblyCompiler.compile_vehicle(vehicle)


@router.post("/{vehicle_id}/sdf")
def generate_vehicle_sdf(vehicle_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/vehicles/{id}/sdf - Generate Gazebo Harmonic SDF XML model."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    compiled = VehicleAssemblyCompiler.compile_vehicle(vehicle)
    sdf_xml, sdf_hash = GazeboVehicleGenerator.generate_sdf(compiled)

    return {
        "vehicle_id": vehicle_id,
        "compiled_model_hash": compiled.compiled_model_hash,
        "artifact_hash": sdf_hash,
        "sdf_xml": sdf_xml,
    }


@router.post("/{vehicle_id}/simulate", response_model=SimulationScenarioResponse)
def simulate_vehicle(vehicle_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/vehicles/{id}/simulate - Launch simulation scenario derived from vehicle specs."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    diag = HardwareCompatibilityEngine.validate_vehicle_assembly(
        vehicle.frame, vehicle.motor, vehicle.esc, vehicle.propeller, vehicle.battery, vehicle.flight_controller, vehicle.gps, vehicle_id=vehicle.id
    )
    if not diag.compatible:
        raise HTTPException(status_code=400, detail=f"Cannot simulate incompatible vehicle: {'; '.join(diag.errors)}")

    # Create simulation scenario tied to vehicle digital twin
    scenario = PersistentSimulationScenario(
        id=str(uuid.uuid4()),
        name=f"Digital Twin Simulation: {vehicle.name}",
        configuration_version=1,
        configuration_metadata={
            "simulator_type": "GAZEBO",
            "autopilot_type": "ARDUPILOT",
            "world_name": "shapes.sdf",
            "vehicle_config": {
                "vehicle_id": vehicle.id,
                "vehicle_type": vehicle.vehicle_type,
                "total_mass_g": vehicle.total_mass_g,
                "hover_throttle": vehicle.estimated_hover_throttle,
            },
        },
    )

    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    return SimulationScenarioResponse(
        id=scenario.id,
        name=scenario.name,
        simulator_type="GAZEBO",
        autopilot_type="ARDUPILOT",
        world_name="shapes.sdf",
        vehicle_config=scenario.configuration_metadata.get("vehicle_config"),
        configuration_metadata=scenario.configuration_metadata,
        created_at=scenario.created_at,
    )
