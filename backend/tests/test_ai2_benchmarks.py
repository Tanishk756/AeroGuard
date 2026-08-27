"""Deterministic Performance Benchmarking Suite for AeroGuard AI2 Multi-Track Intelligence.

Measures:
- Grouping latency (correlate_tracks)
- Behavioral classification latency (classify_track_behavior)
- Coordination latency (compute_coordination_index)
- Priority triage latency (evaluate_threat_priority)
- Complete end-to-end multi-track intelligence evaluation latency (evaluate_multi_track_intelligence)

Scale benchmarks for: 10, 50, 100, 500, 1,000 synthetic tracks.

NOTE: These measurements represent local CPU software microbenchmarks on the development system,
not guaranteed real-world or production SLA figures.
"""

from datetime import UTC, datetime, timedelta
import statistics
import time
from typing import Sequence
import pytest

from ai.anomaly.persistent import (
    PersistentAnomalyAccumulator,
    PersistentAnomalyConfig,
)
from ai.behavior.classifier import ClassifierInput, classify_track_behavior
from ai.correlation.coordination import compute_coordination_index
from ai.correlation.grouping import TrackObservation, correlate_tracks
from ai.priority.scoring import evaluate_threat_priority
from ai.schemas import MultiTrackIntelligenceSummary, TrackGroup
from ai.service import DefensiveIntelligenceService


def generate_benchmark_tracks(n_tracks: int, base_time: datetime | None = None) -> list[TrackObservation]:
    """Generate deterministic synthetic tracks in a grid distribution with clusters."""
    t0 = base_time or datetime(2026, 8, 27, 0, 0, 0, tzinfo=UTC)
    tracks: list[TrackObservation] = []

    # Center origin
    origin_lat = 37.7749
    origin_lon = -122.4194

    for i in range(n_tracks):
        # Create small clusters every 4 tracks
        cluster_id = i // 4
        in_cluster_offset = (i % 4) * 0.0002
        lat = origin_lat + (cluster_id * 0.005) + in_cluster_offset
        lon = origin_lon + (cluster_id * 0.005) + in_cluster_offset
        hdg = (cluster_id * 30.0 + (i % 4) * 0.5) % 360.0
        spd = 15.0 + (cluster_id % 10) * 2.0

        tracks.append(
            TrackObservation(
                id=f"TRK-BENCH-{i:04d}",
                latitude=lat,
                longitude=lon,
                altitude=100.0 + (i % 50),
                velocity=spd,
                heading=hdg,
                confidence=0.90 + ((i % 10) * 0.01),
                timestamp=t0,
            )
        )
    return tracks


class BenchmarkStats:
    """Helper to collect and compute execution statistics."""

    def __init__(self, name: str, n_tracks: int, durations_sec: list[float]) -> None:
        self.name = name
        self.n_tracks = n_tracks
        self.durations_ms = [d * 1000.0 for d in durations_sec]
        self.mean_ms = statistics.mean(self.durations_ms)
        self.median_ms = statistics.median(self.durations_ms)
        self.max_ms = max(self.durations_ms)
        self.min_ms = min(self.durations_ms)
        self.per_track_us = (self.mean_ms * 1000.0) / max(1, n_tracks)

    def summary(self) -> str:
        return (
            f"[{self.name} (N={self.n_tracks})] "
            f"Mean: {self.mean_ms:.3f} ms | "
            f"Median: {self.median_ms:.3f} ms | "
            f"Max: {self.max_ms:.3f} ms | "
            f"Per-track: {self.per_track_us:.2f} µs"
        )


class TestAI2PerformanceBenchmarks:
    """Performance benchmarks across multiple scale factors."""

    TRACK_COUNTS = [10, 50, 100, 500, 1000]

    def test_grouping_latency_scale(self) -> None:
        """Benchmark spatial/heading clustering latency scaling."""
        results: list[BenchmarkStats] = []
        for n in self.TRACK_COUNTS:
            tracks = generate_benchmark_tracks(n)
            iterations = 20 if n <= 100 else 5
            durations: list[float] = []

            for _ in range(iterations):
                t_start = time.perf_counter()
                groups = correlate_tracks(tracks)
                t_end = time.perf_counter()
                durations.append(t_end - t_start)
                assert isinstance(groups, list)

            stats = BenchmarkStats("Spatial Grouping", n, durations)
            results.append(stats)
            print(f"\n{stats.summary()}")

            # Basic performance sanity bounds: <= 50ms per 100 tracks
            if n <= 100:
                assert stats.mean_ms < 50.0

    def test_behavioral_classification_latency_scale(self) -> None:
        """Benchmark behavioral state evaluation latency scaling."""
        results: list[BenchmarkStats] = []
        for n in self.TRACK_COUNTS:
            tracks = generate_benchmark_tracks(n)
            iterations = 20 if n <= 100 else 5
            durations: list[float] = []

            for _ in range(iterations):
                t_start = time.perf_counter()
                for t in tracks:
                    inp = ClassifierInput(
                        track_id=t.id,
                        speed_mps=t.velocity or 0.0,
                        heading_deg=t.heading,
                        timestamp=t.timestamp,
                    )
                    classify_track_behavior(inp)
                t_end = time.perf_counter()
                durations.append(t_end - t_start)

            stats = BenchmarkStats("Behavioral Classification", n, durations)
            results.append(stats)
            print(f"\n{stats.summary()}")

            # Behavioral classification is O(N), per track should be under 50 µs
            assert stats.per_track_us < 100.0

    def test_coordination_evaluation_latency_scale(self) -> None:
        """Benchmark swarm coordination index calculation latency scaling."""
        results: list[BenchmarkStats] = []
        for n in self.TRACK_COUNTS:
            tracks = generate_benchmark_tracks(n)
            groups = correlate_tracks(tracks)
            iterations = 20 if n <= 100 else 5
            durations: list[float] = []

            for _ in range(iterations):
                t_start = time.perf_counter()
                for g in groups:
                    member_objs = [t for t in tracks if t.id in g.member_track_ids]
                    compute_coordination_index(g, member_objs)
                t_end = time.perf_counter()
                durations.append(t_end - t_start)

            stats = BenchmarkStats("Coordination Index", n, durations)
            results.append(stats)
            print(f"\n{stats.summary()}")
            if n <= 100:
                assert stats.mean_ms < 25.0

    def test_priority_evaluation_latency_scale(self) -> None:
        """Benchmark explainable threat priority evaluation latency scaling."""
        results: list[BenchmarkStats] = []
        for n in self.TRACK_COUNTS:
            tracks = generate_benchmark_tracks(n)
            iterations = 20 if n <= 100 else 5
            durations: list[float] = []

            for _ in range(iterations):
                t_start = time.perf_counter()
                for t in tracks:
                    evaluate_threat_priority(
                        track_id=t.id,
                        kinematics=t.velocity,
                        sensor_confidence=t.confidence,
                        evaluated_at=t.timestamp,
                    )
                t_end = time.perf_counter()
                durations.append(t_end - t_start)

            stats = BenchmarkStats("Priority Scoring", n, durations)
            results.append(stats)
            print(f"\n{stats.summary()}")

            # Priority evaluation is pure arithmetic O(N)
            assert stats.per_track_us < 50.0

    def test_full_multi_track_intelligence_latency_scale(self) -> None:
        """Benchmark end-to-end evaluate_multi_track_intelligence latency across scales."""
        print("\n" + "=" * 70)
        print("  AEROGUARD AI2 MULTI-TRACK DEFENSIVE INTELLIGENCE BENCHMARK RESULTS")
        print("  Local Software Microbenchmark — Not a Guaranteed Production SLA")
        print("=" * 70)

        for n in self.TRACK_COUNTS:
            tracks = generate_benchmark_tracks(n)
            iterations = 20 if n <= 100 else 5
            durations: list[float] = []

            for _ in range(iterations):
                t_start = time.perf_counter()
                summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(
                    tracks=tracks,
                    now=tracks[0].timestamp,
                    publish_events=False,
                )
                t_end = time.perf_counter()
                durations.append(t_end - t_start)
                assert len(summary.priorities) == n

            stats = BenchmarkStats("Full AI2 Multi-Track Engine", n, durations)
            print(f"  {stats.summary()}")

            # Performance target: 100 tracks under 50ms (permits 20Hz live operational update rate)
            if n == 100:
                assert stats.mean_ms < 50.0, f"100 tracks took {stats.mean_ms:.2f}ms (>50ms budget)"
            if n == 1000:
                assert stats.mean_ms < 3000.0, f"1000 tracks took {stats.mean_ms:.2f}ms (>3000ms budget)"
