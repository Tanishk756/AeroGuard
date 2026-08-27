"""Unit tests for the realtime EventBus and event envelope contracts."""

import asyncio
from datetime import UTC, datetime
import pytest

from app.core.events import CRITICAL_EVENT_TYPES, EventBus, get_event_bus
from app.schemas.events import RealtimeChannel, RealtimeEventEnvelope, RealtimeEventType


def test_event_envelope_serialization():
    """Verify that RealtimeEventEnvelope enforces required fields and UTC timestamps."""
    now = datetime.now(UTC)
    envelope = RealtimeEventEnvelope(
        event_id="evt-123",
        event_type=RealtimeEventType.TRACK_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        sequence=1,
        timestamp=now,
        resource_type="track",
        resource_id="TRK-001",
        correlation_id="corr-abc",
        payload={"latitude": 37.7749, "longitude": -122.4194, "state": "CONFIRMED"},
    )

    data = envelope.model_dump(mode="json")
    assert data["event_id"] == "evt-123"
    assert data["event_type"] == "track.created"
    assert data["channel"] == "operational"
    assert data["sequence"] == 1
    assert data["resource_type"] == "track"
    assert data["resource_id"] == "TRK-001"
    assert data["payload"]["latitude"] == 37.7749


def test_monotonic_sequence_per_channel():
    """Verify that sequences are incremented independently and monotonically per channel."""
    bus = EventBus()
    seq_op1 = bus.get_next_sequence("operational")
    seq_op2 = bus.get_next_sequence("operational")
    seq_sim1 = bus.get_next_sequence("simulation")
    seq_op3 = bus.get_next_sequence("operational")
    seq_sim2 = bus.get_next_sequence("simulation")

    assert seq_op1 == 1
    assert seq_op2 == 2
    assert seq_op3 == 3
    assert seq_sim1 == 1
    assert seq_sim2 == 2


@pytest.mark.asyncio
async def test_publish_and_subscribe_delivery():
    """Verify that a subscriber receives published events matching its channel."""
    bus = EventBus()
    sub = bus.subscribe(RealtimeChannel.OPERATIONAL)

    env = bus.publish(
        event_type=RealtimeEventType.TRACK_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"track_id": "TRK-100", "state": "NEW"},
        resource_type="track",
        resource_id="TRK-100",
    )

    assert not sub.queue.empty()
    received = await asyncio.wait_for(sub.queue.get(), timeout=1.0)
    assert received.event_id == env.event_id
    assert received.event_type == "track.created"
    assert received.payload["track_id"] == "TRK-100"
    assert sub.delivered_count == 1
    assert sub.dropped_count == 0

    bus.unsubscribe(sub)
    assert bus.get_stats()["active_subscribers"] == 0


@pytest.mark.asyncio
async def test_channel_filtering_and_wildcard():
    """Verify that subscribers only receive events for their subscribed channel or wildcard."""
    bus = EventBus()
    op_sub = bus.subscribe(RealtimeChannel.OPERATIONAL)
    sim_sub = bus.subscribe(RealtimeChannel.SIMULATION)
    all_sub = bus.subscribe("*")

    # Publish operational event
    bus.publish(
        event_type=RealtimeEventType.TRACK_UPDATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"track_id": "TRK-1"},
    )

    # Publish simulation event
    bus.publish(
        event_type=RealtimeEventType.SIMULATION_STEP,
        channel=RealtimeChannel.SIMULATION,
        payload={"tick": 42},
    )

    assert op_sub.queue.qsize() == 1
    assert sim_sub.queue.qsize() == 1
    assert all_sub.queue.qsize() == 2

    op_item = await op_sub.queue.get()
    assert op_item.channel == "operational"

    sim_item = await sim_sub.queue.get()
    assert sim_item.channel == "simulation"

    bus.unsubscribe(op_sub)
    bus.unsubscribe(sim_sub)
    bus.unsubscribe(all_sub)


@pytest.mark.asyncio
async def test_custom_filter_function():
    """Verify that custom filter functions selectively gate event delivery."""
    bus = EventBus()
    # Subscribe only to CRITICAL alerts
    critical_sub = bus.subscribe(
        RealtimeChannel.OPERATIONAL,
        filter_func=lambda env: env.payload.get("severity") == "CRITICAL",
    )

    bus.publish(
        event_type=RealtimeEventType.ALERT_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"alert_id": "ALT-1", "severity": "LOW"},
    )
    bus.publish(
        event_type=RealtimeEventType.ALERT_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"alert_id": "ALT-2", "severity": "CRITICAL"},
    )

    assert critical_sub.queue.qsize() == 1
    item = await critical_sub.queue.get()
    assert item.payload["alert_id"] == "ALT-2"

    bus.unsubscribe(critical_sub)


@pytest.mark.asyncio
async def test_backpressure_telemetry_dropping():
    """Verify that non-critical telemetry is dropped when subscriber queue capacity is reached."""
    bus = EventBus()
    # Small queue of 10 items
    sub = bus.subscribe(RealtimeChannel.OPERATIONAL, maxsize=10)

    # Fill queue with 10 items
    for i in range(10):
        bus.publish(
            event_type=RealtimeEventType.TRACK_UPDATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"index": i},
        )

    assert sub.queue.full()
    assert sub.dropped_count == 0

    # Publish 11th telemetry event -> should be dropped
    bus.publish(
        event_type=RealtimeEventType.TRACK_UPDATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"index": 10},
    )

    assert sub.dropped_count == 1
    assert sub.queue.qsize() == 10

    bus.unsubscribe(sub)


@pytest.mark.asyncio
async def test_backpressure_critical_event_preservation():
    """Verify that critical events evict oldest items instead of being silently dropped."""
    bus = EventBus()
    sub = bus.subscribe(RealtimeChannel.OPERATIONAL, maxsize=10)

    # Fill queue with 10 non-critical telemetry items
    for i in range(10):
        bus.publish(
            event_type=RealtimeEventType.TRACK_UPDATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"index": i},
        )

    assert sub.queue.full()

    # Publish a CRITICAL alert event
    bus.publish(
        event_type=RealtimeEventType.ALERT_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        payload={"alert_id": "ALT-CRIT-1", "severity": "CRITICAL"},
    )

    # The critical event must have made it into the queue
    items = []
    while not sub.queue.empty():
        items.append(await sub.queue.get())

    assert len(items) == 10
    # The last item must be the critical alert
    assert items[-1].event_type == RealtimeEventType.ALERT_CREATED
    assert items[-1].payload["alert_id"] == "ALT-CRIT-1"
    assert sub.dropped_count == 1  # 1 old telemetry item was dropped to make room

    bus.unsubscribe(sub)


def test_event_bus_singleton():
    """Verify that get_event_bus returns the singleton instance."""
    b1 = get_event_bus()
    b2 = get_event_bus()
    assert b1 is b2
