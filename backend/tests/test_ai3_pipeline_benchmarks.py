"""Performance benchmarks for Stage AI3-D: Pipeline Telemetry & REST Route Acceleration.

Measures:
1. REST cached snapshot read latency across N = 100, 500, 1,000, 5,000 tracks.
2. Single-track incremental update latency across N = 100, 500, 1,000, 5,000 tracks.
3. Event publication and subscriber dispatch overhead.
"""

from datetime import UTC, datetime
import time
import pytest

from ai.correlation.grouping import TrackObservation
from ai.incremental.pipeline import IntelligencePipeline, reset_intelligence_pipeline
from ai.incremental.store import IncrementalIntelligenceStore
from app.core.events import EventBus, get_event_bus
from app.schemas.events import RealtimeChannel


def make_track(
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
        timestamp=ts or datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC),
    )


class TestAI3PipelineBenchmarks:
    """Benchmark suite validating REST acceleration and localized update latency."""

    def test_pipeline_scale_and_telemetry_benchmarks(self) -> None:
        """Measure REST read, incremental update, and event dispatch latency at scale."""
        print("\n" + "=" * 82)
        print("  AEROGUARD AI3-D PIPELINE & REST ACCELERATION PERFORMANCE BENCHMARKS")
        print("  Local Software Microbenchmark — Pure Python 3.12 (Windows Native)")
        print("=" * 82)

        scales = [100, 500, 1000, 5000]
        base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)

        for n in scales:
            bus = get_event_bus()
            bus.reset()
            sub = bus.subscribe(RealtimeChannel.OPERATIONAL, maxsize=1000)

            store = IncrementalIntelligenceStore()
            pipeline = IntelligencePipeline(store=store)

            # 1. Build Population
            tracks = []
            for i in range(n):
                cluster_id = i // 4
                in_cluster = i % 4
                lat = 37.7749 + (cluster_id % 50) * 0.009 + (in_cluster * 0.0002)
                lon = -122.4194 + (cluster_id // 50) * 0.009 + (in_cluster * 0.0002)
                tracks.append(make_track(f"TRK-{i:05d}", lat, lon, ts=base_time))

            t0 = time.perf_counter()
            store.update_tracks_batch(tracks, now=base_time)
            t_batch_ms = (time.perf_counter() - t0) * 1000.0

            # 2. REST Cached Summary Read (Pure in-memory snapshot read)
            read_iters = 1000 if n <= 1000 else 200
            t0 = time.perf_counter()
            for _ in range(read_iters):
                snap = pipeline.get_snapshot()
            t_rest_read_us = ((time.perf_counter() - t0) / read_iters) * 1_000_000.0

            # 3. Single-Track Incremental Update WITHOUT event publication
            update_iters = 50 if n <= 1000 else 20
            t0 = time.perf_counter()
            for k in range(update_iters):
                moving_track = make_track("TRK-00000", 37.7750 + k * 0.00001, -122.4194, ts=base_time)
                pipeline.process_track_update(moving_track, publish_events=False, now=base_time)
            t_update_no_events_ms = ((time.perf_counter() - t0) / update_iters) * 1000.0

            # 4. Single-Track Incremental Update WITH event publication
            # Reset sub queue
            while not sub.queue.empty():
                sub.queue.get_nowait()

            t0 = time.perf_counter()
            for k in range(update_iters):
                moving_track = make_track("TRK-00000", 37.7750 + (k + 100) * 0.00001, -122.4194, ts=base_time)
                pipeline.process_track_update(moving_track, publish_events=True, now=base_time)
            t_update_with_events_ms = ((time.perf_counter() - t0) / update_iters) * 1000.0
            t_event_overhead_ms = max(0.0, t_update_with_events_ms - t_update_no_events_ms)

            print(
                f"  [N={n:5d}] Batch Init: {t_batch_ms:7.2f}ms | "
                f"REST Read: {t_rest_read_us:6.2f}µs | "
                f"Update: {t_update_no_events_ms:5.2f}ms | "
                f"Update+Events: {t_update_with_events_ms:5.2f}ms | "
                f"Evt Overhead: {t_event_overhead_ms:5.2f}ms"
            )

            # Assertions
            assert snap is not None
            assert len(snap.priorities) == n
            assert t_rest_read_us < 1000.0, f"REST snapshot read should be sub-millisecond, took {t_rest_read_us:.2f}µs"
            if n <= 1000:
                assert t_update_no_events_ms < 15.0
                assert t_rest_read_us < 200.0
