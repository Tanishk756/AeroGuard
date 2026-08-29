"""Incident management domain model and lifecycle state definitions."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class IncidentStatus(StrEnum):
    NEW = "NEW"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    TRIAGED = "TRIAGED"
    ESCALATED = "ESCALATED"
    RESOLVED = "RESOLVED"
    CLOSED = "CLOSED"


class IncidentSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class IncidentSource(StrEnum):
    OPERATOR = "OPERATOR"
    ALERT = "ALERT"
    INTELLIGENCE = "INTELLIGENCE"
    SYSTEM = "SYSTEM"


class InvalidIncidentTransitionError(ValueError):
    """Raised when an illegal incident lifecycle state transition is attempted."""

    def __init__(self, current_status: IncidentStatus, target_status: IncidentStatus, reason: str | None = None):
        msg = f"Cannot transition incident from {current_status} to {target_status}"
        if reason:
            msg += f": {reason}"
        super().__init__(msg)
        self.current_status = current_status
        self.target_status = target_status


# Explicit, deterministic state transition table for incident lifecycle
VALID_INCIDENT_TRANSITIONS: dict[IncidentStatus, frozenset[IncidentStatus]] = {
    IncidentStatus.NEW: frozenset({
        IncidentStatus.ACKNOWLEDGED,
    }),
    IncidentStatus.ACKNOWLEDGED: frozenset({
        IncidentStatus.TRIAGED,
        IncidentStatus.RESOLVED,
    }),
    IncidentStatus.TRIAGED: frozenset({
        IncidentStatus.ESCALATED,
        IncidentStatus.RESOLVED,
    }),
    IncidentStatus.ESCALATED: frozenset({
        IncidentStatus.TRIAGED,
        IncidentStatus.ACKNOWLEDGED,
    }),
    IncidentStatus.RESOLVED: frozenset({
        IncidentStatus.TRIAGED,  # Reopening for additional triage
        IncidentStatus.CLOSED,
    }),
    IncidentStatus.CLOSED: frozenset(),  # Terminal state
}


def can_transition(current_status: IncidentStatus, target_status: IncidentStatus) -> bool:
    """Return True if the state transition is legally allowed by the state machine."""
    allowed = VALID_INCIDENT_TRANSITIONS.get(current_status, frozenset())
    return target_status in allowed


def validate_transition(current_status: IncidentStatus, target_status: IncidentStatus) -> None:
    """Validate a lifecycle state transition. Raises InvalidIncidentTransitionError if forbidden."""
    if current_status == target_status:
        raise InvalidIncidentTransitionError(
            current_status, target_status, "Incident is already in this status"
        )
    if not can_transition(current_status, target_status):
        raise InvalidIncidentTransitionError(
            current_status, target_status, "Transition is not permitted by lifecycle rules"
        )


class Incident(Base):
    """Operational incident entity representing an actionable defensive workflow record."""

    __tablename__ = "incidents"
    __table_args__ = (
        Index("ix_incidents_status", "status"),
        Index("ix_incidents_severity", "severity"),
        Index("ix_incidents_created_at", "created_at"),
        Index("ix_incidents_assigned_to", "assigned_to"),
        Index("ix_incidents_primary_track_id", "primary_track_id"),
        Index("ix_incidents_primary_group_id", "primary_group_id"),
        Index("ix_incidents_incident_number", "incident_number", unique=True),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    incident_number: Mapped[str] = mapped_column(String(32), unique=True, nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    description: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    status: Mapped[IncidentStatus] = mapped_column(
        Enum(IncidentStatus, native_enum=False, create_constraint=True),
        nullable=False,
        default=IncidentStatus.NEW,
    )
    severity: Mapped[IncidentSeverity] = mapped_column(
        Enum(IncidentSeverity, native_enum=False, create_constraint=True),
        nullable=False,
        default=IncidentSeverity.MEDIUM,
    )
    source: Mapped[IncidentSource] = mapped_column(
        Enum(IncidentSource, native_enum=False, create_constraint=True),
        nullable=False,
        default=IncidentSource.OPERATOR,
    )

    # Optional foreign key & correlation references
    primary_track_id: Mapped[str | None] = mapped_column(
        ForeignKey("tracks.id", ondelete="SET NULL"),
        nullable=True,
    )
    primary_group_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    originating_alert_id: Mapped[str | None] = mapped_column(
        ForeignKey("alerts.id", ondelete="SET NULL"),
        nullable=True,
    )
    originating_intelligence_event_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    # User identity tracking
    created_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    acknowledged_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    assigned_to: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )
    closed_by: Mapped[str | None] = mapped_column(
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    # Lifecycle timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
        onupdate=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    assigned_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Structured metadata
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)

    # Relationships
    events = relationship(
        "IncidentEvent",
        back_populates="incident",
        cascade="all, delete-orphan",
        order_by="IncidentEvent.timestamp.asc()",
    )
    primary_track = relationship("Track", foreign_keys=[primary_track_id])
    originating_alert = relationship("Alert", foreign_keys=[originating_alert_id])
    creator = relationship("User", foreign_keys=[created_by])
    assignee = relationship("User", foreign_keys=[assigned_to])


def _get_metadata(incident: Incident) -> dict:
    return incident.metadata_json if incident.metadata_json is not None else {}


def _set_metadata(incident: Incident, value: dict) -> None:
    incident.metadata_json = value


Incident.metadata = property(_get_metadata, _set_metadata)
