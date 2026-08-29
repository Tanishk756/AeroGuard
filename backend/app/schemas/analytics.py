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


class IntelligenceAnalyticsReport(BaseModel):
    window_start: datetime
    window_end: datetime
    total_snapshots: int = 0
    total_group_events: int = 0
    total_behavior_transitions: int = 0
    behavior_distribution: dict[str, int] = Field(default_factory=dict)
    group_state_distribution: dict[str, int] = Field(default_factory=dict)
    avg_group_size: float = 0.0
    max_group_size: int = 0
    avg_coordination_index: float = 0.0
    peak_threat_score: float = 0.0
    threat_score_time_series: list[dict[str, Any]] = Field(default_factory=list)
    coordination_peaks: list[dict[str, Any]] = Field(default_factory=list)


class AnalyticsSummaryResponse(BaseModel):
    window_start: datetime
    window_end: datetime
    detections: DetectionMetrics
    tracks: TrackMetrics
    alerts: AlertMetrics
    threats: ThreatMetrics
    intelligence: IntelligenceAnalyticsReport | None = None
    geofence_breach_count: int = 0
