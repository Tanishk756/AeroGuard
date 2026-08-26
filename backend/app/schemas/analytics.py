"""Pydantic contracts and response schemas for deterministic operational analytics."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class DetectionMetrics(BaseModel):
    total_detections: int
    by_sensor: dict[str, int] = Field(default_factory=dict)
    by_modality: dict[str, int] = Field(default_factory=dict)
    by_source_class: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0


class TrackMetrics(BaseModel):
    total_tracks: int
    by_state: dict[str, int] = Field(default_factory=dict)
    by_classification: dict[str, int] = Field(default_factory=dict)
    avg_confidence: float = 0.0
    avg_source_count: float = 0.0


class AlertMetrics(BaseModel):
    total_alerts: int
    by_type: dict[str, int] = Field(default_factory=dict)
    by_severity: dict[str, int] = Field(default_factory=dict)
    by_status: dict[str, int] = Field(default_factory=dict)


class ThreatMetrics(BaseModel):
    total_assessed: int
    by_level: dict[str, int] = Field(default_factory=dict)
    avg_score: float = 0.0
    max_score: float = 0.0


class AnalyticsSummaryResponse(BaseModel):
    window_start: datetime
    window_end: datetime
    detections: DetectionMetrics
    tracks: TrackMetrics
    alerts: AlertMetrics
    threats: ThreatMetrics
    geofence_breach_count: int = 0
