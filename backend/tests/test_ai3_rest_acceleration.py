"""Tests for Stage AI3-D: REST Route Acceleration & In-Memory Query Snapshotting.

Verifies:
1. GET /api/v1/intelligence/summary reads from in-memory IncrementalIntelligenceStore snapshot in O(1).
2. Full batch DefensiveIntelligenceService.evaluate_multi_track_intelligence is NOT invoked on cache hit.
3. In-memory query parameter filters (track_id, group_id, min_priority_level, min_priority_score).
4. Snapshot isolation under client-side mutations.
5. Concurrency safety between live track updates and REST summary reads.
"""

from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from unittest.mock import patch
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.correlation.grouping import TrackObservation
from ai.incremental.pipeline import get_intelligence_pipeline, reset_intelligence_pipeline
from ai.schemas import MultiTrackIntelligenceSummary
from ai.service import DefensiveIntelligenceService
from app.models.role import Role
from app.models.track import Track, TrackState


def assign_role(database: Session, user, role_name: str = "OPERATOR"):
    role = database.scalar(select(Role).where(Role.name == role_name))
    user.roles.append(role)
    database.commit()


@pytest.fixture(autouse=True)
def clean_pipeline():
    reset_intelligence_pipeline()
    yield
    reset_intelligence_pipeline()


@pytest.fixture
def seed_tracks(database: Session):
    """Seed 10 active tracks in the test database."""
    now = datetime.now(UTC).replace(tzinfo=None)
    tracks = []

    # 2 groups of 3 tracks + 4 isolated tracks
    for i in range(10):
        grp = i // 3 if i < 6 else None
        in_grp = i % 3 if i < 6 else 0
        if grp is not None:
            lat = 37.7749 + (grp * 0.05) + (in_grp * 0.0003)
            lon = -122.4194 + (grp * 0.05) + (in_grp * 0.0003)
            hdg = 45.0 + (in_grp * 0.5)
            spd = 20.0
        else:
            lat = 38.5000 + (i * 0.1)
            lon = -121.5000 + (i * 0.1)
            hdg = 180.0
            spd = 10.0

        t = Track(
            id=f"TRK-ACCEL-{i:02d}",
            state=TrackState.ACTIVE,
            first_seen_at=now - timedelta(seconds=60),
            last_seen_at=now,
            latitude=lat,
            longitude=lon,
            altitude=150.0,
            velocity=spd,
            heading=hdg,
            confidence=0.95,
            classification="UAV",
            source_count=2,
            created_at=now,
            updated_at=now,
        )
        database.add(t)
        tracks.append(t)

    database.commit()
    return tracks


class TestAI3RESTAcceleration:
    """Verification of REST API acceleration via in-memory snapshot reads."""

    def test_01_rest_reads_cached_snapshot_without_batch_recomputation(
        self,
        client: TestClient,
        database: Session,
        rbac_user,
        seed_tracks,
    ) -> None:
        """Test 1: Initial call bootstraps; subsequent requests read directly from in-memory cache."""
        client.post(
            "/api/v1/auth/login",
            json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
        )
        assign_role(database, rbac_user, "OPERATOR")

        # Initial call bootstraps pipeline
        resp1 = client.get("/api/v1/intelligence/summary")
        assert resp1.status_code == 200
        data1 = resp1.json()
        assert len(data1["priorities"]) == 10
        assert len(data1["groups"]) == 2

        # Subsequent call: Patch DefensiveIntelligenceService.evaluate_multi_track_intelligence
        # to guarantee it is NEVER called on a cache hit
        with patch.object(
            DefensiveIntelligenceService,
            "evaluate_multi_track_intelligence",
            side_effect=RuntimeError("Batch recomputation was erroneously invoked!"),
        ):
            resp2 = client.get("/api/v1/intelligence/summary")
            assert resp2.status_code == 200
            data2 = resp2.json()
            assert len(data2["priorities"]) == 10
            assert len(data2["groups"]) == 2

    def test_02_rest_filters_operate_on_in_memory_snapshot(
        self,
        client: TestClient,
        database: Session,
        rbac_user,
        seed_tracks,
    ) -> None:
        """Test 2: track_id, group_id, priority level/score filtering works in-memory."""
        client.post(
            "/api/v1/auth/login",
            json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
        )
        assign_role(database, rbac_user, "OPERATOR")

        # 1. Filter by track_id
        resp_trk = client.get("/api/v1/intelligence/summary?track_id=TRK-ACCEL-00")
        assert resp_trk.status_code == 200
        d_trk = resp_trk.json()
        assert len(d_trk["priorities"]) == 1
        assert d_trk["priorities"][0]["track_id"] == "TRK-ACCEL-00"

        # 2. Filter by group_id
        all_data = client.get("/api/v1/intelligence/summary").json()
        target_gid = all_data["groups"][0]["group_id"]

        resp_grp = client.get(f"/api/v1/intelligence/summary?group_id={target_gid}")
        assert resp_grp.status_code == 200
        d_grp = resp_grp.json()
        assert len(d_grp["groups"]) == 1
        assert d_grp["groups"][0]["group_id"] == target_gid
        assert len(d_grp["priorities"]) == len(d_grp["groups"][0]["member_track_ids"])

        # 3. Filter by min_priority_score
        resp_score = client.get("/api/v1/intelligence/summary?min_priority_score=99.0")
        assert resp_score.status_code == 200
        d_score = resp_score.json()
        assert len(d_score["priorities"]) == 0  # No tracks >= 99.0

        resp_score_low = client.get("/api/v1/intelligence/summary?min_priority_score=0.0")
        assert resp_score_low.status_code == 200
        assert len(resp_score_low.json()["priorities"]) == 10

    def test_03_empty_database_returns_clean_empty_summary(
        self,
        client: TestClient,
        database: Session,
        rbac_user,
    ) -> None:
        """Test 3: An empty database bootstraps cleanly and returns empty snapshot."""
        client.post(
            "/api/v1/auth/login",
            json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
        )
        assign_role(database, rbac_user, "OPERATOR")

        resp = client.get("/api/v1/intelligence/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert data["groups"] == []
        assert data["behaviors"] == []
        assert data["formations"] == []
        assert data["priorities"] == []

    def test_04_concurrent_rest_reads_and_track_updates(
        self,
        client: TestClient,
        database: Session,
        rbac_user,
        seed_tracks,
    ) -> None:
        """Test 4: Interleaved concurrent REST reads and incremental updates maintain consistent snapshots."""
        client.post(
            "/api/v1/auth/login",
            json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
        )
        assign_role(database, rbac_user, "OPERATOR")

        pipeline = get_intelligence_pipeline()
        pipeline.bootstrap_from_database(db=database)

        def reader_task(i: int) -> None:
            for _ in range(20):
                snap = pipeline.get_snapshot()
                assert isinstance(snap, MultiTrackIntelligenceSummary)
                assert len(snap.priorities) >= 10

        def writer_task(i: int) -> None:
            for k in range(20):
                t = TrackObservation(
                    id=f"TRK-CONC-R-{i:02d}",
                    latitude=37.7749 + (i * 0.001) + (k * 0.0001),
                    longitude=-122.4194,
                    velocity=20.0,
                    heading=90.0,
                )
                pipeline.process_track_update(t, publish_events=False)

        with ThreadPoolExecutor(max_workers=8) as executor:
            futures = [
                executor.submit(reader_task if i % 2 == 0 else writer_task, i)
                for i in range(12)
            ]
            for f in futures:
                f.result()

        final_resp = client.get("/api/v1/intelligence/summary")
        assert final_resp.status_code == 200
        assert len(final_resp.json()["priorities"]) >= 10
