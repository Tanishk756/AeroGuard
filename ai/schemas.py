"""Data contracts and schemas for AeroGuard AI & Defensive Intelligence Subsystem."""

from datetime import UTC, datetime
from enum import StrEnum
from pydantic import BaseModel, Field


class TrackPoint(BaseModel):
    """Normalized kinematic point in time for a track."""

    timestamp: datetime
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    altitude: float | None = None
    velocity: float | None = Field(default=None, ge=0.0)
    heading: float | None = Field(default=None, ge=0.0, lt=360.0)
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)


class KinematicFeatures(BaseModel):
    """Deterministic kinematic features extracted from track history."""

    speed_mps: float = Field(default=0.0, ge=0.0)
    acceleration_mps2: float = Field(default=0.0)
    vertical_speed_mps: float = Field(default=0.0)
    heading_deg: float | None = Field(default=None, ge=0.0, lt=360.0)
    turn_rate_dps: float = Field(default=0.0)
    speed_variance: float = Field(default=0.0, ge=0.0)
    altitude_variance: float = Field(default=0.0, ge=0.0)
    acceleration_variance: float = Field(default=0.0, ge=0.0)
    trajectory_curvature: float = Field(default=0.0, ge=0.0)
    loiter_radius_meters: float | None = Field(default=None, ge=0.0)
    directional_consistency: float = Field(default=1.0, ge=0.0, le=1.0)
    sample_count: int = Field(default=1, ge=0)
    timespan_seconds: float = Field(default=0.0, ge=0.0)


class AnomalyCategory(StrEnum):
    """Operationally meaningful defensive anomaly classifications."""

    NORMAL = "NORMAL"
    UNUSUAL_KINEMATICS = "UNUSUAL_KINEMATICS"
    RAPID_ALTITUDE_CHANGE = "RAPID_ALTITUDE_CHANGE"
    ERRATIC_HEADING = "ERRATIC_HEADING"
    EXCESSIVE_ACCELERATION = "EXCESSIVE_ACCELERATION"
    LOITERING_PATTERN = "LOITERING_PATTERN"
    TRAJECTORY_DEVIATION = "TRAJECTORY_DEVIATION"


class AnomalyFactor(BaseModel):
    """Individual contributing factor for explainable anomaly scoring."""

    name: str
    score: float = Field(..., ge=0.0, le=100.0)
    weight: float = Field(..., ge=0.0, le=1.0)
    contribution: float = Field(..., ge=0.0, le=100.0)
    severity: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    description: str


class AnomalyAssessment(BaseModel):
    """Explainable deterministic anomaly assessment for a track."""

    track_id: str
    anomaly_score: float = Field(..., ge=0.0, le=100.0)
    anomaly_level: str = Field(..., pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$")
    primary_category: AnomalyCategory
    sensor_confidence: float = Field(..., ge=0.0, le=1.0)
    factors: list[AnomalyFactor] = Field(default_factory=list)
    summary: str
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class TrajectoryWayPoint(BaseModel):
    """Projected future coordinate on a predicted flight path."""

    timestamp: datetime
    time_offset_seconds: float = Field(..., ge=0.0)
    latitude: float = Field(..., ge=-90.0, le=90.0)
    longitude: float = Field(..., ge=-180.0, le=180.0)
    altitude: float | None = None
    uncertainty_radius_meters: float = Field(..., ge=0.0)


class TrajectoryPrediction(BaseModel):
    """Defensive forward trajectory prediction over a time horizon."""

    track_id: str
    prediction_horizon_seconds: float = Field(..., ge=0.0)
    model_type: str = Field(default="CONSTANT_VELOCITY")
    waypoints: list[TrajectoryWayPoint] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class GeofenceIngressEstimate(BaseModel):
    """Defensive perimeter ingress estimation against an airspace geofence."""

    track_id: str
    geofence_id: str
    geofence_name: str
    estimated_time_to_breach_seconds: float | None = Field(default=None, ge=0.0)
    intersection_latitude: float | None = None
    intersection_longitude: float | None = None
    status: str = Field(..., pattern="^(INSIDE|APPROACHING|DIVERGING|NO_INTERSECTION)$")
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class DefensiveIntelligenceSummary(BaseModel):
    """Aggregated defensive intelligence state for an airspace track."""

    track_id: str
    features: KinematicFeatures
    anomaly: AnomalyAssessment
    trajectory: TrajectoryPrediction
    ingress_estimates: list[GeofenceIngressEstimate] = Field(default_factory=list)
    evaluated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
