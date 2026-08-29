"""Unit tests for Incident Audit Logging, Transactional Consistency, and Concurrency Protection."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.audit import AuditEvent
from app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    InvalidIncidentTransitionError,
)
from app.models.incident_event import DefensiveActionCategory, IncidentEvent, IncidentEventType
from app.models.user import User, UserStatus
from app.services.incident import IncidentService


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


@pytest.fixture
def operator_user(db_session: Session) -> User:
    user = User(
        username="audit_operator",
        email="audit_op@aeroguard.internal",
        password_hash="hash_placeholder",
        display_name="Audit Operator",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.flush()
    return user


def test_audit_records_for_all_incident_operations(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    t0 = datetime(2026, 8, 29, 14, 0, 0)

    # 1. CREATE
    inc = service.create_incident(
        title="Audit Matrix Incident",
        severity=IncidentSeverity.MEDIUM,
        source=IncidentSource.OPERATOR,
        created_by=operator_user.id,
        correlation_id="corr-create-001",
        now=t0,
    )

    # 2. ACKNOWLEDGE
    service.acknowledge_incident(
        inc.id, actor_user_id=operator_user.id, correlation_id="corr-ack-002", now=t0 + timedelta(seconds=1)
    )

    # 3. ASSIGN
    service.assign_incident(
        inc.id, assigned_to=operator_user.id, actor_user_id=operator_user.id, correlation_id="corr-assign-003", now=t0 + timedelta(seconds=2)
    )

    # 4. REASSIGN
    service.assign_incident(
        inc.id, assigned_to="user_analyst_2", actor_user_id=operator_user.id, correlation_id="corr-reassign-004", now=t0 + timedelta(seconds=3)
    )

    # 5. TRIAGE
    service.triage_incident(
        inc.id, actor_user_id=operator_user.id, severity=IncidentSeverity.HIGH, notes="Upgraded severity", correlation_id="corr-triage-005", now=t0 + timedelta(seconds=4)
    )

    # 6. ESCALATE
    service.escalate_incident(
        inc.id, actor_user_id=operator_user.id, reason="Approaching restricted airspace", correlation_id="corr-esc-006", now=t0 + timedelta(seconds=5)
    )

    # 7. DE-ESCALATE
    service.de_escalate_incident(
        inc.id, target_status=IncidentStatus.TRIAGED, actor_user_id=operator_user.id, reason="Asset safely redirected", correlation_id="corr-deesc-007", now=t0 + timedelta(seconds=6)
    )

    # 8. NOTE
    service.add_note(
        inc.id, message="Telemetry frequency recorded", actor_user_id=operator_user.id, correlation_id="corr-note-008", now=t0 + timedelta(seconds=7)
    )

    # 9. ACTION LOG
    service.log_defensive_action(
        inc.id, category=DefensiveActionCategory.SENSOR_REVIEW, message="Radar Doppler matched", actor_user_id=operator_user.id, correlation_id="corr-act-009", now=t0 + timedelta(seconds=8)
    )

    # 10. RESOLVE
    service.resolve_incident(
        inc.id, actor_user_id=operator_user.id, resolution_summary="Target dispersed", correlation_id="corr-res-010", now=t0 + timedelta(seconds=9)
    )

    # 11. CLOSE
    service.close_incident(
        inc.id, actor_user_id=operator_user.id, closure_notes="Archived", correlation_id="corr-close-011", now=t0 + timedelta(seconds=10)
    )

    # Fetch all audit events for this incident
    audit_events = db_session.scalars(
        select(AuditEvent).where(AuditEvent.target_id == inc.id).order_by(AuditEvent.timestamp.asc(), AuditEvent.id.asc())
    ).all()

    assert len(audit_events) == 11
    expected_event_types = [
        "INCIDENT_CREATED",
        "INCIDENT_ACKNOWLEDGED",
        "INCIDENT_ASSIGNED",
        "INCIDENT_REASSIGNED",
        "INCIDENT_TRIAGED",
        "INCIDENT_ESCALATED",
        "INCIDENT_DE_ESCALATED",
        "INCIDENT_NOTE_ADDED",
        "INCIDENT_ACTION_LOGGED",
        "INCIDENT_RESOLVED",
        "INCIDENT_CLOSED",
    ]
    assert [e.event_type for e in audit_events] == expected_event_types

    for event in audit_events:
        assert event.result == "SUCCESS"
        assert event.target_type == "INCIDENT"
        assert event.target_id == inc.id
        assert event.actor_user_id == operator_user.id


def test_transactional_rollback_preserves_clean_state(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Rollback Test", created_by=operator_user.id)
    initial_event_count = len(service.get_timeline(inc.id))
    initial_audit_count = len(
        db_session.scalars(select(AuditEvent).where(AuditEvent.target_id == inc.id)).all()
    )

    # Attempt an illegal transition inside a nested transaction or savepoint
    try:
        with db_session.begin_nested():
            service.escalate_incident(inc.id)  # NEW -> ESCALATED is illegal
    except InvalidIncidentTransitionError:
        pass

    # Invariants: incident status remains NEW, no orphan timeline events, no orphan audit logs
    saved = service.get_incident(inc.id)
    assert saved.status == IncidentStatus.NEW
    assert len(service.get_timeline(inc.id)) == initial_event_count
    assert len(db_session.scalars(select(AuditEvent).where(AuditEvent.target_id == inc.id)).all()) == initial_audit_count


def test_concurrency_duplicate_transition_rejection(db_session: Session, operator_user: User) -> None:
    """Verify that race/double transition attempts are cleanly rejected without duplicate events."""
    service = IncidentService(db_session)
    inc = service.create_incident(title="Double Acknowledge Race Test")

    # Operator 1 acknowledges
    service.acknowledge_incident(inc.id, actor_user_id=operator_user.id)
    assert inc.status == IncidentStatus.ACKNOWLEDGED

    # Operator 2 attempts acknowledge concurrently on the same incident
    with pytest.raises(InvalidIncidentTransitionError, match="Cannot transition incident from ACKNOWLEDGED to ACKNOWLEDGED"):
        service.acknowledge_incident(inc.id, actor_user_id="operator_2")

    # Verify no duplicate ACKNOWLEDGED event in timeline
    timeline = service.get_timeline(inc.id)
    ack_events = [e for e in timeline if e.event_type == IncidentEventType.ACKNOWLEDGED]
    assert len(ack_events) == 1

    # Verify no duplicate ACKNOWLEDGED audit record
    audits = db_session.scalars(
        select(AuditEvent).where(AuditEvent.target_id == inc.id, AuditEvent.event_type == "INCIDENT_ACKNOWLEDGED")
    ).all()
    assert len(audits) == 1
