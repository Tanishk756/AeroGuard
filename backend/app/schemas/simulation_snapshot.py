"""Stage S12 Canonical Simulation Snapshot & Replay Pydantic Schemas."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from app.schemas.simulation_platform import VehicleState
from app.schemas.swarm import SafetyEvent, SwarmState
from app.schemas.swarm_safety import SwarmSafetyActionDecision
from app.schemas.swarm_telemetry import SwarmTelemetrySnapshot


class SimulationSnapshot(BaseModel):
    """Canonical versioned state snapshot for a single simulation timestep."""

    snapshot_id: str
    version: int = 1
    sim_time_seconds: float
    tick_count: int
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())

    vehicles_state: Dict[str, VehicleState] = Field(default_factory=dict)
    swarm_state: Optional[SwarmState] = None
    telemetry_snapshot: Optional[SwarmTelemetrySnapshot] = None
    safety_events: List[SafetyEvent] = Field(default_factory=list)
    safety_decisions: List[SwarmSafetyActionDecision] = Field(default_factory=list)
    mission_progress: Dict[str, Any] = Field(default_factory=dict)
    snapshot_hash: Optional[str] = None


class SimulationRecordingMetadata(BaseModel):
    """Metadata summary of a recorded simulation run."""

    recording_id: str
    scenario_id: str
    swarm_id: Optional[str] = None
    vehicle_count: int
    total_ticks: int
    total_duration_s: float
    dt_seconds: float
    recorded_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    recording_hash: str
    sample_count: int


class SimulationReplayState(BaseModel):
    """Current state of replay engine playback."""

    recording_id: str
    playback_status: str  # PLAYING, PAUSED, STOPPED
    current_sim_time_s: float
    current_tick: int
    total_ticks: int
    total_duration_s: float
    playback_speed: float = 1.0
    current_snapshot: Optional[SimulationSnapshot] = None
