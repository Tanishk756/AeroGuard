"""Scenario configuration data contracts, validation schemas, and execution status models."""

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator, model_validator

from app.models.scenario import ScenarioStatus
from app.models.sensor import SensorSourceClass
from app.schemas._operational import OperationalSchema


class ScenarioSchema(OperationalSchema):
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    status: ScenarioStatus = ScenarioStatus.DRAFT
    created_by_user_id: str
    source_class: SensorSourceClass = SensorSourceClass.SIMULATION
    configuration_metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None


class ScenarioWaypoint(BaseModel):
    latitude: FiniteFloat = Field(ge=-90.0, le=90.0)
    longitude: FiniteFloat = Field(ge=-180.0, le=180.0)
    altitude: FiniteFloat | None = Field(default=None, ge=0.0)
    speed: FiniteFloat | None = Field(default=None, ge=0.0)


class ScenarioTargetDefinition(BaseModel):
    target_id: str = Field(min_length=1, max_length=64)
    initial_latitude: FiniteFloat = Field(ge=-90.0, le=90.0)
    initial_longitude: FiniteFloat = Field(ge=-180.0, le=180.0)
    initial_altitude: FiniteFloat | None = Field(default=None, ge=0.0)
    velocity: FiniteFloat = Field(default=0.0, ge=0.0)
    heading: FiniteFloat = Field(default=0.0, ge=0.0, lt=360.0)
    waypoints: list[ScenarioWaypoint] = Field(default_factory=list)
    classification: str | None = Field(default=None, max_length=64)


class ScenarioSensorDefinition(BaseModel):
    sensor_id: str = Field(min_length=1, max_length=64)
    modality: str = Field(default="radar", min_length=1, max_length=64)
    latitude: FiniteFloat = Field(ge=-90.0, le=90.0)
    longitude: FiniteFloat = Field(ge=-180.0, le=180.0)
    altitude: FiniteFloat | None = Field(default=None, ge=0.0)
    range_meters: FiniteFloat = Field(default=5000.0, ge=0.0)
    detection_probability: FiniteFloat = Field(default=0.90, ge=0.0, le=1.0)
    position_uncertainty_meters: FiniteFloat = Field(default=5.0, ge=0.0)
    altitude_uncertainty_meters: FiniteFloat | None = Field(default=None, ge=0.0)
    velocity_uncertainty_mps: FiniteFloat | None = Field(default=None, ge=0.0)
    fov_azimuth_start_deg: FiniteFloat | None = Field(default=None, ge=0.0, lt=360.0)
    fov_azimuth_span_deg: FiniteFloat | None = Field(default=None, gt=0.0, le=360.0)


class ScenarioConfiguration(BaseModel):
    seed: int = Field(default=0, ge=0, le=2**31 - 1)
    duration_seconds: FiniteFloat = Field(default=300.0, gt=0.0, le=86400.0)
    tick_rate_hz: FiniteFloat = Field(default=1.0, gt=0.0, le=100.0)
    start_time: datetime = Field(
        default_factory=lambda: datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
    )
    targets: list[ScenarioTargetDefinition] = Field(default_factory=list)
    sensors: list[ScenarioSensorDefinition] = Field(default_factory=list)
    geofence_ids: list[str] = Field(default_factory=list)

    @field_validator("start_time")
    @classmethod
    def validate_start_time_utc(cls, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def validate_unique_identifiers(self) -> "ScenarioConfiguration":
        target_ids = [t.target_id for t in self.targets]
        if len(target_ids) != len(set(target_ids)):
            raise ValueError("Target IDs in scenario configuration must be unique")

        sensor_ids = [s.sensor_id for s in self.sensors]
        if len(sensor_ids) != len(set(sensor_ids)):
            raise ValueError("Sensor IDs in scenario configuration must be unique")

        return self


class ScenarioCreateRequest(OperationalSchema):
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=1000)
    configuration: ScenarioConfiguration


class ScenarioUpdateRequest(OperationalSchema):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=1000)
    configuration: ScenarioConfiguration | None = None
    status: ScenarioStatus | None = None


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    status: ScenarioStatus
    source_class: SensorSourceClass
    created_by_user_id: str
    configuration_metadata: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class ScenarioPage(BaseModel):
    items: list[ScenarioResponse]
    next_cursor: str | None = None


class ScenarioStepRequest(BaseModel):
    ticks: int = Field(default=1, ge=1, le=1000)


class ScenarioExecutionStatusResponse(BaseModel):
    scenario_id: str
    status: ScenarioStatus
    is_paused: bool
    virtual_time: datetime
    tick_count: int
    active_targets: int
    generated_detections_count: int
    processed_detections_count: int
    seed: int
    error: str | None = None