"""Pydantic contracts and response schemas for deterministic historical replay and comparison."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, FiniteFloat

from app.models.track import TrackState
from app.schemas.history import (
    HistoricalAlertItem,
    HistoricalDetectionItem,
    HistoricalThreatItem,
)


class ReplayFilter(BaseModel):
    track_ids: list[str] = Field(default_factory=list)
    sensor_ids: list[str] = Field(default_factory=list)
    classifications: list[str] = Field(default_factory=list)
    event_types: list[str] = Field(default_factory=list)


class ReplayRequest(BaseModel):
    start_time: datetime
    end_time: datetime
    step_interval_seconds: FiniteFloat = Field(default=1.0, gt=0.0, le=3600.0)
    filters: ReplayFilter = Field(default_factory=ReplayFilter)


class ReplayTrackState(BaseModel):
    track_id: str
    state: TrackState
    latitude: float
    longitude: float
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    confidence: float
    classification: str | None = None
    source_count: int = 1


class ReplaySnapshot(BaseModel):
    replay_time: datetime
    step_index: int
    is_complete: bool
    active_tracks: list[ReplayTrackState] = Field(default_factory=list)
    recent_detections: list[HistoricalDetectionItem] = Field(default_factory=list)
    active_alerts: list[HistoricalAlertItem] = Field(default_factory=list)
    active_threats: list[HistoricalThreatItem] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)


class ReplayStepRequest(BaseModel):
    start_time: datetime
    current_time: datetime
    end_time: datetime
    step_interval_seconds: FiniteFloat = Field(default=1.0, gt=0.0, le=3600.0)
    steps: int = Field(default=1, ge=1, le=1000)
    filters: ReplayFilter = Field(default_factory=ReplayFilter)


class ReplayComparisonRequest(BaseModel):
    request_1: ReplayRequest
    request_2: ReplayRequest


class ReplayComparisonReport(BaseModel):
    identical: bool
    total_detections_match: bool
    total_tracks_match: bool
    total_alerts_match: bool
    total_threats_match: bool
    detections_count_1: int
    detections_count_2: int
    tracks_count_1: int
    tracks_count_2: int
    alerts_count_1: int
    alerts_count_2: int
    threats_count_1: int
    threats_count_2: int
    differences: list[str] = Field(default_factory=list)
