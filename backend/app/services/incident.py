"""Transactional incident management and timeline service."""

from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import secrets
from typing import Any
from uuid import uuid4

from sqlalchemy import event as sa_event, func, select
from sqlalchemy.orm import Session

from app.core.events import get_event_bus
from app.models.audit import AuditEvent
from app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    InvalidIncidentTransitionError,
    validate_transition,
)
from app.models.incident_event import (
    DefensiveActionCategory,
    IncidentEvent,
    IncidentEventType,
)
from app.schemas.events import IncidentRealtimePayload, RealtimeChannel, RealtimeEventType
from app.services.audit import AuditService

logger = logging.getLogger(__name__)


@dataclass
class PendingIncidentEvent:
    event_type: RealtimeEventType
    payload: dict[str, Any]
    incident_id: str
    correlation_id: str | None = None


def _dispatch_pending_session_events(session: Session) -> list[PendingIncidentEvent]:
    """Drain and publish all pending incident events from a committed database session."""
    pending: list[PendingIncidentEvent] = session.info.pop("_pending_incident_events", [])
    if not pending:
        return []

    event_bus = get_event_bus()
    for evt in pending:
        try:
            event_bus.publish(
                event_type=evt.event_type,
                channel=RealtimeChannel.OPERATIONAL,
                payload=evt.payload,
                resource_type="incident",
                resource_id=evt.incident_id,
                correlation_id=evt.correlation_id,
            )
        except Exception:
            logger.exception("Failed to publish incident realtime event: %s", evt.event_type)
    return pending


@sa_event.listens_for(Session, "after_commit")
def _handle_session_after_commit(session: Session) -> None:
    _dispatch_pending_session_events(session)


@sa_event.listens_for(Session, "after_rollback")
def _handle_session_after_rollback(session: Session) -> None:
    session.info.pop("_pending_incident_events", None)


class IncidentNotFoundError(ValueError):
    """Raised when an incident entity does not exist in the database."""


class InvalidIncidentActionError(ValueError):
    """Raised when an invalid action, blank note, or illegal parameter is supplied."""


def generate_incident_number(db: Session, now: datetime | None = None, max_attempts: int = 5) -> str:
    """Generate a collision-resistant, operator-friendly incident identifier.

    Format: INC-YYYYMMDD-XXXXXX (e.g. INC-20260829-4A9B1C)
    """
    if now is None:
        now = datetime.now(UTC).replace(tzinfo=None)
    elif now.tzinfo is not None:
        now = now.astimezone(UTC).replace(tzinfo=None)

    date_str = now.strftime("%Y%m%d")

    for _ in range(max_attempts):
        suffix = secrets.token_hex(3).upper()
        candidate = f"INC-{date_str}-{suffix}"
        exists = db.scalar(
            select(Incident.id).where(Incident.incident_number == candidate).limit(1)
        )
        if not exists:
            return candidate

    # Deterministic UUID-based fallback if random generation encounters extreme collisions
    return f"INC-{date_str}-{uuid4().hex[:6].upper()}"


class IncidentService:
    """Application service for managing defensive incidents, timeline events, and audit integration."""

    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def _normalize_now(self, now: datetime | None) -> datetime:
        if now is None:
            return datetime.now(UTC).replace(tzinfo=None)
        if now.tzinfo is not None:
            return now.astimezone(UTC).replace(tzinfo=None)
        return now

    def _append_event(
        self,
        incident: Incident,
        event_type: IncidentEventType,
        now: datetime,
        actor_user_id: str | None = None,
        previous_status: IncidentStatus | None = None,
        new_status: IncidentStatus | None = None,
        message: str | None = None,
        category: DefensiveActionCategory | None = None,
        metadata: dict | None = None,
    ) -> IncidentEvent:
        """Internal timeline append primitive enforcing append-only invariants and deterministic sequence."""
        current_max = self.db.scalar(
            select(func.max(IncidentEvent.sequence)).where(
                IncidentEvent.incident_id == incident.id
            )
        ) or 0

        for obj in self.db.new:
            if isinstance(obj, IncidentEvent) and obj.incident_id == incident.id:
                if obj.sequence is not None and obj.sequence > current_max:
                    current_max = obj.sequence

        next_seq = current_max + 1

        event = IncidentEvent(
            id=str(uuid4()),
            incident=incident,
            incident_id=incident.id,
            sequence=next_seq,
            timestamp=now,
            event_type=event_type,
            actor_user_id=actor_user_id,
            previous_status=previous_status,
            new_status=new_status,
            message=message,
            category=category,
            metadata_json=metadata or {},
            created_at=now,
        )
        self.db.add(event)
        return event

    def _record_audit(
        self,
        event_type: str,
        action: str,
        incident: Incident,
        actor_user_id: str | None,
        timestamp: datetime,
        correlation_id: str | None = None,
        reason: str | None = None,
        metadata: dict | None = None,
    ) -> AuditEvent:
        """Internal audit append helper ensuring unified timestamp and schema consistency."""
        return self.audit_service.record_event(
            event_type=event_type,
            action=action,
            result="SUCCESS",
            correlation=correlation_id,
            actor_user_id=actor_user_id,
            target_type="INCIDENT",
            target_id=incident.id,
            reason=reason,
            metadata=metadata or {},
            timestamp=timestamp,
        )

    def _queue_event(
        self,
        event_type: RealtimeEventType,
        payload: IncidentRealtimePayload,
        incident_id: str,
        correlation_id: str | None = None,
    ) -> None:
        """Queue a validated incident realtime event payload onto the active session pending buffer."""
        pending_list = self.db.info.setdefault("_pending_incident_events", [])
        pending_list.append(
            PendingIncidentEvent(
                event_type=event_type,
                payload=payload.model_dump(mode="json"),
                incident_id=incident_id,
                correlation_id=correlation_id,
            )
        )

    def publish_pending_events(self) -> list[PendingIncidentEvent]:
        """Manually drain and publish pending incident events for manual or uncommitted test workflows."""
        return _dispatch_pending_session_events(self.db)

    def create_incident(
        self,
        title: str,
        description: str | None = None,
        severity: IncidentSeverity = IncidentSeverity.MEDIUM,
        source: IncidentSource = IncidentSource.OPERATOR,
        primary_track_id: str | None = None,
        primary_group_id: str | None = None,
        originating_alert_id: str | None = None,
        originating_intelligence_event_id: str | None = None,
        created_by: str | None = None,
        metadata: dict | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """Create a new incident with initial status NEW and exactly one CREATED timeline event."""
        clean_title = (title or "").strip()
        if not clean_title:
            raise InvalidIncidentActionError("Incident title cannot be blank")

        timestamp = self._normalize_now(now)
        incident_number = generate_incident_number(self.db, timestamp)

        incident = Incident(
            id=str(uuid4()),
            incident_number=incident_number,
            title=clean_title,
            description=description.strip() if description else None,
            status=IncidentStatus.NEW,
            severity=severity,
            source=source,
            primary_track_id=primary_track_id,
            primary_group_id=primary_group_id,
            originating_alert_id=originating_alert_id,
            originating_intelligence_event_id=originating_intelligence_event_id,
            created_by=created_by,
            created_at=timestamp,
            updated_at=timestamp,
            metadata_json=metadata or {},
        )
        self.db.add(incident)

        created_event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.CREATED,
            now=timestamp,
            actor_user_id=created_by,
            new_status=IncidentStatus.NEW,
            message=description.strip() if description else "Incident created",
            metadata=metadata or {},
        )

        self._record_audit(
            event_type="INCIDENT_CREATED",
            action="CREATE_INCIDENT",
            incident=incident,
            actor_user_id=created_by,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={
                "incident_number": incident.incident_number,
                "title": incident.title,
                "severity": str(incident.severity),
                "source": str(incident.source),
                "primary_track_id": incident.primary_track_id,
            },
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=None,
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=created_by,
            incident_event_id=created_event.id,
            incident_event_sequence=created_event.sequence,
            incident_event_type=str(created_event.event_type),
            category=None,
            message=created_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_CREATED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def get_incident(self, incident_id: str) -> Incident:
        """Retrieve an incident by ID or raise IncidentNotFoundError."""
        incident = self.db.get(Incident, incident_id)
        if incident is None:
            raise IncidentNotFoundError(f"Incident with ID '{incident_id}' not found")
        return incident

    def list_incidents(
        self,
        status: IncidentStatus | None = None,
        severity: IncidentSeverity | None = None,
        assigned_to: str | None = None,
        primary_track_id: str | None = None,
        primary_group_id: str | None = None,
        created_from: datetime | None = None,
        created_to: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Incident]:
        """List incidents matching query filters with deterministic sorting."""
        query = select(Incident)

        if status is not None:
            query = query.where(Incident.status == status)
        if severity is not None:
            query = query.where(Incident.severity == severity)
        if assigned_to is not None:
            query = query.where(Incident.assigned_to == assigned_to)
        if primary_track_id is not None:
            query = query.where(Incident.primary_track_id == primary_track_id)
        if primary_group_id is not None:
            query = query.where(Incident.primary_group_id == primary_group_id)
        if created_from is not None:
            norm_from = created_from.astimezone(UTC).replace(tzinfo=None) if created_from.tzinfo else created_from
            query = query.where(Incident.created_at >= norm_from)
        if created_to is not None:
            norm_to = created_to.astimezone(UTC).replace(tzinfo=None) if created_to.tzinfo else created_to
            query = query.where(Incident.created_at <= norm_to)

        query = query.order_by(Incident.created_at.desc(), Incident.id.desc())
        query = query.limit(max(1, min(limit, 500))).offset(max(0, offset))

        return list(self.db.scalars(query).all())

    def acknowledge_incident(
        self,
        incident_id: str,
        actor_user_id: str | None = None,
        message: str | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """Transition incident from NEW to ACKNOWLEDGED."""
        incident = self.get_incident(incident_id)
        old_status = incident.status
        validate_transition(old_status, IncidentStatus.ACKNOWLEDGED)

        timestamp = self._normalize_now(now)
        incident.status = IncidentStatus.ACKNOWLEDGED
        incident.acknowledged_by = actor_user_id
        incident.acknowledged_at = timestamp
        incident.updated_at = timestamp

        ack_event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.ACKNOWLEDGED,
            now=timestamp,
            actor_user_id=actor_user_id,
            previous_status=old_status,
            new_status=IncidentStatus.ACKNOWLEDGED,
            message=message or "Incident acknowledged by operator",
        )

        self._record_audit(
            event_type="INCIDENT_ACKNOWLEDGED",
            action="ACKNOWLEDGE_INCIDENT",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={"incident_number": incident.incident_number},
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=str(old_status),
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=ack_event.id,
            incident_event_sequence=ack_event.sequence,
            incident_event_type=str(ack_event.event_type),
            category=None,
            message=ack_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_ACKNOWLEDGED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def assign_incident(
        self,
        incident_id: str,
        assigned_to: str,
        actor_user_id: str | None = None,
        message: str | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """Assign or reassign an incident to a designated user."""
        incident = self.get_incident(incident_id)
        assigned_to_clean = (assigned_to or "").strip()
        if not assigned_to_clean:
            raise InvalidIncidentActionError("Assignee user ID cannot be blank")

        old_assignee = incident.assigned_to
        is_reassignment = old_assignee is not None and old_assignee != assigned_to_clean

        timestamp = self._normalize_now(now)
        incident.assigned_to = assigned_to_clean
        incident.assigned_at = timestamp
        incident.updated_at = timestamp

        event_type = IncidentEventType.REASSIGNED if is_reassignment else IncidentEventType.ASSIGNED
        audit_event_type = "INCIDENT_REASSIGNED" if is_reassignment else "INCIDENT_ASSIGNED"
        rt_type = RealtimeEventType.INCIDENT_REASSIGNED if is_reassignment else RealtimeEventType.INCIDENT_ASSIGNED

        assign_event = self._append_event(
            incident=incident,
            event_type=event_type,
            now=timestamp,
            actor_user_id=actor_user_id,
            message=message or (f"Incident reassigned to {assigned_to_clean}" if is_reassignment else f"Incident assigned to {assigned_to_clean}"),
            metadata={"previous_assignee": old_assignee, "assigned_to": assigned_to_clean},
        )

        self._record_audit(
            event_type=audit_event_type,
            action="ASSIGN_INCIDENT",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={
                "incident_number": incident.incident_number,
                "previous_assignee": old_assignee,
                "assigned_to": assigned_to_clean,
            },
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=None,
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=assigned_to_clean,
            previous_assignee=old_assignee,
            actor_user_id=actor_user_id,
            incident_event_id=assign_event.id,
            incident_event_sequence=assign_event.sequence,
            incident_event_type=str(assign_event.event_type),
            category=None,
            message=assign_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(rt_type, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def triage_incident(
        self,
        incident_id: str,
        actor_user_id: str | None = None,
        severity: IncidentSeverity | None = None,
        notes: str | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """Transition incident to TRIAGED (from ACKNOWLEDGED, ESCALATED, or RESOLVED reopen)."""
        incident = self.get_incident(incident_id)
        old_status = incident.status
        old_severity = incident.severity
        validate_transition(old_status, IncidentStatus.TRIAGED)

        timestamp = self._normalize_now(now)
        if severity is not None:
            incident.severity = severity

        incident.status = IncidentStatus.TRIAGED
        incident.updated_at = timestamp

        triage_event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.TRIAGED,
            now=timestamp,
            actor_user_id=actor_user_id,
            previous_status=old_status,
            new_status=IncidentStatus.TRIAGED,
            message=notes or "Incident triage assessment recorded",
            metadata={"severity": str(incident.severity)},
        )

        self._record_audit(
            event_type="INCIDENT_TRIAGED",
            action="TRIAGE_INCIDENT",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={
                "incident_number": incident.incident_number,
                "previous_status": str(old_status),
                "severity": str(incident.severity),
            },
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=str(old_status),
            severity=str(incident.severity),
            previous_severity=str(old_severity) if severity is not None and old_severity != severity else None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=triage_event.id,
            incident_event_sequence=triage_event.sequence,
            incident_event_type=str(triage_event.event_type),
            category=None,
            message=triage_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_TRIAGED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def escalate_incident(
        self,
        incident_id: str,
        actor_user_id: str | None = None,
        reason: str | None = None,
        severity: IncidentSeverity | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """Transition incident from TRIAGED to ESCALATED."""
        incident = self.get_incident(incident_id)
        old_status = incident.status
        old_severity = incident.severity
        validate_transition(old_status, IncidentStatus.ESCALATED)

        timestamp = self._normalize_now(now)
        if severity is not None:
            incident.severity = severity

        incident.status = IncidentStatus.ESCALATED
        incident.updated_at = timestamp

        esc_event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.ESCALATED,
            now=timestamp,
            actor_user_id=actor_user_id,
            previous_status=old_status,
            new_status=IncidentStatus.ESCALATED,
            message=reason or "Incident escalated to supervisor/operations command",
            metadata={"severity": str(incident.severity)},
        )

        self._record_audit(
            event_type="INCIDENT_ESCALATED",
            action="ESCALATE_INCIDENT",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            reason=reason,
            metadata={"incident_number": incident.incident_number, "severity": str(incident.severity)},
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=str(old_status),
            severity=str(incident.severity),
            previous_severity=str(old_severity) if severity is not None and old_severity != severity else None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=esc_event.id,
            incident_event_sequence=esc_event.sequence,
            incident_event_type=str(esc_event.event_type),
            category=None,
            message=esc_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_ESCALATED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def de_escalate_incident(
        self,
        incident_id: str,
        target_status: IncidentStatus = IncidentStatus.TRIAGED,
        actor_user_id: str | None = None,
        reason: str | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """De-escalate incident from ESCALATED back to TRIAGED or ACKNOWLEDGED."""
        incident = self.get_incident(incident_id)
        old_status = incident.status
        validate_transition(old_status, target_status)

        timestamp = self._normalize_now(now)
        incident.status = target_status
        incident.updated_at = timestamp

        de_esc_event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.DE_ESCALATED,
            now=timestamp,
            actor_user_id=actor_user_id,
            previous_status=old_status,
            new_status=target_status,
            message=reason or f"Incident de-escalated to {target_status}",
            metadata={"target_status": str(target_status)},
        )

        self._record_audit(
            event_type="INCIDENT_DE_ESCALATED",
            action="DE_ESCALATE_INCIDENT",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            reason=reason,
            metadata={"incident_number": incident.incident_number, "target_status": str(target_status)},
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=str(old_status),
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=de_esc_event.id,
            incident_event_sequence=de_esc_event.sequence,
            incident_event_type=str(de_esc_event.event_type),
            category=None,
            message=de_esc_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_DE_ESCALATED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def resolve_incident(
        self,
        incident_id: str,
        actor_user_id: str | None = None,
        resolution_summary: str | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """Transition incident from ACKNOWLEDGED or TRIAGED to RESOLVED."""
        incident = self.get_incident(incident_id)
        old_status = incident.status
        validate_transition(old_status, IncidentStatus.RESOLVED)

        timestamp = self._normalize_now(now)
        incident.status = IncidentStatus.RESOLVED
        incident.resolved_by = actor_user_id
        incident.resolved_at = timestamp
        incident.updated_at = timestamp

        res_event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.RESOLVED,
            now=timestamp,
            actor_user_id=actor_user_id,
            previous_status=old_status,
            new_status=IncidentStatus.RESOLVED,
            message=resolution_summary or "Defensive operational incident resolved",
        )

        self._record_audit(
            event_type="INCIDENT_RESOLVED",
            action="RESOLVE_INCIDENT",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={"incident_number": incident.incident_number, "summary": resolution_summary},
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=str(old_status),
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=res_event.id,
            incident_event_sequence=res_event.sequence,
            incident_event_type=str(res_event.event_type),
            category=None,
            message=res_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_RESOLVED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def close_incident(
        self,
        incident_id: str,
        actor_user_id: str | None = None,
        closure_notes: str | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> Incident:
        """Transition incident from RESOLVED to CLOSED (terminal state)."""
        incident = self.get_incident(incident_id)
        old_status = incident.status
        validate_transition(old_status, IncidentStatus.CLOSED)

        timestamp = self._normalize_now(now)
        incident.status = IncidentStatus.CLOSED
        incident.closed_by = actor_user_id
        incident.closed_at = timestamp
        incident.updated_at = timestamp

        close_event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.CLOSED,
            now=timestamp,
            actor_user_id=actor_user_id,
            previous_status=old_status,
            new_status=IncidentStatus.CLOSED,
            message=closure_notes or "Incident formally closed and archived",
        )

        self._record_audit(
            event_type="INCIDENT_CLOSED",
            action="CLOSE_INCIDENT",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={"incident_number": incident.incident_number, "closure_notes": closure_notes},
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=str(old_status),
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=close_event.id,
            incident_event_sequence=close_event.sequence,
            incident_event_type=str(close_event.event_type),
            category=None,
            message=close_event.message,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_CLOSED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return incident

    def add_note(
        self,
        incident_id: str,
        message: str,
        actor_user_id: str | None = None,
        metadata: dict | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> IncidentEvent:
        """Add an operator observation or analytical note to the incident timeline."""
        incident = self.get_incident(incident_id)
        clean_msg = (message or "").strip()
        if not clean_msg:
            raise InvalidIncidentActionError("Note message cannot be blank")

        timestamp = self._normalize_now(now)
        event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.NOTE_ADDED,
            now=timestamp,
            actor_user_id=actor_user_id,
            message=clean_msg,
            metadata=metadata or {},
        )

        self._record_audit(
            event_type="INCIDENT_NOTE_ADDED",
            action="ADD_INCIDENT_NOTE",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={"incident_number": incident.incident_number},
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=None,
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=event.id,
            incident_event_sequence=event.sequence,
            incident_event_type=str(event.event_type),
            category=None,
            message=clean_msg,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_NOTE_ADDED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return event

    def log_defensive_action(
        self,
        incident_id: str,
        category: DefensiveActionCategory,
        message: str | None = None,
        actor_user_id: str | None = None,
        metadata: dict | None = None,
        correlation_id: str | None = None,
        now: datetime | None = None,
    ) -> IncidentEvent:
        """Log a defensive workflow/procedural record to the incident timeline."""
        incident = self.get_incident(incident_id)
        if not isinstance(category, DefensiveActionCategory) and category not in set(DefensiveActionCategory):
            raise InvalidIncidentActionError(f"Invalid defensive action category: {category}")

        timestamp = self._normalize_now(now)
        cat_enum = category if isinstance(category, DefensiveActionCategory) else DefensiveActionCategory(category)
        event = self._append_event(
            incident=incident,
            event_type=IncidentEventType.ACTION_LOGGED,
            now=timestamp,
            actor_user_id=actor_user_id,
            category=cat_enum,
            message=message.strip() if message else None,
            metadata=metadata or {},
        )

        self._record_audit(
            event_type="INCIDENT_ACTION_LOGGED",
            action="LOG_DEFENSIVE_ACTION",
            incident=incident,
            actor_user_id=actor_user_id,
            timestamp=timestamp,
            correlation_id=correlation_id,
            metadata={"incident_number": incident.incident_number, "category": str(cat_enum)},
        )

        iso_ts = timestamp if timestamp.tzinfo else timestamp.replace(tzinfo=UTC)
        realtime_payload = IncidentRealtimePayload(
            incident_id=incident.id,
            incident_number=incident.incident_number,
            title=incident.title,
            status=str(incident.status),
            previous_status=None,
            severity=str(incident.severity),
            previous_severity=None,
            source=str(incident.source),
            primary_track_id=incident.primary_track_id,
            primary_group_id=incident.primary_group_id,
            originating_alert_id=incident.originating_alert_id,
            originating_intelligence_event_id=incident.originating_intelligence_event_id,
            assigned_to=incident.assigned_to,
            previous_assignee=None,
            actor_user_id=actor_user_id,
            incident_event_id=event.id,
            incident_event_sequence=event.sequence,
            incident_event_type=str(event.event_type),
            category=str(cat_enum),
            message=message.strip() if message else None,
            timestamp=iso_ts,
        )
        self._queue_event(RealtimeEventType.INCIDENT_ACTION_LOGGED, realtime_payload, incident.id, correlation_id)

        self.db.flush()
        return event

    def get_timeline(self, incident_id: str) -> list[IncidentEvent]:
        """Retrieve the immutable chronological event timeline for an incident."""
        # Ensure incident exists
        self.get_incident(incident_id)

        query = (
            select(IncidentEvent)
            .where(IncidentEvent.incident_id == incident_id)
            .order_by(IncidentEvent.sequence.asc(), IncidentEvent.timestamp.asc(), IncidentEvent.id.asc())
        )
        return list(self.db.scalars(query).all())
