"""Comprehensive unit and service tests for IncidentService (Stage IM1-B)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    InvalidIncidentTransitionError,
)
from app.models.incident_event import (
    DefensiveActionCategory,
    IncidentEvent,
    IncidentEventType,
)
from app.models.track import Track, TrackState
from app.models.user import User, UserStatus
from app.services.incident import (
    IncidentNotFoundError,
    IncidentService,
    InvalidIncidentActionError,
    generate_incident_number,
)


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
        username="lead_operator",
        email="lead_operator@aeroguard.internal",
        password_hash="hash_placeholder",
        display_name="Lead Operator",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)
    db_session.flush()
    return user


@pytest.fixture
def test_track(db_session: Session) -> Track:
    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=150.0,
        velocity=20.0,
        heading=90.0,
        confidence=0.95,
        classification="UAV_ROTARY",
    )
    db_session.add(track)
    db_session.flush()
    return track


# ============================================================================
# CREATION & NUMBERING TESTS
# ============================================================================

def test_create_incident_basic(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    now = datetime.now(UTC).replace(tzinfo=None)

    incident = service.create_incident(
        title="Unidentified Low-Altitude Ingress",
        description="Rotary UAV detected approaching defensive boundary zone.",
        severity=IncidentSeverity.HIGH,
        source=IncidentSource.OPERATOR,
        created_by=operator_user.id,
        now=now,
    )

    assert incident.id is not None
    assert incident.incident_number.startswith("INC-")
    assert incident.title == "Unidentified Low-Altitude Ingress"
    assert incident.description == "Rotary UAV detected approaching defensive boundary zone."
    assert incident.status == IncidentStatus.NEW
    assert incident.severity == IncidentSeverity.HIGH
    assert incident.source == IncidentSource.OPERATOR
    assert incident.created_by == operator_user.id
    assert incident.created_at == now
    assert incident.updated_at == now

    # Exactly one CREATED timeline event
    timeline = service.get_timeline(incident.id)
    assert len(timeline) == 1
    assert timeline[0].event_type == IncidentEventType.CREATED
    assert timeline[0].actor_user_id == operator_user.id
    assert timeline[0].new_status == IncidentStatus.NEW
    assert timeline[0].timestamp == now


def test_create_incident_blank_title_rejected(db_session: Session) -> None:
    service = IncidentService(db_session)
    with pytest.raises(InvalidIncidentActionError, match="Incident title cannot be blank"):
        service.create_incident(title="   ")


def test_create_incident_with_correlations(
    db_session: Session, operator_user: User, test_track: Track
) -> None:
    service = IncidentService(db_session)
    now = datetime.now(UTC).replace(tzinfo=None)

    alert = Alert(
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        track_id=test_track.id,
        reason="Zone breach alert",
        metadata_json={"zone": "ALPHA"},
        created_at=now,
        updated_at=now,
    )
    db_session.add(alert)
    db_session.flush()

    incident = service.create_incident(
        title="Correlated Multi-Sensor Incursion",
        primary_track_id=test_track.id,
        primary_group_id="GRP-SWARM-01",
        originating_alert_id=alert.id,
        originating_intelligence_event_id="EVT-AI-404",
        metadata={"priority_score": 92.5},
        created_by=operator_user.id,
    )

    assert incident.primary_track_id == test_track.id
    assert incident.primary_group_id == "GRP-SWARM-01"
    assert incident.originating_alert_id == alert.id
    assert incident.originating_intelligence_event_id == "EVT-AI-404"
    assert incident.metadata == {"priority_score": 92.5}


def test_generate_incident_number_uniqueness(db_session: Session) -> None:
    numbers = {generate_incident_number(db_session) for _ in range(50)}
    assert len(numbers) == 50
    for num in numbers:
        assert num.startswith("INC-")
        parts = num.split("-")
        assert len(parts) == 3
        assert len(parts[1]) == 8  # YYYYMMDD
        assert len(parts[2]) == 6  # 6 chars hex


# ============================================================================
# LIFECYCLE STATE MACHINE TRANSITION TESTS
# ============================================================================

def test_lifecycle_full_happy_path(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    t0 = datetime(2026, 8, 29, 10, 0, 0)
    t1 = datetime(2026, 8, 29, 10, 5, 0)
    t2 = datetime(2026, 8, 29, 10, 10, 0)
    t3 = datetime(2026, 8, 29, 10, 15, 0)
    t4 = datetime(2026, 8, 29, 10, 20, 0)
    t5 = datetime(2026, 8, 29, 10, 30, 0)

    # 1. NEW
    inc = service.create_incident(title="Lifecycle Test", created_by=operator_user.id, now=t0)
    assert inc.status == IncidentStatus.NEW

    # 2. ACKNOWLEDGED
    inc = service.acknowledge_incident(inc.id, actor_user_id=operator_user.id, now=t1)
    assert inc.status == IncidentStatus.ACKNOWLEDGED
    assert inc.acknowledged_by == operator_user.id
    assert inc.acknowledged_at == t1

    # 3. TRIAGED
    inc = service.triage_incident(
        inc.id, actor_user_id=operator_user.id, severity=IncidentSeverity.CRITICAL, notes="Confirmed multi-rotor", now=t2
    )
    assert inc.status == IncidentStatus.TRIAGED
    assert inc.severity == IncidentSeverity.CRITICAL

    # 4. ESCALATED
    inc = service.escalate_incident(
        inc.id, actor_user_id=operator_user.id, reason="Approaching high-priority defense asset", now=t3
    )
    assert inc.status == IncidentStatus.ESCALATED

    # 5. DE-ESCALATE to TRIAGED
    inc = service.de_escalate_incident(
        inc.id, target_status=IncidentStatus.TRIAGED, actor_user_id=operator_user.id, reason="Track turned away", now=t4
    )
    assert inc.status == IncidentStatus.TRIAGED

    # 6. RESOLVED
    inc = service.resolve_incident(
        inc.id, actor_user_id=operator_user.id, resolution_summary="Track departed area", now=t5
    )
    assert inc.status == IncidentStatus.RESOLVED
    assert inc.resolved_by == operator_user.id
    assert inc.resolved_at == t5

    # 7. CLOSED
    t6 = datetime(2026, 8, 29, 10, 45, 0)
    inc = service.close_incident(
        inc.id, actor_user_id=operator_user.id, closure_notes="Post-incident log complete", now=t6
    )
    assert inc.status == IncidentStatus.CLOSED
    assert inc.closed_by == operator_user.id
    assert inc.closed_at == t6

    # Verify complete timeline has 7 distinct ordered events
    timeline = service.get_timeline(inc.id)
    assert len(timeline) == 7
    event_types = [e.event_type for e in timeline]
    assert event_types == [
        IncidentEventType.CREATED,
        IncidentEventType.ACKNOWLEDGED,
        IncidentEventType.TRIAGED,
        IncidentEventType.ESCALATED,
        IncidentEventType.DE_ESCALATED,
        IncidentEventType.RESOLVED,
        IncidentEventType.CLOSED,
    ]


def test_lifecycle_reopening_from_resolved(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Reopen Test")
    service.acknowledge_incident(inc.id)
    service.triage_incident(inc.id)
    service.resolve_incident(inc.id, resolution_summary="Initial resolution")
    assert inc.status == IncidentStatus.RESOLVED

    # Reopen to TRIAGED
    reopened = service.triage_incident(inc.id, actor_user_id=operator_user.id, notes="New radar return detected")
    assert reopened.status == IncidentStatus.TRIAGED

    timeline = service.get_timeline(inc.id)
    assert timeline[-1].event_type == IncidentEventType.TRIAGED
    assert timeline[-1].previous_status == IncidentStatus.RESOLVED
    assert timeline[-1].new_status == IncidentStatus.TRIAGED


def test_lifecycle_closed_is_strictly_terminal(db_session: Session) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Terminal Test")
    service.acknowledge_incident(inc.id)
    service.resolve_incident(inc.id)
    service.close_incident(inc.id)

    assert inc.status == IncidentStatus.CLOSED

    # Any subsequent transition must fail
    with pytest.raises(InvalidIncidentTransitionError):
        service.acknowledge_incident(inc.id)
    with pytest.raises(InvalidIncidentTransitionError):
        service.triage_incident(inc.id)
    with pytest.raises(InvalidIncidentTransitionError):
        service.escalate_incident(inc.id)
    with pytest.raises(InvalidIncidentTransitionError):
        service.resolve_incident(inc.id)
    with pytest.raises(InvalidIncidentTransitionError):
        service.close_incident(inc.id)


def test_lifecycle_illegal_transitions_rejected(db_session: Session) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Illegal Transition Test")

    # NEW cannot jump directly to ESCALATED or CLOSED
    with pytest.raises(InvalidIncidentTransitionError):
        service.escalate_incident(inc.id)
    with pytest.raises(InvalidIncidentTransitionError):
        service.close_incident(inc.id)


# ============================================================================
# ASSIGNMENT & REASSIGNMENT TESTS
# ============================================================================

def test_assign_and_reassign_incident(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    second_user = User(
        username="analyst_smith",
        email="smith@aeroguard.internal",
        password_hash="hash_placeholder",
        display_name="Analyst Smith",
        status=UserStatus.ACTIVE,
    )
    db_session.add(second_user)
    db_session.flush()

    inc = service.create_incident(title="Assignment Test")
    assert inc.assigned_to is None

    # 1. First assignment
    inc = service.assign_incident(
        inc.id, assigned_to=operator_user.id, actor_user_id=operator_user.id, message="Assigned to lead"
    )
    assert inc.assigned_to == operator_user.id
    assert inc.status == IncidentStatus.NEW  # Assignment does NOT change status

    timeline = service.get_timeline(inc.id)
    assert len(timeline) == 2
    assert timeline[1].event_type == IncidentEventType.ASSIGNED
    assert timeline[1].metadata == {"previous_assignee": None, "assigned_to": operator_user.id}

    # 2. Reassignment
    inc = service.assign_incident(
        inc.id, assigned_to=second_user.id, actor_user_id=operator_user.id, message="Reassigned to analyst"
    )
    assert inc.assigned_to == second_user.id

    timeline = service.get_timeline(inc.id)
    assert len(timeline) == 3
    assert timeline[2].event_type == IncidentEventType.REASSIGNED
    assert timeline[2].metadata == {"previous_assignee": operator_user.id, "assigned_to": second_user.id}


def test_assign_blank_assignee_rejected(db_session: Session) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Blank Assignee Test")
    with pytest.raises(InvalidIncidentActionError, match="Assignee user ID cannot be blank"):
        service.assign_incident(inc.id, assigned_to="   ")


# ============================================================================
# NOTES & DEFENSIVE ACTIONS TESTS
# ============================================================================

def test_add_note(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Note Test")

    note_event = service.add_note(
        inc.id,
        message="Primary radar frequency shift noted in track telemetry.",
        actor_user_id=operator_user.id,
        metadata={"frequency_ghz": 9.4},
    )

    assert note_event.event_type == IncidentEventType.NOTE_ADDED
    assert note_event.message == "Primary radar frequency shift noted in track telemetry."
    assert note_event.actor_user_id == operator_user.id
    assert note_event.metadata == {"frequency_ghz": 9.4}

    # Verify status unchanged
    saved = service.get_incident(inc.id)
    assert saved.status == IncidentStatus.NEW


def test_add_blank_note_rejected(db_session: Session) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Blank Note Test")
    with pytest.raises(InvalidIncidentActionError, match="Note message cannot be blank"):
        service.add_note(inc.id, message="   ")


def test_log_defensive_actions_all_categories(db_session: Session, operator_user: User) -> None:
    service = IncidentService(db_session)
    inc = service.create_incident(title="Defensive Action Test")

    for cat in DefensiveActionCategory:
        evt = service.log_defensive_action(
            inc.id,
            category=cat,
            message=f"Executed workflow review: {cat}",
            actor_user_id=operator_user.id,
        )
        assert evt.event_type == IncidentEventType.ACTION_LOGGED
        assert evt.category == cat

    timeline = service.get_timeline(inc.id)
    # 1 CREATED + len(DefensiveActionCategory) ACTION_LOGGED events
    assert len(timeline) == 1 + len(DefensiveActionCategory)


# ============================================================================
# LISTING & FILTERING TESTS
# ============================================================================

def test_list_incidents_filtering(db_session: Session, operator_user: User, test_track: Track) -> None:
    service = IncidentService(db_session)
    now = datetime(2026, 8, 29, 12, 0, 0)

    i1 = service.create_incident(
        title="Incident 1",
        severity=IncidentSeverity.LOW,
        primary_track_id=test_track.id,
        created_by=operator_user.id,
        now=now - timedelta(minutes=10),
    )
    i2 = service.create_incident(
        title="Incident 2",
        severity=IncidentSeverity.HIGH,
        primary_group_id="GRP-01",
        now=now - timedelta(minutes=5),
    )
    i3 = service.create_incident(
        title="Incident 3",
        severity=IncidentSeverity.CRITICAL,
        now=now,
    )
    service.acknowledge_incident(i2.id, now=now)

    # 1. Filter by status
    new_incidents = service.list_incidents(status=IncidentStatus.NEW)
    assert len(new_incidents) == 2
    assert {inc.id for inc in new_incidents} == {i1.id, i3.id}

    # 2. Filter by severity
    crit_incidents = service.list_incidents(severity=IncidentSeverity.CRITICAL)
    assert len(crit_incidents) == 1
    assert crit_incidents[0].id == i3.id

    # 3. Filter by primary_track_id
    track_incidents = service.list_incidents(primary_track_id=test_track.id)
    assert len(track_incidents) == 1
    assert track_incidents[0].id == i1.id

    # 4. Filter by primary_group_id
    group_incidents = service.list_incidents(primary_group_id="GRP-01")
    assert len(group_incidents) == 1
    assert group_incidents[0].id == i2.id

    # 5. Deterministic ordering: newest first
    all_incidents = service.list_incidents()
    assert len(all_incidents) == 3
    assert [inc.id for inc in all_incidents] == [i3.id, i2.id, i1.id]


def test_get_incident_not_found(db_session: Session) -> None:
    service = IncidentService(db_session)
    with pytest.raises(IncidentNotFoundError, match="not found"):
        service.get_incident("non-existent-id")
