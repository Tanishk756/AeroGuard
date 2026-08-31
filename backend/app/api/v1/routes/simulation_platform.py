"""Stage S1 Simulation Platform REST API and WebSocket Telemetry Stream Routes.

Exposes endpoints for system capability diagnostics, scenario management, simulation run lifecycle,
and WebSocket real-time normalized VehicleState streaming.
"""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.simulation_platform import (
    PersistentSimulationRun,
    PersistentSimulationScenario,
)
from app.schemas.simulation_platform import (
    CapabilityDiagnosticResponse,
    SimulationRunCreate,
    SimulationRunResponse,
    SimulationRunStatus,
    SimulationScenarioCreate,
    SimulationScenarioResponse,
    SimulationScenarioSpec,
)
from app.simulation.core.orchestrator import SimulationOrchestrator
from app.simulation.core.process_manager import SimulationProcessManager

router = APIRouter(prefix="/simulation", tags=["Simulation Platform"])


@router.get("/capabilities", response_model=CapabilityDiagnosticResponse)
def get_simulation_capabilities() -> CapabilityDiagnosticResponse:
    """Return environment diagnostic reporting availability of Gazebo, ArduPilot SITL, and MAVLink."""
    return SimulationProcessManager.get_capabilities()


@router.post("/scenarios", response_model=SimulationScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(payload: SimulationScenarioCreate, db: Session = Depends(get_db)) -> PersistentSimulationScenario:
    """Create a persistent simulation scenario definition."""
    scenario_id = f"scen-{uuid.uuid4().hex[:8]}"
    spec = SimulationScenarioSpec(
        scenario_id=scenario_id,
        name=payload.name,
        simulator_type=payload.simulator_type,
        autopilot_type=payload.autopilot_type,
        world_name=payload.world_name,
        random_seed=payload.random_seed,
    )
    if payload.vehicle_config:
        spec.vehicle_config = payload.vehicle_config

    db_scenario = PersistentSimulationScenario(
        id=scenario_id,
        name=payload.name,
        configuration_version=1,
        configuration_metadata=spec.model_dump(mode="json"),
    )
    db.add(db_scenario)
    db.commit()
    db.refresh(db_scenario)
    return db_scenario


@router.get("/scenarios", response_model=List[SimulationScenarioResponse])
def list_scenarios(db: Session = Depends(get_db)) -> List[PersistentSimulationScenario]:
    """List all configured simulation scenarios."""
    return list(db.scalars(select(PersistentSimulationScenario).order_by(PersistentSimulationScenario.created_at.desc())).all())


@router.post("/runs", response_model=SimulationRunResponse, status_code=status.HTTP_201_CREATED)
async def create_run(payload: SimulationRunCreate, db: Session = Depends(get_db)) -> PersistentSimulationRun:
    """Create a simulation run instance for a scenario."""
    scenario = db.get(PersistentSimulationScenario, payload.scenario_id)
    if not scenario:
        raise HTTPException(status_code=404, detail=f"Scenario '{payload.scenario_id}' not found")

    run_id = f"run-{uuid.uuid4().hex[:8]}"
    spec = SimulationScenarioSpec.model_validate(scenario.configuration_metadata)
    
    await SimulationOrchestrator.create_run(run_id, spec)

    db_run = PersistentSimulationRun(
        id=run_id,
        scenario_id=scenario.id,
        status=SimulationRunStatus.CREATED.value,
    )
    db.add(db_run)
    db.commit()
    db.refresh(db_run)
    return db_run


@router.post("/runs/{run_id}/start", response_model=SimulationRunResponse)
async def start_run(run_id: str, db: Session = Depends(get_db)) -> PersistentSimulationRun:
    """Start simulation run physics and autopilot execution."""
    db_run = db.get(PersistentSimulationRun, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    success = await SimulationOrchestrator.start_run(run_id)
    if not success:
        db_run.status = SimulationRunStatus.FAILED.value
        db.commit()
        raise HTTPException(status_code=500, detail="Failed to start simulation run")

    db_run.status = SimulationRunStatus.RUNNING.value
    db.commit()
    db.refresh(db_run)
    return db_run


@router.post("/runs/{run_id}/pause", response_model=SimulationRunResponse)
async def pause_run(run_id: str, db: Session = Depends(get_db)) -> PersistentSimulationRun:
    """Pause simulation run physics."""
    db_run = db.get(PersistentSimulationRun, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    await SimulationOrchestrator.pause_run(run_id)
    db_run.status = SimulationRunStatus.PAUSED.value
    db.commit()
    db.refresh(db_run)
    return db_run


@router.post("/runs/{run_id}/resume", response_model=SimulationRunResponse)
async def resume_run(run_id: str, db: Session = Depends(get_db)) -> PersistentSimulationRun:
    """Resume paused simulation run physics."""
    db_run = db.get(PersistentSimulationRun, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    await SimulationOrchestrator.resume_run(run_id)
    db_run.status = SimulationRunStatus.RUNNING.value
    db.commit()
    db.refresh(db_run)
    return db_run


@router.post("/runs/{run_id}/stop", response_model=SimulationRunResponse)
async def stop_run(run_id: str, db: Session = Depends(get_db)) -> PersistentSimulationRun:
    """Stop simulation run and terminate processes."""
    db_run = db.get(PersistentSimulationRun, run_id)
    if not db_run:
        raise HTTPException(status_code=404, detail=f"Run '{run_id}' not found")

    session = SimulationOrchestrator.get_run(run_id)
    if session:
        db_run.telemetry_count = len(session.telemetry_history)

    await SimulationOrchestrator.stop_run(run_id)
    db_run.status = SimulationRunStatus.STOPPED.value
    db.commit()
    db.refresh(db_run)
    return db_run


@router.get("/runs/{run_id}/replay")
def get_run_replay(run_id: str) -> dict:
    """Fetch recorded VehicleState telemetry history for offline run replay."""
    session = SimulationOrchestrator.get_run(run_id)
    if not session:
        return {"run_id": run_id, "telemetry_count": 0, "samples": []}

    samples = [sample.model_dump() for sample in session.telemetry_history]
    return {
        "run_id": run_id,
        "telemetry_count": len(samples),
        "samples": samples,
    }


@router.websocket("/runs/{run_id}/telemetry")
async def websocket_run_telemetry(websocket: WebSocket, run_id: str) -> None:
    """WebSocket stream broadcasting real-time normalized VehicleState vectors."""
    await websocket.accept()
    session = SimulationOrchestrator.get_run(run_id)
    if not session:
        await websocket.close(code=4004, reason="Run session not found")
        return

    session.active_websockets.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        session.active_websockets.discard(websocket)
