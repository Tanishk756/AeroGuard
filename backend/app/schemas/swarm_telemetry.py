"""Stage S11 Swarm Telemetry Stream Fusion & Aggregation Schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional, Tuple
from pydantic import BaseModel, Field

from app.schemas.simulation_platform import (
    AccelerationVector,
    AngularVelocityVector,
    AttitudeVector,
    BatteryState,
    GPSState,
    LinkStatus,
    PositionVector,
    VelocityVector,
)


class TelemetrySource(str, Enum):
    SITL = "SITL"
    MOCK = "MOCK"
    HARDWARE = "HARDWARE"


class SwarmVehicleTelemetry(BaseModel):
    """Canonical normalized telemetry vector for a vehicle member within a swarm."""

    vehicle_id: str
    swarm_id: str
    timestamp_utc: str
    sequence_number: int = 0
    sim_time_seconds: float = 0.0

    position: PositionVector = Field(default_factory=PositionVector)
    velocity: VelocityVector = Field(default_factory=VelocityVector)
    acceleration: AccelerationVector = Field(default_factory=AccelerationVector)
    attitude: AttitudeVector = Field(default_factory=AttitudeVector)
    angular_velocity: AngularVelocityVector = Field(default_factory=AngularVelocityVector)

    battery: BatteryState = Field(default_factory=BatteryState)
    gps: GPSState = Field(default_factory=GPSState)
    link_status: LinkStatus = Field(default_factory=LinkStatus)

    autopilot_type: str = "ARDUPILOT"  # ARDUPILOT, PX4, MOCK
    vehicle_health: str = "HEALTHY"  # HEALTHY, DEGRADED, CRITICAL
    armed: bool = False
    flight_mode: str = "GUIDED"

    telemetry_age_s: float = 0.0
    source: TelemetrySource = TelemetrySource.SITL
    frame_id: str = "base_link"


class SwarmBoundingBoxENU(BaseModel):
    min_x: float = 0.0
    max_x: float = 0.0
    min_y: float = 0.0
    max_y: float = 0.0
    min_z: float = 0.0
    max_z: float = 0.0


class FormationDeviationStats(BaseModel):
    mean_error_m: float = 0.0
    max_error_m: float = 0.0
    std_dev_m: float = 0.0


class PairwiseSeparationStats(BaseModel):
    min_distance_m: float = 0.0
    max_distance_m: float = 0.0
    closest_pair: Optional[Tuple[str, str]] = None


class VehicleHealthSummary(BaseModel):
    healthy_count: int = 0
    degraded_count: int = 0
    critical_count: int = 0
    disconnected_count: int = 0


class TelemetryFreshnessSummary(BaseModel):
    avg_age_s: float = 0.0
    max_age_s: float = 0.0


class CommunicationQualitySummary(BaseModel):
    avg_quality_percent: float = 100.0
    min_quality_percent: float = 100.0


class SwarmTelemetrySnapshot(BaseModel):
    """Coherent, deterministic real-time telemetry snapshot for an entire swarm."""

    swarm_id: str
    snapshot_sequence: int = 0
    timestamp_utc: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    sim_time_seconds: float = 0.0

    active_vehicle_ids: List[str] = Field(default_factory=list)
    vehicles_telemetry: Dict[str, SwarmVehicleTelemetry] = Field(default_factory=dict)

    centroid_enu: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    bounding_box_enu: SwarmBoundingBoxENU = Field(default_factory=SwarmBoundingBoxENU)
    bounding_sphere_radius_m: float = 0.0

    average_velocity_enu: Tuple[float, float, float] = (0.0, 0.0, 0.0)
    formation_centroid_enu: Tuple[float, float, float] = (0.0, 0.0, 0.0)

    formation_deviation_stats: FormationDeviationStats = Field(default_factory=FormationDeviationStats)
    pairwise_separation_stats: PairwiseSeparationStats = Field(default_factory=PairwiseSeparationStats)
    vehicle_health_summary: VehicleHealthSummary = Field(default_factory=VehicleHealthSummary)
    telemetry_freshness_summary: TelemetryFreshnessSummary = Field(default_factory=TelemetryFreshnessSummary)
    communication_quality_summary: CommunicationQualitySummary = Field(default_factory=CommunicationQualitySummary)
