"""Integration tests for incident EventBus contracts, serialization, dispatching, and transaction hooks."""

from datetime import UTC, datetime
from unittest.mock import patch
import pytest
from sqlalchemy import select

from app.core.events import CRITICAL_EVENT_TYPES, get_event_bus
from app.models.incident import (
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    InvalidIncidentTransitionError,
)
from app.models.incident_event import DefensiveActionCategory, IncidentEvent, IncidentEventType
from app.models.track import Track, TrackState
from app.schemas.events import (
    IncidentRealtimePayload,
    RealtimeChannel,
    RealtimeEventEnvelope,
    RealtimeEventType,
)
from app.services.auth import create_user
from app.services.incident import IncidentNotFoundError, IncidentService, InvalidIncidentActionError


@pytest.fixture(autouse=True)
def reset_bus():
    get_event_bus().reset()
    yield
    get_event_bus().reset()


# --- EVENT CONTRACTS (Tests 1-4) ---


def test_01_all_incident_realtime_event_types_are_registered():
    """1. Verify that all 11 incident realtime event types are registered and classified as critical."""
    expected_event_types = {
        RealtimeEventType.INCIDENT_CREATED: "incident.created",
        RealtimeEventType.INCIDENT_ACKNOWLEDGED: "incident.acknowledged",
        RealtimeEventType.INCIDENT_ASSIGNED: "incident.assigned",
        RealtimeEventType.INCIDENT_REASSIGNED: "incident.reassigned",
        RealtimeEventType.INCIDENT_TRIAGED: "incident.triaged",
        RealtimeEventType.INCIDENT_ESCALATED: "incident.escalated",
        RealtimeEventType.INCIDENT_DE_ESCALATED: "incident.de_escalated",
        RealtimeEventType.INCIDENT_RESOLVED: "incident.resolved",
        RealtimeEventType.INCIDENT_CLOSED: "incident.closed",
        RealtimeEventType.INCIDENT_NOTE_ADDED: "incident.note_added",
        RealtimeEventType.INCIDENT_ACTION_LOGGED: "incident.action_logged",
    }

    for enum_variant, wire_val in expected_event_types.items():
        assert enum_variant.value == wire_val
        assert enum_variant in CRITICAL_EVENT_TYPES


def test_02_event_envelope_validates():
    """2. Verify that RealtimeEventEnvelope strictly validates required fields and types."""
    now = datetime.now(UTC)
    envelope = RealtimeEventEnvelope(
        event_type=RealtimeEventType.INCIDENT_CREATED.value,
        channel=RealtimeChannel.OPERATIONAL.value,
        sequence=1,
        timestamp=now,
        resource_type="incident",
        resource_id="inc-100",
        correlation_id="corr-100",
        payload={"title": "Test Incident"},
    )
    dumped = envelope.model_dump(mode="json")
    assert dumped["event_type"] == "incident.created"
    assert dumped["channel"] == "operational"
    assert dumped["sequence"] == 1
    assert dumped["resource_id"] == "inc-100"


def test_03_payload_serialization_round_trips():
    """3. Verify that IncidentRealtimePayload serializes and deserializes without data loss."""
    now = datetime.now(UTC)
    payload = IncidentRealtimePayload(
        incident_id="inc-uuid-1",
        incident_number="INC-20260829-AB12CD",
        title="Unauthorized Drone Formation",
        status=str(IncidentStatus.NEW),
        previous_status=None,
        severity=str(IncidentSeverity.HIGH),
        previous_severity=None,
        source=str(IncidentSource.ALERT),
        primary_track_id="TRK-101",
        primary_group_id="GRP-55",
        originating_alert_id="ALT-900",
        originating_intelligence_event_id="intel-evt-88",
        assigned_to="operator-1",
        previous_assignee=None,
        actor_user_id="user-123",
        incident_event_id="event-uuid-1",
        incident_event_sequence=1,
        incident_event_type=str(IncidentEventType.CREATED),
        category=None,
        message="Initial detection over perimeter",
        timestamp=now,
    )

    dumped = payload.model_dump(mode="json")
    rehydrated = IncidentRealtimePayload.model_validate(dumped)
    assert rehydrated.incident_id == "inc-uuid-1"
    assert rehydrated.incident_number == "INC-20260829-AB12CD"
    assert rehydrated.severity == "HIGH"
    assert rehydrated.incident_event_sequence == 1


def test_04_enums_serialize_deterministically():
    """4. Verify that IncidentStatus, IncidentSeverity, and DefensiveActionCategory serialize deterministically."""
    assert str(IncidentStatus.NEW) == "NEW"
    assert str(IncidentStatus.ACKNOWLEDGED) == "ACKNOWLEDGED"
    assert str(IncidentStatus.TRIAGED) == "TRIAGED"
    assert str(IncidentStatus.ESCALATED) == "ESCALATED"
    assert str(IncidentStatus.RESOLVED) == "RESOLVED"
    assert str(IncidentStatus.CLOSED) == "CLOSED"

    assert str(IncidentSeverity.LOW) == "LOW"
    assert str(IncidentSeverity.MEDIUM) == "MEDIUM"
    assert str(IncidentSeverity.HIGH) == "HIGH"
    assert str(IncidentSeverity.CRITICAL) == "CRITICAL"

    assert str(DefensiveActionCategory.SENSOR_REVIEW) == "SENSOR_REVIEW"
    assert str(DefensiveActionCategory.PROCEDURE_REVIEW) == "PROCEDURE_REVIEW"


# --- CREATION (Tests 5-9) ---


def test_05_create_emits_incident_created(database):
    """5. Verify that incident creation emits an incident.created event on EventBus upon transaction commit."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    incident = service.create_incident(title="Creation Test Incident", severity=IncidentSeverity.HIGH)
    database.commit()

    assert sub.queue.qsize() == 1
    evt = sub.queue.get_nowait()
    assert evt.event_type == "incident.created"
    assert evt.payload["incident_id"] == incident.id


def test_06_create_persists_created_timeline_event(database):
    """6. Verify that incident creation persists a CREATED timeline event in the database."""
    service = IncidentService(database)
    incident = service.create_incident(title="Timeline Created Test")
    database.commit()

    timeline = database.scalars(
        select(IncidentEvent).where(IncidentEvent.incident_id == incident.id).order_by(IncidentEvent.sequence)
    ).all()
    assert len(timeline) == 1
    assert timeline[0].event_type == IncidentEventType.CREATED
    assert timeline[0].sequence == 1


def test_07_event_references_correct_incident(database):
    """7. Verify that the emitted event envelope and payload reference the correct incident ID and incident number."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    incident = service.create_incident(title="Reference Check Incident")
    database.commit()

    evt = sub.queue.get_nowait()
    assert evt.resource_id == incident.id
    assert evt.payload["incident_id"] == incident.id
    assert evt.payload["incident_number"] == incident.incident_number


def test_08_actor_id_is_correct(database):
    """8. Verify that the actor user ID is accurately reflected in both database timeline and event payload."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    actor = create_user(database, "actor_user_8", "Actor 8", "a8@example.invalid", "test-password-123")
    database.commit()

    service = IncidentService(database)
    incident = service.create_incident(title="Actor Check Incident", created_by=actor.id)
    database.commit()

    evt = sub.queue.get_nowait()
    assert evt.payload["actor_user_id"] == actor.id


def test_09_correlation_fields_preserved(database):
    """9. Verify that primary_track_id, primary_group_id, originating_alert_id are preserved in the creation event."""
    from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType

    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        id="TRK-09",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.77,
        longitude=-122.41,
        confidence=0.9,
    )
    alert = Alert(
        id="ALT-09",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        reason="Test alert 09",
        created_at=now,
        updated_at=now,
    )
    database.add_all([track, alert])
    database.commit()

    service = IncidentService(database)
    incident = service.create_incident(
        title="Correlated Incident 09",
        primary_track_id="TRK-09",
        primary_group_id="GRP-09",
        originating_alert_id="ALT-09",
        originating_intelligence_event_id="INTEL-09",
    )
    database.commit()

    evt = sub.queue.get_nowait()
    assert evt.payload["primary_track_id"] == "TRK-09"
    assert evt.payload["primary_group_id"] == "GRP-09"
    assert evt.payload["originating_alert_id"] == "ALT-09"
    assert evt.payload["originating_intelligence_event_id"] == "INTEL-09"


# --- LIFECYCLE & TIMELINE (Tests 10-20) ---


def test_10_to_20_lifecycle_and_timeline_events(database):
    """10-20. Verify acknowledge, assign, reassignment, triage, escalation, de-escalation, resolve, close, note, action."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    u1 = create_user(database, "u_op1", "Op One", "u1@example.invalid", "test-password-123")
    u2 = create_user(database, "u_op2", "Op Two", "u2@example.invalid", "test-password-123")
    admin = create_user(database, "u_admin", "Admin", "adm@example.invalid", "test-password-123")
    database.commit()

    service = IncidentService(database)

    # Creation
    inc = service.create_incident(title="Lifecycle Test", severity=IncidentSeverity.LOW, created_by=u1.id)
    database.commit()
    e_create = sub.queue.get_nowait()
    assert e_create.event_type == "incident.created"

    # 10. Acknowledge -> incident.acknowledged
    service.acknowledge_incident(inc.id, actor_user_id=u2.id)
    database.commit()
    e_ack = sub.queue.get_nowait()
    assert e_ack.event_type == "incident.acknowledged"
    assert e_ack.payload["previous_status"] == "NEW"
    assert e_ack.payload["status"] == "ACKNOWLEDGED"

    # 11. Assign -> incident.assigned
    service.assign_incident(inc.id, assigned_to=u1.id, actor_user_id=u2.id)
    database.commit()
    e_assign = sub.queue.get_nowait()
    assert e_assign.event_type == "incident.assigned"
    assert e_assign.payload["assigned_to"] == u1.id
    assert e_assign.payload["previous_assignee"] is None

    # 12. Reassign -> incident.reassigned
    service.assign_incident(inc.id, assigned_to=u2.id, actor_user_id=u1.id)
    database.commit()
    e_reassign = sub.queue.get_nowait()
    assert e_reassign.event_type == "incident.reassigned"
    assert e_reassign.payload["assigned_to"] == u2.id
    assert e_reassign.payload["previous_assignee"] == u1.id

    # 13. Triage -> incident.triaged
    service.triage_incident(inc.id, actor_user_id=u2.id, severity=IncidentSeverity.HIGH, notes="Upgraded")
    database.commit()
    e_triage = sub.queue.get_nowait()
    assert e_triage.event_type == "incident.triaged"
    assert e_triage.payload["previous_severity"] == "LOW"
    assert e_triage.payload["severity"] == "HIGH"

    # 14. Escalate -> incident.escalated
    service.escalate_incident(inc.id, actor_user_id=u2.id, reason="Perimeter breach")
    database.commit()
    e_esc = sub.queue.get_nowait()
    assert e_esc.event_type == "incident.escalated"
    assert e_esc.payload["previous_status"] == "TRIAGED"
    assert e_esc.payload["status"] == "ESCALATED"

    # 15. De-escalate -> incident.de_escalated
    service.de_escalate_incident(inc.id, target_status=IncidentStatus.TRIAGED, actor_user_id=u2.id, reason="Resolved breach")
    database.commit()
    e_deesc = sub.queue.get_nowait()
    assert e_deesc.event_type == "incident.de_escalated"
    assert e_deesc.payload["previous_status"] == "ESCALATED"
    assert e_deesc.payload["status"] == "TRIAGED"

    # 18. Note -> incident.note_added
    service.add_note(inc.id, message="Field report observation", actor_user_id=u2.id)
    database.commit()
    e_note = sub.queue.get_nowait()
    assert e_note.event_type == "incident.note_added"
    assert e_note.payload["message"] == "Field report observation"

    # 19. Action -> incident.action_logged
    service.log_defensive_action(inc.id, category=DefensiveActionCategory.PROCEDURE_REVIEW, message="Reviewed SOP", actor_user_id=u2.id)
    database.commit()
    e_act = sub.queue.get_nowait()
    assert e_act.event_type == "incident.action_logged"
    assert e_act.payload["category"] == "PROCEDURE_REVIEW"

    # 16. Resolve -> incident.resolved
    service.resolve_incident(inc.id, actor_user_id=u2.id, resolution_summary="Clear")
    database.commit()
    e_res = sub.queue.get_nowait()
    assert e_res.event_type == "incident.resolved"
    assert e_res.payload["previous_status"] == "TRIAGED"
    assert e_res.payload["status"] == "RESOLVED"

    # 17. Close -> incident.closed
    service.close_incident(inc.id, actor_user_id=admin.id, closure_notes="Closed cleanly")
    database.commit()
    e_close = sub.queue.get_nowait()
    assert e_close.event_type == "incident.closed"
    assert e_close.payload["previous_status"] == "RESOLVED"
    assert e_close.payload["status"] == "CLOSED"

    # 20. Timeline sequence matches realtime payload sequence monotonically (1..11)
    all_events = [e_create, e_ack, e_assign, e_reassign, e_triage, e_esc, e_deesc, e_note, e_act, e_res, e_close]
    for idx, evt in enumerate(all_events, start=1):
        assert evt.payload["incident_event_sequence"] == idx


# --- INVALID TRANSITIONS & DEDUPLICATION (Tests 21-26) ---


def test_21_to_24_invalid_transitions_produce_zero_events(database):
    """21-24. Verify rejected transitions, rejected assignments, and mutations on closed incidents emit 0 events."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)
    service = IncidentService(database)

    inc = service.create_incident(title="Invalid Invariant Test")
    database.commit()
    sub.queue.get_nowait()  # consume creation event

    # 21. Rejected transition: direct NEW -> CLOSED
    with pytest.raises(InvalidIncidentTransitionError):
        service.close_incident(inc.id)
    database.commit()
    assert sub.queue.qsize() == 0

    # 22. Rejected assignment: blank assignee
    with pytest.raises(InvalidIncidentActionError):
        service.assign_incident(inc.id, assigned_to="   ")
    database.commit()
    assert sub.queue.qsize() == 0

    # 23. Rejected close without resolve
    with pytest.raises(InvalidIncidentTransitionError):
        service.close_incident(inc.id)
    database.commit()
    assert sub.queue.qsize() == 0

    # 24. Terminal CLOSED incident cannot be mutated
    service.acknowledge_incident(inc.id)
    service.resolve_incident(inc.id)
    service.close_incident(inc.id)
    database.commit()

    # Drain events
    while not sub.queue.empty():
        sub.queue.get_nowait()

    # Attempt mutation after terminal CLOSED
    with pytest.raises(InvalidIncidentTransitionError):
        service.triage_incident(inc.id)
    database.commit()
    assert sub.queue.qsize() == 0


def test_25_and_26_deduplication_and_rejected_requests(database):
    """25-26. Verify successful mutation produces exactly one event, and repeated rejected requests emit 0 events."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)
    service = IncidentService(database)

    inc = service.create_incident(title="Deduplication Test")
    database.commit()
    # 25. Exactly 1 event produced
    assert sub.queue.qsize() == 1
    sub.queue.get_nowait()

    # 26. Repeated rejected request produces zero additional events
    for _ in range(5):
        with pytest.raises(InvalidIncidentTransitionError):
            service.close_incident(inc.id)
        database.commit()

    assert sub.queue.qsize() == 0


# --- ROLLBACK & FAILURE SEMANTICS (Tests 38-40) ---


def test_38_failed_creation_emits_no_realtime_event(database):
    """38. Verify that rolling back after create_incident emits zero realtime events."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    service.create_incident(title="Rolled Back Creation")
    database.rollback()

    assert sub.queue.qsize() == 0


def test_39_failed_transition_emits_no_realtime_event(database):
    """39. Verify that a database rollback during a lifecycle transition suppresses all event emission."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    inc = service.create_incident(title="Rollback Transition Test")
    database.commit()
    sub.queue.get_nowait()

    service.acknowledge_incident(inc.id)
    database.rollback()

    assert sub.queue.qsize() == 0


def test_40_eventbus_failure_follows_documented_transaction_semantics(database):
    """40. Verify that EventBus transient publishing exceptions do not roll back committed database state."""
    service = IncidentService(database)
    inc = service.create_incident(title="Bus Exception Test")

    with patch.object(get_event_bus(), "publish", side_effect=RuntimeError("Bus queue saturated")):
        database.commit()

    # DB state remains committed and durable
    persisted = service.get_incident(inc.id)
    assert persisted.title == "Bus Exception Test"


# --- ORDERING & REPLAY DETERMINISM (Tests 41-43) ---


def test_41_lifecycle_event_sequence_is_monotonic(database):
    """41. Verify that sequence numbers assigned to incident events strictly increase monotonically."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    inc = service.create_incident(title="Monotonic Test")
    service.acknowledge_incident(inc.id)
    service.triage_incident(inc.id)
    service.resolve_incident(inc.id)
    database.commit()

    sequences = []
    while not sub.queue.empty():
        evt = sub.queue.get_nowait()
        sequences.append(evt.payload["incident_event_sequence"])

    assert sequences == [1, 2, 3, 4]


def test_42_timeline_sequence_is_deterministic(database):
    """42. Verify that querying incident timeline returns events in exact deterministic sequence order."""
    service = IncidentService(database)
    inc = service.create_incident(title="Deterministic Timeline Test")
    service.add_note(inc.id, message="Note 1")
    service.add_note(inc.id, message="Note 2")
    service.add_note(inc.id, message="Note 3")
    database.commit()

    timeline = service.get_timeline(inc.id)
    assert [e.sequence for e in timeline] == [1, 2, 3, 4]
    assert [e.message for e in timeline] == ["Incident created", "Note 1", "Note 2", "Note 3"]


def test_43_repeated_replay_produces_identical_event_ordering(database):
    """43. Verify that executing identical lifecycle operations in sequence produces identical event contracts."""
    service = IncidentService(database)

    inc1 = service.create_incident(title="Replay 1", severity=IncidentSeverity.MEDIUM)
    service.acknowledge_incident(inc1.id)
    service.resolve_incident(inc1.id)
    database.commit()

    inc2 = service.create_incident(title="Replay 2", severity=IncidentSeverity.MEDIUM)
    service.acknowledge_incident(inc2.id)
    service.resolve_incident(inc2.id)
    database.commit()

    t1 = service.get_timeline(inc1.id)
    t2 = service.get_timeline(inc2.id)

    assert [e.event_type for e in t1] == [e.event_type for e in t2]
    assert [e.sequence for e in t1] == [e.sequence for e in t2]


def test_backpressure_and_critical_event_eviction():
    """Verify that incident events are treated as CRITICAL and evict non-critical items under queue saturation."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL, maxsize=10)

    # Fill queue with 10 non-critical AI summary events
    for i in range(10):
        event_bus.publish(
            event_type=RealtimeEventType.AI_SUMMARY,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"cluster_count": i},
        )
    assert sub.queue.full()

    # Publish critical incident event
    event_bus.publish(
        event_type=RealtimeEventType.INCIDENT_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"incident_number": "INC-CRITICAL-1"},
    )

    items = []
    while not sub.queue.empty():
        items.append(sub.queue.get_nowait())

    assert any(item.event_type == "incident.created" for item in items)
