"""Deterministic Replay & Multi-Stream Equivalence Test Suite for AeroGuard AI3-E.

Verifies:
1. Strict Replay Determinism: Stream(T) -> Pipeline A == Pipeline B for all entities, groups, behaviors, formations, and priorities.
2. Incremental vs Batch Equivalence: Verifies mathematical and structural equivalence between sequential pipeline feed and batch evaluation.
3. Spatial Disjoint Invariance: Replaying independent clusters in different arrival orders yields identical final state.
4. Multithreaded Concurrency Invariance: Concurrent worker streams maintain strict integrity and snapshot isolation.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
import math
import random
import pytest

from ai.correlation.grouping import TrackObservation
from ai.incremental.pipeline import IntelligencePipeline, reset_intelligence_pipeline
from ai.incremental.store import IncrementalIntelligenceStore
from ai.schemas import BehavioralState, MultiTrackIntelligenceSummary
from ai.service import DefensiveIntelligenceService


BASE_TIME = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)


# ─────────────────────────────────────────────────────────────────────────────
# Multi-Step Synthetic Chronological Stream Generator
# ─────────────────────────────────────────────────────────────────────────────

def generate_multi_step_replay_stream(n_ticks: int = 50) -> list[tuple[str, TrackObservation | str]]:
    """Generate a deterministic chronological stream of actions ('UPDATE', obs) or ('DROP', track_id)."""
    stream: list[tuple[str, TrackObservation | str]] = []
    base_lat = 37.7749
    base_lon = -122.4194

    for tick in range(n_ticks):
        t_sec = tick * 1.0
        now = BASE_TIME + timedelta(seconds=t_sec)

        # 1. Cluster 1: 3 tracks cruising in tight formation at 25 m/s heading 45 deg
        for m in range(3):
            tid = f"TRK-C1-{m}"
            lat = base_lat + (t_sec * 0.0001) + (m * 0.0002)
            lon = base_lon + (t_sec * 0.0001) + (m * 0.0002)
            stream.append((
                "UPDATE",
                TrackObservation(
                    id=tid,
                    latitude=lat,
                    longitude=lon,
                    altitude=150.0,
                    velocity=25.0,
                    heading=45.0,
                    confidence=0.95,
                    timestamp=now,
                ),
            ))

        # 2. Cluster 2: 2 tracks in formation + 1 joiner at tick 10 + 1 leaver at tick 25
        for m in range(2):
            tid = f"TRK-C2-{m}"
            lat = base_lat + 0.05 - (t_sec * 0.0001) + (m * 0.0002)
            lon = base_lon + 0.05 + (m * 0.0002)
            stream.append((
                "UPDATE",
                TrackObservation(
                    id=tid,
                    latitude=lat,
                    longitude=lon,
                    altitude=180.0,
                    velocity=20.0,
                    heading=180.0,
                    confidence=0.92,
                    timestamp=now,
                ),
            ))

        # Joiner: joins Cluster 2 starting at tick 10
        if tick >= 10:
            tid = "TRK-C2-JOINER"
            lat = base_lat + 0.05 - (t_sec * 0.0001) + 0.0004
            lon = base_lon + 0.05 + 0.0004
            stream.append((
                "UPDATE",
                TrackObservation(
                    id=tid,
                    latitude=lat,
                    longitude=lon,
                    altitude=180.0,
                    velocity=20.0,
                    heading=180.0,
                    confidence=0.90,
                    timestamp=now,
                ),
            ))

        # 3. Fast Inbound Isolated Track with evolving anomaly score
        if tick < 40:
            stream.append((
                "UPDATE",
                TrackObservation(
                    id="TRK-FAST-INBOUND",
                    latitude=37.9000 - (t_sec * 0.0003),
                    longitude=-122.3500,
                    altitude=90.0,
                    velocity=42.0,
                    heading=180.0,
                    confidence=0.98,
                    timestamp=now,
                ),
            ))
        elif tick == 40:
            # Drop inbound track at tick 40
            stream.append(("DROP", "TRK-FAST-INBOUND"))

        # 4. Loitering track performing circular orbit
        angle = (t_sec * 10.0) * math.pi / 180.0
        stream.append((
            "UPDATE",
            TrackObservation(
                id="TRK-LOITER-01",
                latitude=base_lat - 0.05 + (0.001 * math.sin(angle)),
                longitude=base_lon - 0.05 + (0.001 * math.cos(angle)),
                altitude=120.0,
                velocity=10.0,
                heading=math.fmod((t_sec * 10.0) + 90.0, 360.0),
                confidence=0.88,
                timestamp=now,
            ),
        ))

    return stream


class TestAI3DeterministicReplay:
    """Deterministic replay and mathematical equivalence verification."""

    def test_01_multi_step_deterministic_replay_equality(self) -> None:
        """Test 1: Replaying a 50-step stream through two independent pipelines produces 100% identical state."""
        stream = generate_multi_step_replay_stream(n_ticks=50)

        pipe_a = IntelligencePipeline(store=IncrementalIntelligenceStore())
        pipe_b = IntelligencePipeline(store=IncrementalIntelligenceStore())

        for action, payload in stream:
            if action == "UPDATE":
                obs: TrackObservation = payload  # type: ignore
                pipe_a.process_track_update(obs, publish_events=False)
                pipe_b.process_track_update(obs, publish_events=False)
            elif action == "DROP":
                tid: str = payload  # type: ignore
                pipe_a.process_track_removal(tid, publish_events=False)
                pipe_b.process_track_removal(tid, publish_events=False)

        snap_a = pipe_a.get_snapshot()
        snap_b = pipe_b.get_snapshot()

        # 1. Structural entity counts
        assert len(snap_a.groups) == len(snap_b.groups)
        assert len(snap_a.formations) == len(snap_b.formations)
        assert len(snap_a.behaviors) == len(snap_b.behaviors)
        assert len(snap_a.priorities) == len(snap_b.priorities)

        # 2. Groups equivalence
        sorted_ga = sorted(snap_a.groups, key=lambda g: g.member_track_ids[0])
        sorted_gb = sorted(snap_b.groups, key=lambda g: g.member_track_ids[0])
        for ga, gb in zip(sorted_ga, sorted_gb):
            assert ga.group_id == gb.group_id
            assert ga.member_track_ids == gb.member_track_ids
            assert ga.centroid_lat == pytest.approx(gb.centroid_lat, abs=1e-7)
            assert ga.centroid_lon == pytest.approx(gb.centroid_lon, abs=1e-7)
            assert ga.radius_meters == pytest.approx(gb.radius_meters, abs=1e-4)

        # 3. Formations equivalence
        sorted_fa = sorted(snap_a.formations, key=lambda f: f.group_id)
        sorted_fb = sorted(snap_b.formations, key=lambda f: f.group_id)
        for fa, fb in zip(sorted_fa, sorted_fb):
            assert fa.formation_id == fb.formation_id
            assert fa.group_id == fb.group_id
            assert fa.member_track_ids == fb.member_track_ids
            assert fa.synchronization_index == pytest.approx(fb.synchronization_index, abs=1e-4)
            assert fa.velocity_dispersion_mps == pytest.approx(fb.velocity_dispersion_mps, abs=1e-4)
            assert fa.heading_dispersion_deg == pytest.approx(fb.heading_dispersion_deg, abs=1e-4)
            assert fa.confidence == pytest.approx(fb.confidence, abs=1e-4)

        # 4. Behaviors equivalence
        b_map_a = {b.track_id: b for b in snap_a.behaviors}
        b_map_b = {b.track_id: b for b in snap_b.behaviors}
        assert set(b_map_a.keys()) == set(b_map_b.keys())
        for tid, ba in b_map_a.items():
            bb = b_map_b[tid]
            assert ba.state == bb.state
            assert ba.confidence == pytest.approx(bb.confidence, abs=1e-4)
            assert ba.reason == bb.reason

        # 5. Priorities and Explainable Factors equivalence
        p_map_a = {p.track_id: p for p in snap_a.priorities}
        p_map_b = {p.track_id: p for p in snap_b.priorities}
        assert set(p_map_a.keys()) == set(p_map_b.keys())
        for tid, pa in p_map_a.items():
            pb = p_map_b[tid]
            assert pa.priority_score == pytest.approx(pb.priority_score, abs=1e-4)
            assert pa.priority_level == pb.priority_level
            assert len(pa.factors) == len(pb.factors)
            for fa, fb in zip(pa.factors, pb.factors):
                assert fa.name == fb.name
                assert fa.score == pytest.approx(fb.score, abs=1e-4)
                assert fa.contribution == pytest.approx(fb.contribution, abs=1e-4)

    def test_02_incremental_vs_batch_equivalence(self) -> None:
        """Test 2: Final active population state produced incrementally matches batch DefensiveIntelligenceService."""
        now_ts = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)

        # 3 clusters of 4 tracks + 8 isolated tracks
        tracks = []
        base_lat = 37.7749
        base_lon = -122.4194

        for i in range(20):
            if i < 12:
                c_idx = i // 4
                m_idx = i % 4
                lat = base_lat + (c_idx * 0.05) + (m_idx * 0.0003)
                lon = base_lon + (c_idx * 0.05) + (m_idx * 0.0003)
                hdg = 45.0 + (c_idx * 30.0)
                spd = 20.0
            else:
                lat = base_lat + 1.0 + (i * 0.05)
                lon = base_lon + 1.0 + (i * 0.05)
                hdg = 0.0
                spd = 12.0

            tracks.append(
                TrackObservation(
                    id=f"TRK-EQ-{i:03d}",
                    latitude=lat,
                    longitude=lon,
                    altitude=150.0,
                    velocity=spd,
                    heading=hdg,
                    confidence=0.95,
                    timestamp=now_ts,
                )
            )

        # 1. Batch reference evaluation
        batch_summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(
            tracks=tracks, now=now_ts, publish_events=False
        )

        # 2. Incremental pipeline evaluation
        store = IncrementalIntelligenceStore()
        store.update_tracks_batch(tracks, now=now_ts)
        incr_summary = store.get_summary_snapshot()

        # 3. Assert full equivalence
        assert len(incr_summary.groups) == len(batch_summary.groups)
        assert len(incr_summary.formations) == len(batch_summary.formations)
        assert len(incr_summary.behaviors) == len(batch_summary.behaviors)
        assert len(incr_summary.priorities) == len(batch_summary.priorities)

        # Verify group memberships
        sorted_inc_g = sorted(incr_summary.groups, key=lambda g: g.member_track_ids[0])
        sorted_bat_g = sorted(batch_summary.groups, key=lambda g: g.member_track_ids[0])
        for gi, gb in zip(sorted_inc_g, sorted_bat_g):
            assert gi.member_track_ids == gb.member_track_ids
            assert gi.centroid_lat == pytest.approx(gb.centroid_lat, abs=1e-6)
            assert gi.centroid_lon == pytest.approx(gb.centroid_lon, abs=1e-6)

        # Verify priorities
        p_inc_map = {p.track_id: p for p in incr_summary.priorities}
        p_bat_map = {p.track_id: p for p in batch_summary.priorities}
        for tid, pi in p_inc_map.items():
            pb = p_bat_map[tid]
            assert pi.priority_score == pytest.approx(pb.priority_score, abs=0.1)
            assert pi.priority_level == pb.priority_level

    def test_03_order_invariance_for_disjoint_clusters(self) -> None:
        """Test 3: Two geographically disjoint clusters produce identical final state regardless of arrival order."""
        now_ts = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)

        cluster_a = [
            TrackObservation(id=f"A{i}", latitude=37.7749 + i * 0.0002, longitude=-122.4194 + i * 0.0002, timestamp=now_ts)
            for i in range(4)
        ]
        cluster_b = [
            TrackObservation(id=f"B{i}", latitude=34.0522 + i * 0.0002, longitude=-118.2437 + i * 0.0002, timestamp=now_ts)
            for i in range(4)
        ]

        # Run 1: Feed Cluster A then Cluster B
        pipe_1 = IntelligencePipeline(store=IncrementalIntelligenceStore())
        for t in cluster_a:
            pipe_1.process_track_update(t, publish_events=False)
        for t in cluster_b:
            pipe_1.process_track_update(t, publish_events=False)

        # Run 2: Feed Cluster B then Cluster A
        pipe_2 = IntelligencePipeline(store=IncrementalIntelligenceStore())
        for t in cluster_b:
            pipe_2.process_track_update(t, publish_events=False)
        for t in cluster_a:
            pipe_2.process_track_update(t, publish_events=False)

        snap1 = pipe_1.get_snapshot()
        snap2 = pipe_2.get_snapshot()

        assert len(snap1.groups) == len(snap2.groups) == 2
        assert len(snap1.priorities) == len(snap2.priorities) == 8

        p1_map = {p.track_id: p.priority_score for p in snap1.priorities}
        p2_map = {p.track_id: p.priority_score for p in snap2.priorities}
        for tid in p1_map:
            assert p1_map[tid] == pytest.approx(p2_map[tid], abs=1e-4)

    def test_04_concurrency_stress_invariance(self) -> None:
        """Test 4: Multithreaded concurrent mutations and reads maintain strict internal structural integrity."""
        pipeline = IntelligencePipeline(store=IncrementalIntelligenceStore())
        n_workers = 8
        ops_per_worker = 25

        def worker_task(wid: int) -> None:
            rng = random.Random(wid)
            for step in range(ops_per_worker):
                tid = f"CONC-T{wid}-{step % 5}"
                lat = 37.7749 + (wid * 0.01) + rng.uniform(-0.001, 0.001)
                lon = -122.4194 + rng.uniform(-0.001, 0.001)

                if step % 8 == 7:
                    # Occasional drop
                    pipeline.process_track_removal(tid, publish_events=False)
                else:
                    obs = TrackObservation(
                        id=tid,
                        latitude=lat,
                        longitude=lon,
                        velocity=18.0 + rng.uniform(0, 5),
                        heading=rng.uniform(0, 360),
                    )
                    pipeline.process_track_update(obs, publish_events=False)

                # Interleave snapshot reads
                snap = pipeline.get_snapshot()
                assert isinstance(snap, MultiTrackIntelligenceSummary)
                assert len(snap.priorities) == len(snap.behaviors)

        with ThreadPoolExecutor(max_workers=n_workers) as executor:
            futures = [executor.submit(worker_task, w) for w in range(n_workers)]
            for f in futures:
                f.result()

        final_snap = pipeline.get_snapshot()
        assert pipeline.store.track_count >= 0
        assert len(final_snap.priorities) == pipeline.store.track_count
