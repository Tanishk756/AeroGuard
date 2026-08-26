"""Pydantic contracts and response schemas for historical operational queries."""

from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.models.sensor import SensorSourceClass
from app.models.threat import ThreatLevel
from app.models.track import TrackState


class HistoricalDetectionItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    sensor_id: str
    source_detection_id: str
    timestamp: datetime
    latitude: float
    longitude: float
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    confidence: float
    horizontal_uncertainty: float | None = None
    vertical_uncertainty: float | None = None
    classification: str | None = None
    source_class: SensorSourceClass
    source_type: str
    track_id: str | None = None


class HistoricalDetectionsPage(BaseModel):
    items: list[HistoricalDetectionItem]
    total_count: int
    limit: int
    offset: int


class HistoricalTrackPoint(BaseModel):
    model_config = ConfigDict(from_attributes=True)

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


class HistoricalTrackStateResponse(BaseModel):
    track_id: str
    as_of_time: datetime
    found: bool
    state_point: HistoricalTrackPoint | None = None


class HistoricalAlertItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    track_id: str | None = None
    sensor_id: str | None = None
    reason: str
    metadata_json: dict[str, Any] = Field(alias="metadata_json")
    created_at: datetime
    updated_at: datetime
    resolved_at: datetime | None = None


class HistoricalAlertsPage(BaseModel):
    items: list[HistoricalAlertItem]
    total_count: int
    limit: int
    offset: int


class HistoricalThreatItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: str
    score: float
    level: ThreatLevel
    factors: dict[str, Any]
    created_at: datetime
    updated_at: datetime


class HistoricalThreatsPage(BaseModel):
    items: list[HistoricalThreatItem]
    total_count: int
    limit: int
    offset: int


class TimelineEventType(StrEnum):
    DETECTION = "DETECTION"
    TRACK_UPDATE = "TRACK_UPDATE"
    THREAT_ASSESSMENT = "THREAT_ASSESSMENT"
    ALERT_RAISED = "ALERT_RAISED"
    ALERT_RESOLVED = "ALERT_RESOLVED"
    GEOFENCE_EVENT = "GEOFENCE_EVENT"


class TimelineItem(BaseModel):
    event_type: TimelineEventType
    timestamp: datetime
    entity_id: str
    track_id: str | None = None
    sensor_id: str | None = None
    summary: str
    payload: dict[str, Any] = Field(default_factory=dict)


class TimelinePage(BaseModel):
    items: list[TimelineItem]
    total_count: int
    limit: int
    offset: int
