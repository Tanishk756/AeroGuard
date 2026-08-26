"""F2 raw detection and ingestion API contracts."""

from datetime import datetime

from pydantic import Field, FiniteFloat, field_validator

from app.models.sensor import SensorSourceClass
from app.schemas._operational import OperationalSchema, validate_utc


class RawDetection(OperationalSchema):
    source_detection_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime
    sensor_id: str = Field(min_length=1, max_length=36)
    latitude: FiniteFloat = Field(ge=-90, le=90)
    longitude: FiniteFloat = Field(ge=-180, le=180)
    altitude: FiniteFloat | None = None
    velocity: FiniteFloat | None = Field(default=None, ge=0)
    heading: FiniteFloat | None = Field(default=None, ge=0, le=360)
    horizontal_uncertainty: FiniteFloat | None = Field(default=None, ge=0)
    vertical_uncertainty: FiniteFloat | None = Field(default=None, ge=0)
    confidence: FiniteFloat = Field(ge=0, le=1)
    classification: str | None = Field(default=None, max_length=64)
    quality: str | None = Field(default=None, max_length=32)
    source_class: SensorSourceClass
    source_type: str = Field(min_length=1, max_length=64)
    metadata: dict = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return validate_utc(value)


class DetectionIngestionRequest(OperationalSchema):
    source_detection_id: str = Field(min_length=1, max_length=128)
    timestamp: datetime
    latitude: FiniteFloat = Field(ge=-90, le=90)
    longitude: FiniteFloat = Field(ge=-180, le=180)
    altitude: FiniteFloat | None = None
    velocity: FiniteFloat | None = Field(default=None, ge=0)
    heading: FiniteFloat | None = Field(default=None, ge=0, le=360)
    horizontal_uncertainty: FiniteFloat | None = Field(default=None, ge=0)
    vertical_uncertainty: FiniteFloat | None = Field(default=None, ge=0)
    confidence: FiniteFloat = Field(ge=0, le=1)
    classification: str | None = Field(default=None, max_length=64)
    quality: str | None = Field(default=None, max_length=32)
    source_class: SensorSourceClass
    source_type: str = Field(min_length=1, max_length=64)
    metadata: dict = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return validate_utc(value)


class DetectionIngestionResponse(OperationalSchema):
    detection_id: str
    created: bool
    sensor_id: str
    source_detection_id: str
    timestamp: datetime
