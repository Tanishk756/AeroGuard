"""Incident management Pydantic schemas and request/response contracts."""

from datetime import datetime
import json
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models.incident import IncidentSeverity, IncidentSource, IncidentStatus
from app.models.incident_event import DefensiveActionCategory, IncidentEventType


def _validate_metadata_size(v: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(v, dict):
        raise ValueError("metadata must be a dictionary")
    try:
        encoded = json.dumps(v, separators=(",", ":")).encode("utf-8")
        if len(encoded) > 65536:
            raise ValueError("metadata exceeds maximum allowed size of 64KB")
    except (TypeError, OverflowError) as exc:
        raise ValueError("metadata must be JSON serializable") from exc
    return v


# ---------------------------------------------------------------------------
# Request Models
# ---------------------------------------------------------------------------

class CreateIncidentRequest(BaseModel):
    title: str = Field(min_length=1, max_length=256, description="Concise operator incident title")
    description: str | None = Field(default=None, max_length=4096, description="Detailed initial incident summary")
    severity: IncidentSeverity = Field(default=IncidentSeverity.MEDIUM, description="Initial operational severity")
    source: IncidentSource = Field(default=IncidentSource.OPERATOR, description="Originating domain source")
    primary_track_id: str | None = Field(default=None, max_length=64, description="Correlated primary track ID")
    primary_group_id: str | None = Field(default=None, max_length=64, description="Correlated primary swarm/group ID")
    originating_alert_id: str | None = Field(default=None, max_length=64, description="Correlated alert ID")
    originating_intelligence_event_id: str | None = Field(default=None, max_length=64, description="Correlated AI event ID")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured operational metadata")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _validate_metadata_size(v)


class AcknowledgeIncidentRequest(BaseModel):
    message: str | None = Field(default=None, max_length=2048, description="Optional acknowledgment note")


class AssignIncidentRequest(BaseModel):
    assigned_to: str = Field(min_length=1, max_length=64, description="Assignee user ID or identifier")
    message: str | None = Field(default=None, max_length=2048, description="Optional assignment notes")


class TriageIncidentRequest(BaseModel):
    severity: IncidentSeverity | None = Field(default=None, description="Updated severity assessment")
    notes: str | None = Field(default=None, max_length=4096, description="Triage findings and assessment notes")


class EscalateIncidentRequest(BaseModel):
    reason: str | None = Field(default=None, max_length=4096, description="Reason for command/supervisor escalation")
    severity: IncidentSeverity | None = Field(default=None, description="Optional elevated severity")


class DeEscalateIncidentRequest(BaseModel):
    target_status: IncidentStatus = Field(
        default=IncidentStatus.TRIAGED,
        description="Target status after de-escalation (TRIAGED or ACKNOWLEDGED)",
    )
    reason: str | None = Field(default=None, max_length=4096, description="Reason for de-escalation")


class ResolveIncidentRequest(BaseModel):
    resolution_summary: str | None = Field(
        default=None,
        max_length=4096,
        description="Operational resolution justification and summary",
    )


class CloseIncidentRequest(BaseModel):
    closure_notes: str | None = Field(
        default=None,
        max_length=4096,
        description="Formal incident closure notes and archive summary",
    )


class AddIncidentNoteRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4096, description="Operator note message")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Optional structured note metadata")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _validate_metadata_size(v)


class LogDefensiveActionRequest(BaseModel):
    category: DefensiveActionCategory = Field(description="Approved defensive action category")
    message: str | None = Field(default=None, max_length=4096, description="Operational action description")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Structured defensive action metadata")

    @field_validator("metadata")
    @classmethod
    def validate_metadata(cls, v: dict[str, Any]) -> dict[str, Any]:
        return _validate_metadata_size(v)


# ---------------------------------------------------------------------------
# Response Models
# ---------------------------------------------------------------------------

class IncidentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    incident_number: str
    title: str
    description: str | None = None
    status: IncidentStatus
    severity: IncidentSeverity
    source: IncidentSource
    primary_track_id: str | None = None
    primary_group_id: str | None = None
    originating_alert_id: str | None = None
    originating_intelligence_event_id: str | None = None
    created_by: str | None = None
    acknowledged_by: str | None = None
    assigned_to: str | None = None
    resolved_by: str | None = None
    closed_by: str | None = None
    created_at: datetime
    updated_at: datetime
    acknowledged_at: datetime | None = None
    assigned_at: datetime | None = None
    resolved_at: datetime | None = None
    closed_at: datetime | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")


class IncidentListResponse(BaseModel):
    items: list[IncidentResponse]
    limit: int
    offset: int
    total_count: int | None = None


class IncidentEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    id: str
    incident_id: str
    sequence: int
    timestamp: datetime
    event_type: IncidentEventType
    actor_user_id: str | None = None
    previous_status: IncidentStatus | None = None
    new_status: IncidentStatus | None = None
    category: DefensiveActionCategory | None = None
    message: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict, validation_alias="metadata_json")
    created_at: datetime


class IncidentTimelineResponse(BaseModel):
    incident_id: str
    events: list[IncidentEventResponse]
    total_count: int


# ---------------------------------------------------------------------------
# Analytics & Reporting Response Models (Stage IM1-G)
# ---------------------------------------------------------------------------

class IncidentSummaryMetrics(BaseModel):
    total_incidents: int = 0
    active_incidents: int = 0
    acknowledged_incidents: int = 0
    assigned_incidents: int = 0
    triaged_incidents: int = 0
    escalated_incidents: int = 0
    resolved_incidents: int = 0
    closed_incidents: int = 0
    critical_count: int = 0
    high_count: int = 0
    medium_count: int = 0
    low_count: int = 0


class IncidentSeverityDistributionItem(BaseModel):
    count: int = 0
    percentage: float = 0.0


class IncidentStatusDistributionItem(BaseModel):
    count: int = 0
    percentage: float = 0.0


class IncidentTimeSeriesBucket(BaseModel):
    bucket_start: str
    created_count: int = 0
    resolved_count: int = 0
    closed_count: int = 0
    escalated_count: int = 0


class IncidentLifecycleTimingMetrics(BaseModel):
    median_acknowledgement_seconds: float | None = None
    p95_acknowledgement_seconds: float | None = None
    median_assignment_seconds: float | None = None
    p95_assignment_seconds: float | None = None
    median_resolution_seconds: float | None = None
    p95_resolution_seconds: float | None = None
    median_closure_seconds: float | None = None
    p95_closure_seconds: float | None = None
    median_duration_seconds: float | None = None
    p95_duration_seconds: float | None = None
    sample_counts: dict[str, int] = Field(default_factory=dict)


class IncidentProceduralActionMetrics(BaseModel):
    by_category: dict[str, int] = Field(default_factory=dict)
    total_actions: int = 0


class IncidentCorrelationMetrics(BaseModel):
    with_primary_track: int = 0
    with_primary_group: int = 0
    uncorrelated: int = 0
    top_tracks: list[dict[str, Any]] = Field(default_factory=list)
    top_groups: list[dict[str, Any]] = Field(default_factory=list)


class IncidentWorkflowEventMetrics(BaseModel):
    by_event_type: dict[str, int] = Field(default_factory=dict)
    total_events: int = 0
    total_notes: int = 0
    total_actions: int = 0


class IncidentAnalyticsResponse(BaseModel):
    window_start: datetime | None = None
    window_end: datetime | None = None
    bucket_size: str = "day"
    summary: IncidentSummaryMetrics
    timing: IncidentLifecycleTimingMetrics
    severity_distribution: dict[IncidentSeverity, IncidentSeverityDistributionItem]
    status_distribution: dict[IncidentStatus, IncidentStatusDistributionItem]
    time_series: list[IncidentTimeSeriesBucket]
    procedural_actions: IncidentProceduralActionMetrics
    correlations: IncidentCorrelationMetrics
    workflow: IncidentWorkflowEventMetrics
