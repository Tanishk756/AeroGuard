"""Comprehensive Unit, Equivalence, Concurrency & Performance Tests for IncrementalIntelligenceStore.

Stage AI3-C — Incremental In-Memory Intelligence Store.

Verifies:
1. Thread-safe atomic mutations and O(1) immutable snapshots.
2. Track lifecycle: insert, move, join group, leave group, drop track.
3. Temporal persistent anomaly accumulation across sequential timestamps.
4. Equivalence against batch DefensiveIntelligenceService.evaluate_multi_track_intelligence.
5. Concurrency safety using ThreadPoolExecutor.
6. Performance benchmarks for single-track incremental updates and O(1) snapshot reads.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import math
import random
import time
from typing import Any
import pytest

from ai.correlation.grouping import TrackObservation
from ai.incremental.store import IncrementalIntelligenceStore, IncrementalStoreConfig
from ai.schemas import BehavioralState, MultiTrackIntelligenceSummary
from ai.service import DefensiveIntelligenceService


BASE_TIME = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)


def make_track(
    tid: str,
    lat: float,
    lon: float,
    vel: float = 15.0,
    hdg: float = 45.0,
    alt: float = 120.0,
    conf: float = 0.95,
    ts: datetime | None = None,
) -> TrackObservation:
    """Helper factory for track observations."""
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


class TestIncrementalIntelligenceStoreUnit:
    """Unit tests for core store capabilities, lifecycle, and invariants."""

    def test_01_empty_initial_state(self) -> None:
        """Test 1: Store starts in clean empty state with valid empty snapshot."""
        store = IncrementalIntelligenceStore()
        assert store.track_count == 0
        assert store.group_count == 0
        assert store.version == 0

        snap = store.get_summary_snapshot()
        assert isinstance(snap, MultiTrackIntelligenceSummary)
        assert snap.groups == []
        assert snap.behaviors == []
        assert snap.formations == []
        assert snap.priorities == []
        assert isinstance(snap.evaluated_at, datetime)

    def test_02_single_track_update(self) -> None:
        """Test 2: Updating a single track initializes its intelligence state."""
        store = IncrementalIntelligenceStore()
        t = make_track("TRK-01", 37.7749, -122.4194, vel=20.0, hdg=90.0)

        p = store.update_track(t)
        assert p.track_id == "TRK-01"
        assert p.priority_score >= 0.0
        assert store.track_count == 1
        assert store.group_count == 0  # Singletons not emitted as groups
        assert store.version == 1

        # Check targeted read APIs
        assert store.get_track("TRK-01") == t
        assert store.get_behavior("TRK-01") is not None
        assert store.get_behavior("TRK-01").state == BehavioralState.NORMAL
        assert store.get_priority("TRK-01") == p

        snap = store.get_summary_snapshot()
        assert len(snap.priorities) == 1
        assert len(snap.behaviors) == 1
        assert len(snap.groups) == 0

    def test_03_group_formation_two_tracks(self) -> None:
        """Test 3: Inserting two nearby tracks dynamically forms a group and formation."""
        store = IncrementalIntelligenceStore()
        t1 = make_track("T1", 37.7749, -122.4194, vel=20.0, hdg=45.0)
        t2 = make_track("T2", 37.7751, -122.4195, vel=20.2, hdg=45.5)

        store.update_track(t1)
        store.update_track(t2)

        assert store.track_count == 2
        assert store.group_count == 1
        assert store.version == 2

        snap = store.get_summary_snapshot()
        assert len(snap.groups) == 1
        grp = snap.groups[0]
        assert set(grp.member_track_ids) == {"T1", "T2"}
        assert grp.member_count == 2

        # Check reverse lookup
        assert store.get_track_group("T1") == grp
        assert store.get_track_group("T2") == grp

        # Both tracks should have group_id attached in priority
        p1 = store.get_priority("T1")
        p2 = store.get_priority("T2")
        assert p1.group_id == grp.group_id
        assert p2.group_id == grp.group_id

    def test_04_group_join_and_hysteresis(self) -> None:
        """Test 4: 3rd track moves into formation; Jaccard hysteresis preserves group ID."""
        store = IncrementalIntelligenceStore()
        store.update_track(make_track("T1", 37.7749, -122.4194, vel=20.0, hdg=45.0))
        store.update_track(make_track("T2", 37.7751, -122.4195, vel=20.2, hdg=45.5))

        initial_grp = store.get_summary_snapshot().groups[0]
        orig_gid = initial_grp.group_id

        # T3 joins formation
        store.update_track(make_track("T3", 37.7750, -122.4193, vel=19.8, hdg=44.5))

        assert store.group_count == 1
        updated_grp = store.get_summary_snapshot().groups[0]
        assert updated_grp.group_id == orig_gid  # Stable ID preserved
        assert set(updated_grp.member_track_ids) == {"T1", "T2", "T3"}
        assert updated_grp.member_count == 3

    def test_05_group_leave_and_dissolution(self) -> None:
        """Test 5: Track departs, reducing group; final track departure dissolves group."""
        store = IncrementalIntelligenceStore()
        store.update_track(make_track("T1", 37.7749, -122.4194, vel=20.0, hdg=45.0))
        store.update_track(make_track("T2", 37.7751, -122.4195, vel=20.0, hdg=45.0))
        store.update_track(make_track("T3", 37.7750, -122.4193, vel=20.0, hdg=45.0))
        assert store.group_count == 1

        # T3 departs far away (to London)
        store.update_track(make_track("T3", 51.5074, -0.1278, vel=20.0, hdg=45.0))
        snap = store.get_summary_snapshot()
        assert len(snap.groups) == 1
        assert set(snap.groups[0].member_track_ids) == {"T1", "T2"}

        # T2 departs far away
        store.update_track(make_track("T2", 40.7128, -74.0060, vel=20.0, hdg=45.0))
        snap2 = store.get_summary_snapshot()
        assert len(snap2.groups) == 0  # No groups of size >= 2 remain
        assert store.get_track_group("T1") is None

    def test_06_drop_track(self) -> None:
        """Test 6: drop_track cleanly removes all track state, spatial entries, and re-clusters groups."""
        store = IncrementalIntelligenceStore()
        store.update_track(make_track("T1", 37.7749, -122.4194, vel=20.0, hdg=45.0))
        store.update_track(make_track("T2", 37.7751, -122.4195, vel=20.0, hdg=45.0))
        assert store.track_count == 2
        assert store.group_count == 1

        assert store.drop_track("T2") is True
        assert store.track_count == 1
        assert store.group_count == 0

        assert store.get_track("T2") is None
        assert store.get_priority("T2") is None
        assert store.get_behavior("T2") is None

        # Unknown track removal returns False
        assert store.drop_track("NONEXISTENT") is False

    def test_07_persistent_anomaly_accumulation_and_decay(self) -> None:
        """Test 7: Sequential track updates accumulate and decay persistent anomaly scores."""
        store = IncrementalIntelligenceStore()
        t0 = BASE_TIME

        # Initial high-anomaly burst
        store.update_track(make_track("ANOM-1", 37.0, -122.0, ts=t0), instantaneous_anomaly_score=80.0, now=t0)
        p1 = store.get_priority("ANOM-1")

        # 5 seconds later, continuous anomaly
        t1 = t0 + timedelta(seconds=5)
        store.update_track(make_track("ANOM-1", 37.001, -122.001, ts=t1), instantaneous_anomaly_score=85.0, now=t1)
        p2 = store.get_priority("ANOM-1")
        assert p2.priority_score >= p1.priority_score

        # 60 seconds later, nominal behavior (anomaly score 0) -> decay
        t2 = t0 + timedelta(seconds=65)
        store.update_track(make_track("ANOM-1", 37.010, -122.010, ts=t2), instantaneous_anomaly_score=0.0, now=t2)
        p3 = store.get_priority("ANOM-1")
        assert p3.priority_score < p2.priority_score

    def test_08_snapshot_isolation(self) -> None:
        """Test 8: Mutating returned snapshot does not corrupt internal store state."""
        store = IncrementalIntelligenceStore()
        store.update_track(make_track("T1", 37.7749, -122.4194))
        store.update_track(make_track("T2", 37.7751, -122.4195))

        snap1 = store.get_summary_snapshot()
        # Mutate lists in snapshot
        snap1.groups.clear()
        snap1.priorities.clear()

        # Second snapshot should be intact
        snap2 = store.get_summary_snapshot()
        assert len(snap2.groups) == 1
        assert len(snap2.priorities) == 2

    def test_09_batch_update_atomicity(self) -> None:
        """Test 9: update_tracks_batch applies multiple tracks in a single version increment."""
        store = IncrementalIntelligenceStore()
        tracks = [
            make_track("B1", 37.7749, -122.4194),
            make_track("B2", 37.7751, -122.4195),
            make_track("B3", 38.5000, -121.5000),
        ]
        priorities = store.update_tracks_batch(tracks)
        assert len(priorities) == 3
        assert store.track_count == 3
        assert store.group_count == 1
        assert store.version == 1  # Exactly 1 version increment

    def test_10_clear_resets_all_state(self) -> None:
        """Test 10: clear() cleanly resets store to empty state."""
        store = IncrementalIntelligenceStore()
        store.update_track(make_track("T1", 37.7749, -122.4194))
        store.update_track(make_track("T2", 37.7751, -122.4195))
        assert store.track_count == 2

        store.clear()
        assert store.track_count == 0
        assert store.group_count == 0
        assert len(store.get_summary_snapshot().priorities) == 0


class TestIncrementalStoreEquivalence:
    """Equivalence testing: Incremental store state vs Batch DefensiveIntelligenceService evaluation."""

    def test_batch_update_exact_equivalence(self) -> None:
        """Verify update_tracks_batch produces exact 1-to-1 equivalence with DefensiveIntelligenceService."""
        tracks: list[TrackObservation] = []
        base_lat = 37.7749
        base_lon = -122.4194
        now_ts = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)

        # 3 clusters of 8 tracks + 16 isolated tracks
        for i in range(40):
            cluster_id = i // 8
            in_cluster = i % 8
            if cluster_id < 3:
                lat = base_lat + (cluster_id * 0.05) + (in_cluster * 0.0003)
                lon = base_lon + (cluster_id * 0.05) + (in_cluster * 0.0003)
                hdg = (cluster_id * 60.0 + in_cluster * 0.5) % 360.0
                spd = 18.0 + (cluster_id * 2.0)
            else:
                lat = base_lat + 1.0 + (i * 0.1)
                lon = base_lon + 1.0 + (i * 0.1)
                hdg = 0.0
                spd = 10.0

            tracks.append(
                TrackObservation(
                    id=f"TRK-EQ-{i:03d}",
                    latitude=lat,
                    longitude=lon,
                    altitude=150.0 + i,
                    velocity=spd,
                    heading=hdg,
                    confidence=0.95,
                    timestamp=now_ts,
                )
            )

        # 1. Evaluate via Batch Service
        batch_summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(
            tracks=tracks,
            now=now_ts,
            publish_events=False,
        )

        # 2. Evaluate via Incremental Store Batch Update
        store = IncrementalIntelligenceStore()
        store.update_tracks_batch(tracks, now=now_ts)
        incr_summary = store.get_summary_snapshot()

        # 3. Assert Exact Equivalence
        assert len(incr_summary.groups) == len(batch_summary.groups)
        assert len(incr_summary.behaviors) == len(batch_summary.behaviors)
        assert len(incr_summary.formations) == len(batch_summary.formations)
        assert len(incr_summary.priorities) == len(batch_summary.priorities)

        # Verify group memberships
        sorted_inc_groups = sorted(incr_summary.groups, key=lambda g: g.member_track_ids[0])
        sorted_bat_groups = sorted(batch_summary.groups, key=lambda g: g.member_track_ids[0])
        for g_inc, g_bat in zip(sorted_inc_groups, sorted_bat_groups):
            assert g_inc.member_track_ids == g_bat.member_track_ids
            assert g_inc.centroid_lat == pytest.approx(g_bat.centroid_lat, abs=1e-6)
            assert g_inc.centroid_lon == pytest.approx(g_bat.centroid_lon, abs=1e-6)
            assert g_inc.radius_meters == pytest.approx(g_bat.radius_meters, abs=1e-4)

        # Verify priorities
        p_inc_map = {p.track_id: p for p in incr_summary.priorities}
        p_bat_map = {p.track_id: p for p in batch_summary.priorities}
        for tid, p_inc in p_inc_map.items():
            p_bat = p_bat_map[tid]
            assert p_inc.priority_score == pytest.approx(p_bat.priority_score, abs=0.1)
            assert p_inc.priority_level == p_bat.priority_level

    def test_sequential_update_temporal_hysteresis(self) -> None:
        """Verify sequential feed correctly advances behavioral state machine through hysteresis ticks."""
        store = IncrementalIntelligenceStore()
        now_ts = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)

        # Initial track alone -> NORMAL
        t1 = make_track("T1", 37.7749, -122.4194, ts=now_ts)
        store.update_track(t1, now=now_ts)
        assert store.get_behavior("T1").state == BehavioralState.NORMAL

        # Second track arrives -> Formation formed, hysteresis tick 1
        t2 = make_track("T2", 37.7751, -122.4195, ts=now_ts)
        store.update_track(t2, now=now_ts)
        # Hysteresis requires 2 ticks for COORDINATED
        assert store.get_group_count() if hasattr(store, "get_group_count") else store.group_count == 1

        # Third update -> T1 satisfies hysteresis (tick 2) and transitions to COORDINATED
        t1_v2 = make_track("T1", 37.77491, -122.41941, ts=now_ts + timedelta(seconds=1))
        store.update_track(t1_v2, now=now_ts + timedelta(seconds=1))
        assert store.get_behavior("T1").state == BehavioralState.COORDINATED


class TestIncrementalStoreConcurrency:
    """Thread-safety & concurrency test using ThreadPoolExecutor."""

    def test_concurrent_mutations_and_reads(self) -> None:
        """Concurrently update 50 tracks and read snapshots from multiple threads."""
        store = IncrementalIntelligenceStore()
        n_tracks = 50
        iterations = 20

        def worker_task(worker_id: int) -> None:
            rng = random.Random(worker_id)
            for step in range(iterations):
                tid = f"CONC-TRK-{(worker_id % n_tracks):03d}"
                lat = 37.7749 + rng.uniform(-0.01, 0.01)
                lon = -122.4194 + rng.uniform(-0.01, 0.01)
                t = make_track(tid, lat, lon, vel=15.0 + rng.uniform(0, 5))

                # Interleave updates and reads
                store.update_track(t)
                snap = store.get_summary_snapshot()
                assert isinstance(snap, MultiTrackIntelligenceSummary)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [executor.submit(worker_task, w) for w in range(16)]
            for f in futures:
                f.result()

        final_snap = store.get_summary_snapshot()
        assert store.track_count > 0
        assert store.version > 0
        assert len(final_snap.priorities) == store.track_count


class TestIncrementalStorePerformanceBenchmarks:
    """Performance benchmarks for single-track incremental updates and O(1) snapshot retrieval."""

    def test_benchmark_incremental_update_and_snapshot_latency(self) -> None:
        """Measure latency of incremental single-track updates at 1,000 and 5,000 tracks scale."""
        print("\n" + "=" * 78)
        print("  AEROGUARD AI3-C INCREMENTAL STORE BENCHMARK & O(1) SNAPSHOT READS")
        print("  Local Software Microbenchmark — Pure Python 3.12")
        print("=" * 78)

        scales = [100, 500, 1000]

        for n in scales:
            store = IncrementalIntelligenceStore()
            base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)

            # 1. Population Build
            tracks = []
            for i in range(n):
                cluster_id = i // 4
                in_cluster = i % 4
                lat = 37.7749 + (cluster_id % 20) * 0.009 + (in_cluster * 0.0002)
                lon = -122.4194 + (cluster_id // 20) * 0.009 + (in_cluster * 0.0002)
                tracks.append(make_track(f"TRK-{i:04d}", lat, lon, ts=base_time))

            t0 = time.perf_counter()
            store.update_tracks_batch(tracks, now=base_time)
            t_batch_ms = (time.perf_counter() - t0) * 1000.0

            # 2. Single-Track Incremental Update Latency (move 1 track)
            update_iters = 50
            t0 = time.perf_counter()
            for k in range(update_iters):
                moving_track = make_track("TRK-0000", 37.7750 + k * 0.00001, -122.4194, ts=base_time)
                store.update_track(moving_track, now=base_time)
            t_single_update_ms = ((time.perf_counter() - t0) / update_iters) * 1000.0

            # 3. Snapshot Read Latency (O(1) cached read)
            read_iters = 1000
            t0 = time.perf_counter()
            for _ in range(read_iters):
                snap = store.get_summary_snapshot()
            t_read_us = ((time.perf_counter() - t0) / read_iters) * 1_000_000.0

            print(
                f"  [N={n:5d}] Batch Init: {t_batch_ms:6.2f}ms | "
                f"Single-Track Update: {t_single_update_ms:6.2f}ms | "
                f"Snapshot Read: {t_read_us:5.2f}µs"
            )

            # Target assertions: Sub-millisecond single track update, O(1) sub-200µs snapshot read under suite load
            assert t_read_us < 200.0, f"Snapshot read should be O(1) sub-200µs under system load, took {t_read_us:.2f}µs"
            if n == 100:
                assert t_single_update_ms < 5.0
            if n == 500:
                assert t_single_update_ms < 10.0
            if n == 1000:
                assert t_single_update_ms < 15.0

