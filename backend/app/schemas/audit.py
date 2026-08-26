"""Explicit audit API schemas."""

from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    event_type: str
    event_version: int
    timestamp: datetime
    action: str
    result: str
    correlation_id: str
    actor_user_id: str | None
    actor_session_id: str | None
    target_type: str | None
    target_id: str | None
    reason: str | None
    permission: str | None
    source_ip: str | None
    user_agent: str | None
    metadata: dict = Field(validation_alias="event_metadata", serialization_alias="metadata")
    created_at: datetime


class AuditEventPage(BaseModel):
    items: list[AuditEventResponse]
    next_cursor: str | None