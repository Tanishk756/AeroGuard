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
from app.models.incident_event import DefensiveActionCategory, IncidentEventType
from app.models.track import Track, TrackState
from app.schemas.events import (
    IncidentRealtimePayload,
    RealtimeChannel,
    RealtimeEventEnvelope,
    RealtimeEventType,
)
from app.services.auth import create_user
from app.services.incident import IncidentService, InvalidIncidentActionError


@pytest.fixture(autouse=True)
def reset_bus():
    get_event_bus().reset()
    yield
    get_event_bus().reset()


def test_all_incident_realtime_event_types_are_registered():
    """Verify that all 11 incident realtime event types are registered and belong to CRITICAL_EVENT_TYPES."""
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


def test_incident_realtime_payload_and_envelope_serialization():
    """Verify that IncidentRealtimePayload validates, serializes, and wraps cleanly inside RealtimeEventEnvelope."""
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
    assert dumped["incident_number"] == "INC-20260829-AB12CD"
    assert dumped["severity"] == "HIGH"
    assert dumped["incident_event_sequence"] == 1

    # Round trip
    rehydrated = IncidentRealtimePayload.model_validate(dumped)
    assert rehydrated.incident_id == "inc-uuid-1"

    # Wrap in EventBus RealtimeEventEnvelope
    envelope = RealtimeEventEnvelope(
        event_type=RealtimeEventType.INCIDENT_CREATED.value,
        channel=RealtimeChannel.OPERATIONAL.value,
        sequence=1,
        resource_type="incident",
        resource_id="inc-uuid-1",
        correlation_id="corr-456",
        payload=dumped,
    )

    envelope_dump = envelope.model_dump(mode="json")
    assert envelope_dump["event_type"] == "incident.created"
    assert envelope_dump["channel"] == "operational"
    assert envelope_dump["payload"]["primary_track_id"] == "TRK-101"


def test_transaction_commit_triggers_eventbus_dispatch(database):
    """Verify that committing a transaction dispatches queued incident events to EventBus subscribers."""
    event_bus = get_event_bus()
    subscription = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        id="TRK-9901",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.95,
    )
    actor = create_user(database, "op_eventbus", "Operator EventBus", "op_eb@example.invalid", "test-password-123")
    database.add(track)
    database.commit()

    service = IncidentService(database)
    incident = service.create_incident(
        title="EventBus Commit Test",
        severity=IncidentSeverity.CRITICAL,
        primary_track_id="TRK-9901",
        created_by=actor.id,
    )

    # Before commit: queue should be empty
    assert subscription.queue.qsize() == 0

    # Commit triggers after_commit hook
    database.commit()

    # After commit: EventBus has received exactly 1 incident.created event
    assert subscription.queue.qsize() == 1
    envelope = subscription.queue.get_nowait()
    assert envelope.event_type == "incident.created"
    assert envelope.channel == "operational"
    assert envelope.resource_id == incident.id
    assert envelope.payload["incident_id"] == incident.id
    assert envelope.payload["severity"] == "CRITICAL"
    assert envelope.payload["primary_track_id"] == "TRK-9901"
    assert envelope.payload["actor_user_id"] == actor.id
    assert envelope.payload["incident_event_sequence"] == 1


def test_transaction_rollback_suppresses_eventbus_dispatch(database):
    """Verify that rolling back a transaction discards all queued incident events with zero emission."""
    event_bus = get_event_bus()
    subscription = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    service.create_incident(
        title="Rollback Test Incident",
        severity=IncidentSeverity.HIGH,
    )

    # Rollback session
    database.rollback()

    # Zero events must be in the subscriber queue
    assert subscription.queue.qsize() == 0


def test_full_incident_lifecycle_event_emission(database):
    """Verify each lifecycle transition emits the exact corresponding realtime event on commit."""
    event_bus = get_event_bus()
    subscription = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    actor1 = create_user(database, "actor_one", "Actor One", "a1@example.invalid", "test-password-123")
    actor2 = create_user(database, "actor_two", "Actor Two", "a2@example.invalid", "test-password-123")
    analyst1 = create_user(database, "analyst_one", "Analyst One", "an1@example.invalid", "test-password-123")
    analyst2 = create_user(database, "analyst_two", "Analyst Two", "an2@example.invalid", "test-password-123")
    admin = create_user(database, "admin_closer", "Admin Closer", "admin@example.invalid", "test-password-123")
    database.commit()

    service = IncidentService(database)

    # 1. Create -> incident.created
    incident = service.create_incident(title="Lifecycle Flow Incident", severity=IncidentSeverity.LOW, created_by=actor1.id)
    database.commit()
    assert subscription.queue.qsize() == 1
    e1 = subscription.queue.get_nowait()
    assert e1.event_type == "incident.created"
    assert e1.payload["status"] == "NEW"

    # 2. Acknowledge -> incident.acknowledged
    service.acknowledge_incident(incident.id, actor_user_id=actor2.id, message="Acknowledged by operator")
    database.commit()
    assert subscription.queue.qsize() == 1
    e2 = subscription.queue.get_nowait()
    assert e2.event_type == "incident.acknowledged"
    assert e2.payload["previous_status"] == "NEW"
    assert e2.payload["status"] == "ACKNOWLEDGED"

    # 3. Initial Assign -> incident.assigned
    service.assign_incident(incident.id, assigned_to=analyst1.id, actor_user_id=actor2.id)
    database.commit()
    assert subscription.queue.qsize() == 1
    e3 = subscription.queue.get_nowait()
    assert e3.event_type == "incident.assigned"
    assert e3.payload["assigned_to"] == analyst1.id
    assert e3.payload["previous_assignee"] is None

    # 4. Reassign -> incident.reassigned
    service.assign_incident(incident.id, assigned_to=analyst2.id, actor_user_id=actor2.id)
    database.commit()
    assert subscription.queue.qsize() == 1
    e4 = subscription.queue.get_nowait()
    assert e4.event_type == "incident.reassigned"
    assert e4.payload["assigned_to"] == analyst2.id
    assert e4.payload["previous_assignee"] == analyst1.id

    # 5. Triage -> incident.triaged
    service.triage_incident(incident.id, actor_user_id=actor2.id, severity=IncidentSeverity.HIGH, notes="Upgrading to high")
    database.commit()
    assert subscription.queue.qsize() == 1
    e5 = subscription.queue.get_nowait()
    assert e5.event_type == "incident.triaged"
    assert e5.payload["previous_severity"] == "LOW"
    assert e5.payload["severity"] == "HIGH"
    assert e5.payload["status"] == "TRIAGED"

    # 6. Escalate -> incident.escalated
    service.escalate_incident(incident.id, actor_user_id=actor2.id, reason="Perimeter breach confirmed")
    database.commit()
    assert subscription.queue.qsize() == 1
    e6 = subscription.queue.get_nowait()
    assert e6.event_type == "incident.escalated"
    assert e6.payload["previous_status"] == "TRIAGED"
    assert e6.payload["status"] == "ESCALATED"

    # 7. De-escalate -> incident.de_escalated
    service.de_escalate_incident(incident.id, target_status=IncidentStatus.TRIAGED, actor_user_id=actor2.id, reason="Track departed")
    database.commit()
    assert subscription.queue.qsize() == 1
    e7 = subscription.queue.get_nowait()
    assert e7.event_type == "incident.de_escalated"
    assert e7.payload["previous_status"] == "ESCALATED"
    assert e7.payload["status"] == "TRIAGED"

    # 8. Note -> incident.note_added
    service.add_note(incident.id, message="Field report noted", actor_user_id=actor2.id)
    database.commit()
    assert subscription.queue.qsize() == 1
    e8 = subscription.queue.get_nowait()
    assert e8.event_type == "incident.note_added"
    assert e8.payload["message"] == "Field report noted"

    # 9. Action -> incident.action_logged
    service.log_defensive_action(incident.id, category=DefensiveActionCategory.PROCEDURE_REVIEW, message="Reviewed SOP", actor_user_id=actor2.id)
    database.commit()
    assert subscription.queue.qsize() == 1
    e9 = subscription.queue.get_nowait()
    assert e9.event_type == "incident.action_logged"
    assert e9.payload["category"] == "PROCEDURE_REVIEW"

    # 10. Resolve -> incident.resolved
    service.resolve_incident(incident.id, actor_user_id=actor2.id, resolution_summary="Resolved cleanly")
    database.commit()
    assert subscription.queue.qsize() == 1
    e10 = subscription.queue.get_nowait()
    assert e10.event_type == "incident.resolved"
    assert e10.payload["previous_status"] == "TRIAGED"
    assert e10.payload["status"] == "RESOLVED"

    # 11. Close -> incident.closed
    service.close_incident(incident.id, actor_user_id=admin.id, closure_notes="Archived after inspection")
    database.commit()
    assert subscription.queue.qsize() == 1
    e11 = subscription.queue.get_nowait()
    assert e11.event_type == "incident.closed"
    assert e11.payload["previous_status"] == "RESOLVED"
    assert e11.payload["status"] == "CLOSED"

    # Sequence numbers on events match 1..11 monotonically
    events = [e1, e2, e3, e4, e5, e6, e7, e8, e9, e10, e11]
    for idx, evt in enumerate(events, start=1):
        assert evt.payload["incident_event_sequence"] == idx


def test_invalid_transitions_produce_zero_events(database):
    """Verify that rejected state machine transitions, invalid assignments, or closed incidents emit 0 events."""
    event_bus = get_event_bus()
    subscription = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)
    service = IncidentService(database)

    incident = service.create_incident(title="Strict Invariant Incident")
    database.commit()
    subscription.queue.get_nowait()  # consume create event

    # 1. Illegal transition: direct NEW -> CLOSED throws InvalidIncidentTransitionError
    with pytest.raises(InvalidIncidentTransitionError):
        service.close_incident(incident.id)
    database.commit()
    assert subscription.queue.qsize() == 0

    # 2. Blank assignment: throws InvalidIncidentActionError
    with pytest.raises(InvalidIncidentActionError):
        service.assign_incident(incident.id, assigned_to="   ")
    database.commit()
    assert subscription.queue.qsize() == 0

    # 3. Illegal blank note: throws InvalidIncidentActionError
    with pytest.raises(InvalidIncidentActionError):
        service.add_note(incident.id, message="   ")
    database.commit()
    assert subscription.queue.qsize() == 0

    # 4. Transitions after terminal CLOSED state
    service.acknowledge_incident(incident.id)
    service.resolve_incident(incident.id)
    service.close_incident(incident.id)
    database.commit()

    # Drain events
    while not subscription.queue.empty():
        subscription.queue.get_nowait()

    # Attempt mutation after terminal CLOSED
    with pytest.raises(InvalidIncidentTransitionError):
        service.triage_incident(incident.id)
    database.commit()
    assert subscription.queue.qsize() == 0


def test_eventbus_dispatch_exception_does_not_break_commit(database):
    """Verify that a transient error during event publication is safely logged and does not abort committed state."""
    service = IncidentService(database)
    incident = service.create_incident(title="Safe Exception Incident")

    with patch.object(get_event_bus(), "publish", side_effect=RuntimeError("Transient queue failure")):
        # Commit should succeed despite event publication failure
        database.commit()

    retrieved = service.get_incident(incident.id)
    assert retrieved.title == "Safe Exception Incident"


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

    # Now publish critical incident event
    event_bus.publish(
        event_type=RealtimeEventType.INCIDENT_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"incident_number": "INC-CRITICAL-1"},
    )

    # Subscriber queue must contain the critical incident event
    items = []
    while not sub.queue.empty():
        items.append(sub.queue.get_nowait())

    assert any(item.event_type == "incident.created" for item in items)
