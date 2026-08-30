"""Performance benchmarks for AeroGuard EventBus and serialization under high load."""

import asyncio
from datetime import UTC, datetime
import time
import pytest

from app.core.events import EventBus
from app.schemas.events import RealtimeChannel, RealtimeEventEnvelope, RealtimeEventType


@pytest.mark.asyncio
async def test_event_bus_publish_throughput():
    """Benchmark event bus publish throughput under 10 concurrent subscribers."""
    bus = EventBus()
    subscriber_count = 10
    subscriptions = [
        bus.subscribe(RealtimeChannel.OPERATIONAL, maxsize=500)
        for _ in range(subscriber_count)
    ]

    event_count = 1000
    start_time = time.perf_counter()

    for i in range(event_count):
        bus.publish(
            event_type=RealtimeEventType.TRACK_UPDATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={
                "id": f"TRK-{i % 50}",
                "latitude": 37.7749 + (i * 0.0001),
                "longitude": -122.4194 + (i * 0.0001),
                "altitude": 150.0,
                "confidence": 0.95,
            },
            resource_type="track",
            resource_id=f"TRK-{i % 50}",
        )

    elapsed = time.perf_counter() - start_time
    throughput = event_count / elapsed

    # Clean up subscriptions
    for sub in subscriptions:
        bus.unsubscribe(sub)

    # Must exceed 5,000 publishes/sec in-process under background test runner CPU load
    assert throughput > 5000, f"Event bus publish throughput too low: {throughput:.0f} events/sec"
    assert bus.get_stats()["total_published"] == event_count


@pytest.mark.asyncio
async def test_event_bus_envelope_serialization_speed():
    """Benchmark RealtimeEventEnvelope serialization and model dumping."""
    envelope = RealtimeEventEnvelope(
        event_type=RealtimeEventType.ALERT_CREATED,
        channel=RealtimeChannel.OPERATIONAL,
        sequence=100,
        timestamp=datetime.now(UTC),
        resource_type="alert",
        resource_id="ALT-100",
        payload={
            "id": "ALT-100",
            "type": "GEOFENCE_BREACH",
            "severity": "CRITICAL",
            "status": "OPEN",
            "reason": "Vehicle breached perimeter",
        },
    )

    iterations = 5000
    start_time = time.perf_counter()

    for _ in range(iterations):
        dumped = envelope.model_dump(mode="json")
        assert dumped["event_type"] == "alert.created"

    elapsed = time.perf_counter() - start_time
    rate = iterations / elapsed
    assert rate > 10000, f"Serialization rate too low: {rate:.0f} ops/sec"
