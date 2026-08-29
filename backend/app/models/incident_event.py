"""Append-only incident timeline event model and action categories."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.incident import IncidentStatus


class IncidentEventType(StrEnum):
    CREATED = "CREATED"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    ASSIGNED = "ASSIGNED"
    REASSIGNED = "REASSIGNED"
    TRIAGED = "TRIAGED"
    ESCALATED = "ESCALATED"
    DE_ESCALATED = "DE_ESCALATED"
    NOTE_ADDED = "NOTE_ADDED"
    ACTION_LOGGED = "ACTION_LOGGED"
    STATUS_CHANGED = "STATUS_CHANGED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class DefensiveActionCategory(StrEnum):
    """Categorization for structured operator defensive workflow and triage actions.

    Note: These represent administrative, procedural, and analytical logging actions only.
    No physical countermeasure, weapon command, or engagement authorization is supported.
    """
    SENSOR_REVIEW = "SENSOR_REVIEW"
    TRACK_CORRELATION_REVIEW = "TRACK_CORRELATION_REVIEW"
    OPERATOR_CONTACT = "OPERATOR_CONTACT"
    SUPERVISOR_ESCALATION = "SUPERVISOR_ESCALATION"
    PROCEDURE_REVIEW = "PROCEDURE_REVIEW"
    SCENARIO_REVIEW = "SCENARIO_REVIEW"
    OTHER = "OTHER"


class IncidentEvent(Base):
    """Append-oriented immutable event log tracking lifecycle mutations and operator observations."""

    __tablename__ = "incident_events"
    __table_args__ = (
        Index("ix_incident_events_incident_sequence", "incident_id", "sequence"),
        Index("ix_incident_events_incident_timestamp", "incident_id", "timestamp"),
        Index("ix_incident_events_actor_timestamp", "actor_user_id", "timestamp"),
        Index("ix_incident_events_event_type", "event_type"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"),
        nullable=False,
    )
    sequence: Mapped[int] = mapped_column(nullable=False, default=1)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    event_type: Mapped[IncidentEventType] = mapped_column(
        Enum(IncidentEventType, native_enum=False, create_constraint=True),
        nullable=False,
    )
    actor_user_id: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    previous_status: Mapped[IncidentStatus | None] = mapped_column(
        Enum(IncidentStatus, native_enum=False, create_constraint=True),
        nullable=True,
    )
    new_status: Mapped[IncidentStatus | None] = mapped_column(
        Enum(IncidentStatus, native_enum=False, create_constraint=True),
        nullable=True,
    )
    message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    category: Mapped[DefensiveActionCategory | None] = mapped_column(
        Enum(DefensiveActionCategory, native_enum=False, create_constraint=True),
        nullable=True,
    )
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    # Relationships
    incident = relationship("Incident", back_populates="events")
    actor = relationship("User", foreign_keys=[actor_user_id])


def _get_event_metadata(event_obj: IncidentEvent) -> dict:
    return event_obj.metadata_json if event_obj.metadata_json is not None else {}


def _set_event_metadata(event_obj: IncidentEvent, value: dict) -> None:
    event_obj.metadata_json = value


IncidentEvent.metadata = property(_get_event_metadata, _set_event_metadata)


@event.listens_for(IncidentEvent, "before_update")
@event.listens_for(IncidentEvent, "before_delete")
def reject_incident_event_mutation(mapper, connection, target: IncidentEvent) -> None:
    """Enforce append-only invariant: historical timeline events cannot be updated or deleted."""
    raise ValueError("Incident timeline events are immutable")
