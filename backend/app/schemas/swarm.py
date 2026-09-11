"""Stage S10 Multi-Vehicle Swarm & Formation Pydantic Schemas."""

from enum import Enum
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timezone
from pydantic import BaseModel, Field


class FormationType(str, Enum):
    LINE = "LINE"
    COLUMN = "COLUMN"
    V_FORMATION = "V_FORMATION"
    GRID = "GRID"
    CIRCLE = "CIRCLE"


class SwarmRole(str, Enum):
    LEADER = "LEADER"
    FOLLOWER = "FOLLOWER"


class SwarmHealth(str, Enum):
    HEALTHY = "HEALTHY"
    DEGRADED = "DEGRADED"
    CRITICAL = "CRITICAL"
    DISCONNECTED = "DISCONNECTED"


class SafetyEventType(str, Enum):
    FORMATION_DEVIATION = "FORMATION_DEVIATION"
    MINIMUM_SEPARATION_BREACH = "MINIMUM_SEPARATION_BREACH"
    VEHICLE_DISCONNECTED = "VEHICLE_DISCONNECTED"
    LEADER_LOST = "LEADER_LOST"
    SLOT_CONFLICT = "SLOT_CONFLICT"


class SwarmConstraints(BaseModel):
    min_separation_m: float = Field(default=5.0, description="Minimum separation threshold between vehicles (m)")
    max_velocity_mps: float = Field(default=15.0, description="Maximum operational velocity (m/s)")
    max_acceleration_mpss: float = Field(default=3.0, description="Maximum operational acceleration (m/s^2)")
    position_tolerance_m: float = Field(default=2.0, description="Acceptable position error tolerance (m)")


class FormationSlot(BaseModel):
    slot_index: int
    role: SwarmRole = SwarmRole.FOLLOWER
    relative_offset_enu: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (East, North, Up) in meters relative to leader
    heading_offset_deg: float = 0.0


class FormationConfiguration(BaseModel):
    formation_type: FormationType = FormationType.LINE
    spacing_m: float = Field(default=10.0, ge=1.0)
    altitude_offset_m: float = Field(default=0.0)
    slots: Dict[int, FormationSlot] = Field(default_factory=dict)


class SwarmMemberConfig(BaseModel):
    vehicle_id: str
    role: SwarmRole = SwarmRole.FOLLOWER
    slot_index: int = 0
    autopilot_type: str = "ARDUPILOT"  # ARDUPILOT, PX4
    initial_position: Tuple[float, float, float] = (0.0, 0.0, 0.0)  # (Lat, Lon, Alt) or local Cartesian (E, N, U)
    initial_heading_deg: float = 0.0
    mission_id: Optional[str] = None
    sensor_config_ids: List[str] = Field(default_factory=list)


class SwarmConfiguration(BaseModel):
    swarm_id: str
    name: str
    description: Optional[str] = None
    leader_vehicle_id: Optional[str] = None
    formation: FormationConfiguration = Field(default_factory=FormationConfiguration)
    members: List[SwarmMemberConfig] = Field(default_factory=list)
    constraints: SwarmConstraints = Field(default_factory=SwarmConstraints)


class SafetyEvent(BaseModel):
    event_type: SafetyEventType
    severity: str = "WARNING"  # INFO, WARNING, CRITICAL
    vehicle_id: str
    target_vehicle_id: Optional[str] = None
    distance_m: Optional[float] = None
    threshold_m: Optional[float] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    message: str


class VehicleDesiredState(BaseModel):
    vehicle_id: str
    target_position_enu: Tuple[float, float, float]
    target_velocity_enu: Tuple[float, float, float]
    target_heading_deg: float
    position_error_m: float


class SwarmVehicleState(BaseModel):
    vehicle_id: str
    autopilot_type: str
    role: SwarmRole
    slot_index: int
    current_position_enu: Tuple[float, float, float]
    current_velocity_enu: Tuple[float, float, float]
    current_heading_deg: float
    desired_position_enu: Tuple[float, float, float]
    desired_velocity_enu: Tuple[float, float, float]
    position_error_m: float
    health_status: str  # HEALTHY, DEGRADED, CRITICAL, DISCONNECTED
    last_telemetry_timestamp: float


class SwarmState(BaseModel):
    swarm_id: str
    leader_vehicle_id: Optional[str]
    formation_type: FormationType
    health: SwarmHealth
    vehicle_states: Dict[str, SwarmVehicleState] = Field(default_factory=dict)
    desired_states: Dict[str, VehicleDesiredState] = Field(default_factory=dict)
    safety_events: List[SafetyEvent] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# API Request/Response Schemas

class SwarmCreate(BaseModel):
    name: str
    description: Optional[str] = None
    leader_vehicle_id: Optional[str] = None
    formation_type: FormationType = FormationType.LINE
    formation_spacing_m: float = 10.0
    min_separation_m: float = 5.0
    member_vehicle_ids: List[str] = Field(default_factory=list)


class SwarmUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    leader_vehicle_id: Optional[str] = None
    formation_type: Optional[FormationType] = None
    formation_spacing_m: Optional[float] = None
    min_separation_m: Optional[float] = None
    status: Optional[str] = None


class SwarmMemberAdd(BaseModel):
    vehicle_id: str
    role: SwarmRole = SwarmRole.FOLLOWER
    slot_index: Optional[int] = None


class SwarmFormationSet(BaseModel):
    formation_type: FormationType
    formation_spacing_m: float = 10.0
    altitude_offset_m: float = 0.0


class SwarmMemberResponse(BaseModel):
    id: str
    swarm_id: str
    vehicle_id: str
    role: str
    slot_index: int
    offset_x: float
    offset_y: float
    offset_z: float

    class Config:
        from_attributes = True


class SwarmResponse(BaseModel):
    id: str
    name: str
    description: Optional[str] = None
    leader_vehicle_id: Optional[str] = None
    formation_type: str
    formation_spacing_m: float
    min_separation_m: float
    status: str
    members: List[SwarmMemberResponse] = Field(default_factory=list)
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
