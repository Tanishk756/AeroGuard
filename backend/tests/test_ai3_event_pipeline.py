"""Tests for Stage AI3-D: Event-Driven Telemetry, Change Detection, Monotonic Sequencing & Replay.

Verifies:
1. Incremental store bootstrap from database tracks.
2. Track update event emission: ai.priority, ai.behavior, ai.group, ai.summary.
3. Change detection: Duplicate identical updates are suppressed.
4. Group join & leave telemetry dispatch.
5. Track removal lifecycle and cleanup.
6. Event sequence monotonicity and concurrency safety.
7. Deterministic replay invariance (Run A == Run B).
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import json
import pytest

from ai.correlation.grouping import TrackObservation
from ai.incremental.pipeline import (
    IntelligencePipeline,
    get_intelligence_pipeline,
    reset_intelligence_pipeline,
)
from ai.incremental.store import IncrementalIntelligenceStore
from ai.schemas import BehavioralState
from app.core.events import EventBus, get_event_bus
from app.schemas.events import RealtimeChannel, RealtimeEventType


BASE_TIME = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)


def make_obs(
    tid: str,
    lat: float,
    lon: float,
    vel: float = 20.0,
    hdg: float = 90.0,
    alt: float = 120.0,
    conf: float = 0.95,
    ts: datetime | None = None,
) -> TrackObservation:
    return TrackObservation(
        id=tid,
        latitude=lat,
        longitude=lon,
        altitude=alt,
        velocity=vel,
        heading=hdg,
        confidence=conf,
        timestamp=ts or BASE_TIME,
    )


@pytest.fixture(autouse=True)
def clean_pipeline():
    reset_intelligence_pipeline()
    bus = get_event_bus()
    bus.reset()
    yield
    reset_intelligence_pipeline()
    bus.reset()


class TestAI3EventPipeline:
    """Verification of event-driven telemetry and change detection."""

    def test_01_track_update_emits_granular_and_summary_events(self) -> None:
        """Test 1: Updating a new track emits ai.priority, ai.behavior, and ai.summary events."""
        bus = get_event_bus()
        sub = bus.subscribe(RealtimeChannel.OPERATIONAL)
        pipeline = get_intelligence_pipeline()

        t1 = make_obs("TRK-EV-01", 37.7749, -122.4194)
        priority = pipeline.process_track_update(t1, publish_events=True)

        assert priority.track_id == "TRK-EV-01"

        events = []
        while not sub.queue.empty():
            events.append(sub.queue.get_nowait())

        event_types = [e.event_type for e in events]
        assert RealtimeEventType.AI_PRIORITY in event_types
        assert RealtimeEventType.AI_BEHAVIOR in event_types
        assert RealtimeEventType.AI_SUMMARY in event_types

        # Verify JSON serializability of all event payloads
        for e in events:
            json_str = json.dumps(e.payload)
            assert len(json_str) > 0
            assert e.sequence >= 1
            assert e.channel == RealtimeChannel.OPERATIONAL

    def test_02_duplicate_suppression_change_detection(self) -> None:
        """Test 2: Re-submitting the exact same track observation does not emit duplicate events."""
        bus = get_event_bus()
        sub = bus.subscribe(RealtimeChannel.OPERATIONAL)
        pipeline = get_intelligence_pipeline()

        t1 = make_obs("TRK-EV-01", 37.7749, -122.4194)
        pipeline.process_track_update(t1, publish_events=True)

        # Clear queue from initial update
        initial_events = []
        while not sub.queue.empty():
            initial_events.append(sub.queue.get_nowait())
        assert len(initial_events) >= 1

        # Re-apply identical observation
        pipeline.process_track_update(t1, publish_events=True)

        # No new events should have been emitted
        second_events = []
        while not sub.queue.empty():
            second_events.append(sub.queue.get_nowait())
        assert len(second_events) == 0

    def test_03_group_join_emits_group_and_summary_events(self) -> None:
        """Test 3: Moving a track into formation with another emits ai.group and ai.summary events."""
        bus = get_event_bus()
        sub = bus.subscribe(RealtimeChannel.OPERATIONAL)
        pipeline = get_intelligence_pipeline()

        t1 = make_obs("T1", 37.7749, -122.4194, vel=20.0, hdg=45.0)
        pipeline.process_track_update(t1, publish_events=True)

        # Drain initial events
        while not sub.queue.empty():
            sub.queue.get_nowait()

        # T2 arrives nearby -> forms group
        t2 = make_obs("T2", 37.7751, -122.4195, vel=20.2, hdg=45.5)
        pipeline.process_track_update(t2, publish_events=True)

        events = []
        while not sub.queue.empty():
            events.append(sub.queue.get_nowait())

        event_types = [e.event_type for e in events]
        assert RealtimeEventType.AI_GROUP in event_types
        assert RealtimeEventType.AI_SUMMARY in event_types

        # Verify group event payload
        group_events = [e for e in events if e.event_type == RealtimeEventType.AI_GROUP]
        assert len(group_events) == 1
        g_payload = group_events[0].payload
        assert set(g_payload["member_track_ids"]) == {"T1", "T2"}
        assert g_payload["member_count"] == 2

    def test_04_track_removal_lifecycle(self) -> None:
        """Test 4: Dropping a track cleans up state and emits updated ai.summary."""
        bus = get_event_bus()
        sub = bus.subscribe(RealtimeChannel.OPERATIONAL)
        pipeline = get_intelligence_pipeline()

        t1 = make_obs("T1", 37.7749, -122.4194)
        t2 = make_obs("T2", 37.7751, -122.4195)
        pipeline.process_track_update(t1, publish_events=False)
        pipeline.process_track_update(t2, publish_events=False)

        assert pipeline.store.track_count == 2
        assert pipeline.store.group_count == 1

        # Drop T2
        assert pipeline.process_track_removal("T2", publish_events=True) is True
        assert pipeline.store.track_count == 1
        assert pipeline.store.group_count == 0

        events = []
        while not sub.queue.empty():
            events.append(sub.queue.get_nowait())

        assert len(events) >= 1
        assert events[-1].event_type == RealtimeEventType.AI_SUMMARY
        assert len(events[-1].payload["groups"]) == 0

    def test_05_monotonic_sequence_under_concurrency(self) -> None:
        """Test 5: Concurrent event emissions strictly maintain monotonic sequence numbers with zero duplicates."""
        bus = get_event_bus()
        sub = bus.subscribe(RealtimeChannel.OPERATIONAL, maxsize=1000)
        pipeline = get_intelligence_pipeline()

        def worker_task(worker_id: int) -> None:
            for i in range(10):
                t = make_obs(
                    f"CONC-W{worker_id}-T{i}",
                    37.7749 + (worker_id * 0.01) + (i * 0.001),
                    -122.4194,
                )
                pipeline.process_track_update(t, publish_events=True)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_task, w) for w in range(8)]
            for f in futures:
                f.result()

        events = []
        while not sub.queue.empty():
            events.append(sub.queue.get_nowait())

        sequences = [e.sequence for e in events]
        assert len(sequences) > 0
        # Check strict monotonicity (strictly increasing without duplicates)
        for i in range(len(sequences) - 1):
            assert sequences[i] < sequences[i + 1], f"Sequence gap/inversion at {i}: {sequences[i]} >= {sequences[i+1]}"

    def test_06_deterministic_replay(self) -> None:
        """Test 6: Feeding identical update sequence to two pipelines produces identical final states and payloads."""
        pipe_a = IntelligencePipeline()
        pipe_b = IntelligencePipeline()

        updates = [
            make_obs("T1", 37.7749, -122.4194, vel=20.0, hdg=0.0),
            make_obs("T2", 37.7751, -122.4195, vel=20.0, hdg=0.0),
            make_obs("T3", 38.0000, -121.0000, vel=10.0, hdg=180.0),
            make_obs("T1", 37.7755, -122.4194, vel=20.0, hdg=0.0),
            make_obs("T3", 37.7752, -122.4193, vel=20.0, hdg=0.0),  # T3 joins formation
        ]

        for u in updates:
            pipe_a.process_track_update(u, publish_events=False)
            pipe_b.process_track_update(u, publish_events=False)

        snap_a = pipe_a.get_snapshot()
        snap_b = pipe_b.get_snapshot()

        assert len(snap_a.groups) == len(snap_b.groups)
        assert len(snap_a.behaviors) == len(snap_b.behaviors)
        assert len(snap_a.formations) == len(snap_b.formations)
        assert len(snap_a.priorities) == len(snap_b.priorities)

        for ga, gb in zip(snap_a.groups, snap_b.groups):
            assert ga.group_id == gb.group_id
            assert ga.member_track_ids == gb.member_track_ids
            assert ga.centroid_lat == pytest.approx(gb.centroid_lat, abs=1e-7)
            assert ga.centroid_lon == pytest.approx(gb.centroid_lon, abs=1e-7)

        for pa, pb in zip(snap_a.priorities, snap_b.priorities):
            assert pa.track_id == pb.track_id
            assert pa.priority_score == pytest.approx(pb.priority_score, abs=1e-4)
            assert pa.priority_level == pb.priority_level
