"""Stage S12 Simulation Orchestration & Replay REST Endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.schemas.simulation_snapshot import (
    SimulationRecordingMetadata,
    SimulationReplayState,
    SimulationSnapshot,
)
from app.simulation.core.multi_vehicle_orchestrator import MultiVehicleSimulationOrchestrator
from app.simulation.core.scenario_regression_suite import ScenarioRegressionSuite
from app.simulation.core.swarm_replay_engine import SwarmReplayEngine

router = APIRouter(prefix="/simulation/orchestrator", tags=["simulation_orchestrator"])

# Global singleton orchestrator & replay engine state for session control
_active_orchestrator: Optional[MultiVehicleSimulationOrchestrator] = None
_active_replay_engine: Optional[SwarmReplayEngine] = None


def get_orchestrator() -> MultiVehicleSimulationOrchestrator:
    """Retrieve or lazy-create active orchestrator."""
    global _active_orchestrator
    if _active_orchestrator is None:
        _active_orchestrator = MultiVehicleSimulationOrchestrator()
    return _active_orchestrator


class InitSimulationRequest(BaseModel):
    scenario_id: str = "default_scenario"
    vehicle_count: int = Field(default=4, ge=1, le=32)
    formation_type: str = "VEE"
    dt_seconds: float = 0.1
    random_seed: int = 42


class StepSimulationRequest(BaseModel):
    count: int = Field(default=1, ge=1, le=1000)


class SeekReplayRequest(BaseModel):
    sim_time_s: Optional[float] = None
    tick_count: Optional[int] = None


@router.post("/init")
def initialize_simulation(req: InitSimulationRequest) -> Dict[str, Any]:
    """Initialize a multi-vehicle simulation run with 1 to 32 vehicles."""
    global _active_orchestrator, _active_replay_engine
    _active_orchestrator = MultiVehicleSimulationOrchestrator(
        scenario_id=req.scenario_id,
        dt_seconds=req.dt_seconds,
        random_seed=req.random_seed,
    )
    vehicle_ids = [f"veh-{i+1:02d}" for i in range(req.vehicle_count)]
    _active_orchestrator.initialize_swarm(vehicle_ids=vehicle_ids)
    _active_replay_engine = SwarmReplayEngine(_active_orchestrator.recorder)

    return {
        "status": "INITIALIZED",
        "scenario_id": req.scenario_id,
        "vehicle_count": req.vehicle_count,
        "dt_seconds": req.dt_seconds,
        "seed": req.random_seed,
    }


@router.post("/start")
def start_simulation() -> Dict[str, Any]:
    """Start live simulation clock and update cycle."""
    orc = get_orchestrator()
    orc.start()
    return {"status": "RUNNING", "clock_mode": orc.clock.mode}


@router.post("/pause")
def pause_simulation() -> Dict[str, Any]:
    """Pause live simulation execution."""
    orc = get_orchestrator()
    orc.pause()
    return {"status": "PAUSED", "sim_time_seconds": orc.clock.sim_time_seconds}


@router.post("/step", response_model=SimulationSnapshot)
def step_simulation(req: StepSimulationRequest) -> SimulationSnapshot:
    """Advance simulation clock by N single steps."""
    orc = get_orchestrator()
    return orc.step(req.count)


@router.get("/snapshot", response_model=SimulationSnapshot)
def get_latest_snapshot() -> SimulationSnapshot:
    """Retrieve the latest versioned simulation snapshot."""
    orc = get_orchestrator()
    return orc.get_latest_snapshot()


@router.get("/recording/metadata", response_model=SimulationRecordingMetadata)
def get_recording_metadata() -> SimulationRecordingMetadata:
    """Retrieve metadata summary of recorded simulation session."""
    orc = get_orchestrator()
    return orc.recorder.get_metadata()


# Replay endpoints
@router.post("/replay/load")
def load_replay() -> SimulationReplayState:
    """Load active recording into replay engine."""
    global _active_replay_engine
    orc = get_orchestrator()
    _active_replay_engine = SwarmReplayEngine(orc.recorder)
    return _active_replay_engine.get_replay_state()


@router.post("/replay/play")
def play_replay() -> SimulationReplayState:
    """Start replay playback."""
    global _active_replay_engine
    if not _active_replay_engine:
        load_replay()
    return _active_replay_engine.play()


@router.post("/replay/pause")
def pause_replay() -> SimulationReplayState:
    """Pause replay playback."""
    global _active_replay_engine
    if not _active_replay_engine:
        load_replay()
    return _active_replay_engine.pause()


@router.post("/replay/seek", response_model=SimulationReplayState)
def seek_replay(req: SeekReplayRequest) -> SimulationReplayState:
    """Seek replay engine to specified timestamp or tick count."""
    global _active_replay_engine
    if not _active_replay_engine:
        load_replay()

    if req.sim_time_s is not None:
        _active_replay_engine.seek_time(req.sim_time_s)
    elif req.tick_count is not None:
        _active_replay_engine.seek_tick(req.tick_count)

    return _active_replay_engine.get_replay_state()


@router.get("/replay/status", response_model=SimulationReplayState)
def get_replay_status() -> SimulationReplayState:
    """Retrieve current replay playback state."""
    global _active_replay_engine
    if not _active_replay_engine:
        load_replay()
    return _active_replay_engine.get_replay_state()


@router.get("/regression/run/{scenario_code}")
def run_regression_scenario(scenario_code: str, ticks: int = Query(default=50, ge=1, le=500)) -> Dict[str, Any]:
    """Execute one of the deterministic regression scenarios A through L."""
    code = scenario_code.upper()
    if code == "A":
        return ScenarioRegressionSuite.run_scenario_a_single_vehicle(ticks=ticks)
    elif code == "B":
        return ScenarioRegressionSuite.run_scenario_b_4_vehicle_formation(ticks=ticks)
    elif code == "C":
        return ScenarioRegressionSuite.run_scenario_c_8_vehicle_heterogeneous(ticks=ticks)
    elif code == "D":
        return ScenarioRegressionSuite.run_scenario_d_16_vehicle_swarm(ticks=ticks)
    elif code == "E":
        return ScenarioRegressionSuite.run_scenario_e_telemetry_dropout(ticks=ticks)
    elif code == "F":
        return ScenarioRegressionSuite.run_scenario_f_leader_loss(ticks=ticks)
    elif code == "G":
        return ScenarioRegressionSuite.run_scenario_g_formation_deviation(ticks=ticks)
    elif code == "H":
        return ScenarioRegressionSuite.run_scenario_h_separation_violation(ticks=ticks)
    elif code == "I":
        return ScenarioRegressionSuite.run_scenario_i_mission_completion(ticks=ticks)
    elif code == "J":
        return ScenarioRegressionSuite.run_scenario_j_mission_abort_safety(ticks=ticks)
    elif code == "K":
        return ScenarioRegressionSuite.run_scenario_k_sensor_dropout(ticks=ticks)
    elif code == "L":
        return ScenarioRegressionSuite.run_scenario_l_communication_degradation(ticks=ticks)
    else:
        raise HTTPException(status_code=400, detail=f"Unknown regression scenario code '{scenario_code}'. Use A-L.")
