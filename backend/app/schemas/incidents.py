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
