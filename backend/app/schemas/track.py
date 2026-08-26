"""Track and track-history data contracts."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

from app.models.association import TrackAssociationDecision
from app.models.sensor import SensorSourceClass
from app.models.track import TrackState
from app.schemas._operational import OperationalSchema, validate_utc


class TrackSchema(OperationalSchema):
    id: str | None = None
    state: TrackState = TrackState.NEW
    first_seen_at: datetime
    last_seen_at: datetime
    latitude: FiniteFloat = Field(ge=-90, le=90)
    longitude: FiniteFloat = Field(ge=-180, le=180)
    altitude: FiniteFloat | None = None
    velocity: FiniteFloat | None = Field(default=None, ge=0)
    heading: FiniteFloat | None = Field(default=None, ge=0, lt=360)
    confidence: FiniteFloat = Field(ge=0, le=1)
    classification: str | None = Field(default=None, max_length=64)
    source_count: int = Field(default=0, ge=0)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("first_seen_at", "last_seen_at")
    @classmethod
    def timestamps_are_utc(cls, value: datetime) -> datetime:
        return validate_utc(value)


class TrackHistorySchema(OperationalSchema):
    id: str | None = None
    track_id: str
    sequence: int = Field(ge=0)
    timestamp: datetime
    latitude: FiniteFloat = Field(ge=-90, le=90)
    longitude: FiniteFloat = Field(ge=-180, le=180)
    altitude: FiniteFloat | None = None
    velocity: FiniteFloat | None = Field(default=None, ge=0)
    heading: FiniteFloat | None = Field(default=None, ge=0, lt=360)
    confidence: FiniteFloat = Field(ge=0, le=1)
    state: TrackState
    provenance: SensorSourceClass
    source_detection_ids: list[str] = Field(default_factory=list, max_length=100)
    created_at: datetime | None = None

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return validate_utc(value)


class TrackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    state: TrackState
    first_seen_at: datetime
    last_seen_at: datetime
    latitude: float
    longitude: float
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    confidence: float
    classification: str | None = None
    source_count: int
    created_at: datetime
    updated_at: datetime


class TrackPage(BaseModel):
    items: list[TrackResponse]
    next_cursor: str | None = None


class TrackHistoryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: str
    sequence: int
    timestamp: datetime
    latitude: float
    longitude: float
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    confidence: float
    state: TrackState
    provenance: SensorSourceClass
    source_detection_ids: list[str]
    created_at: datetime


class TrackHistoryPage(BaseModel):
    items: list[TrackHistoryResponse]
    next_cursor: str | None = None


class TrackAssociationResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    detection_id: str
    track_id: str
    sensor_id: str
    timestamp: datetime
    distance_meters: float | None = None
    vertical_distance_meters: float | None = None
    time_delta_seconds: float | None = None
    score: float | None = None
    decision: TrackAssociationDecision
    reason: str
    gate_result: str | None = None
    created_at: datetime
