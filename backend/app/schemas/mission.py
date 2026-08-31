"""Stage S7 Mission Planner, Compiler, and Execution Schemas."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class MissionItemSpec(BaseModel):
    """Deterministic ordered item within a flight mission."""
    id: Optional[str] = None
    sequence: int = Field(..., ge=1)
    command_type: str  # TAKEOFF, WAYPOINT, LOITER, LAND, RETURN_TO_HOME
    latitude: Optional[float] = Field(default=None, ge=-90.0, le=90.0)
    longitude: Optional[float] = Field(default=None, ge=-180.0, le=180.0)
    altitude_m: float = Field(default=10.0, ge=0.0, le=500.0)
    acceptance_radius_m: float = Field(default=2.0, ge=0.5, le=50.0)
    loiter_duration_s: float = Field(default=0.0, ge=0.0, le=3600.0)
    params: Optional[Dict[str, Any]] = None


class MissionCreate(BaseModel):
    """Request payload to create a new versioned Mission."""
    project_id: str = "proj-default-01"
    vehicle_id: str
    scenario_id: str
    name: str
    description: Optional[str] = None
    items: List[MissionItemSpec] = Field(default_factory=list)


class MissionResponse(BaseModel):
    """Response payload for a versioned Mission."""
    id: str
    project_id: str
    vehicle_id: str
    scenario_id: str
    name: str
    description: Optional[str] = None
    version: int
    status: str  # CREATED, VALIDATED, UPLOADED, RUNNING, COMPLETED, ABORTED
    items: List[MissionItemSpec]
    created_at: str
    updated_at: str


class CompiledMissionItem(BaseModel):
    """Canonical compiled item ready for autopilot translation."""
    sequence: int
    command_type: str
    latitude: float
    longitude: float
    altitude_m: float
    acceptance_radius_m: float
    loiter_duration_s: float


class CompiledMission(BaseModel):
    """Immutable compiled mission specification with SHA256 checksum."""
    mission_id: str
    version: int
    vehicle_id: str
    scenario_id: str
    items: List[CompiledMissionItem]
    compiled_mission_hash: str


class ArduPilotMissionItem(BaseModel):
    """MAVLink-compatible ArduCopter MAV_CMD mission item."""
    seq: int
    frame: int  # 3 = MAV_FRAME_GLOBAL_RELATIVE_ALT
    command: int  # e.g., 16 = WAYPOINT, 22 = TAKEOFF, 19 = LOITER_TIME, 20 = RTL, 21 = LAND
    current: int = 0
    autocontinue: int = 1
    param1: float = 0.0
    param2: float = 0.0
    param3: float = 0.0
    param4: float = 0.0
    x_lat: int  # Latitude * 1e7
    y_lon: int  # Longitude * 1e7
    z_alt: float  # Altitude in meters


class MissionValidationDiagnostic(BaseModel):
    """Diagnostic result from MissionValidationEngine."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class MissionProgress(BaseModel):
    """Live telemetry-derived mission execution progress."""
    mission_id: str
    mission_status: str
    current_item_index: int
    completed_items: int
    total_items: int
    progress_percentage: float
    distance_to_target_m: float
    mission_elapsed_time_s: float
