"""Tests for IntelligencePersistenceService and historical intelligence persistence primitives."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.schemas import (
    BehaviorClassification,
    BehavioralState,
    CoordinatedFormation,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    TrackGroup,
)
from app.history.intelligence import (
    IntelligencePersistenceService,
    get_intelligence_persistence,
    reset_intelligence_persistence,
)
from app.models.intelligence_history import (
    BehaviorEventHistory,
    IntelligenceSnapshot,
    TrackGroupHistory,
)


@pytest.fixture(autouse=True)
def clean_persistence():
    reset_intelligence_persistence()
    yield
    reset_intelligence_persistence()


def test_persistence_service_record_snapshot_and_flush(database: Session):
    service = IntelligencePersistenceService(snapshot_min_interval_seconds=0.5)
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)

    summary = MultiTrackIntelligenceSummary(
        groups=[
            TrackGroup(
                group_id="GRP-001",
                member_track_ids=["TRK-001", "TRK-002"],
                member_count=2,
                centroid_lat=37.7749,
                centroid_lon=-122.4194,
                radius_meters=150.0,
                behavioral_state="COORDINATED",
                created_at=now,
            )
        ],
        behaviors=[
            BehaviorClassification(
                track_id="TRK-001",
                state=BehavioralState.COORDINATED,
                confidence=0.95,
                duration_seconds=12.0,
                reason="Synchronized flight with member tracks",
                contributing_factors=["Synchronized flight"],
            )
        ],
        formations=[
            CoordinatedFormation(
                formation_id="FMT-001",
                group_id="GRP-001",
                member_track_ids=["TRK-001", "TRK-002"],
                synchronization_index=0.88,
                heading_dispersion_deg=5.2,
                velocity_dispersion_mps=0.8,
                confidence=0.95,
            )
        ],
        priorities=[
            ThreatPriorityAssessment(
                track_id="TRK-001",
                priority_score=65.5,
                priority_level="HIGH",
                confidence=0.90,
                reason="High velocity approaching defense perimeter with coordinated swarm",
                evaluated_at=now,
            )
        ],
        evaluated_at=now,
    )

    # 1. Enqueue snapshot
    assert service.record_summary_snapshot(summary, now=now) is True
    assert service.queue.qsize() == 1

    # 2. Throttled attempt within 0.5s should return False
    now_soon = now + timedelta(seconds=0.2)
    assert service.record_summary_snapshot(summary, force=False, now=now_soon) is False
    assert service.queue.qsize() == 1

    # 3. Flush to database
    committed = service.flush(db=database)
    assert committed == 1
    assert service.queue.empty()
    assert service.persisted_count == 1

    # 4. Verify in database
    row = database.scalar(select(IntelligenceSnapshot).limit(1))
    assert row is not None
    assert row.group_count == 1
    assert row.formation_count == 1
    assert row.active_track_count == 1
    assert row.peak_threat_score == 65.5
    assert row.summary_json["groups"][0]["group_id"] == "GRP-001"


def test_persistence_service_group_history_deduplication(database: Session):
    service = IntelligencePersistenceService()
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)

    grp = TrackGroup(
        group_id="GRP-ALPHA",
        member_track_ids=["TRK-1", "TRK-2"],
        member_count=2,
        centroid_lat=37.77,
        centroid_lon=-122.41,
        radius_meters=100.0,
        behavioral_state="NORMAL",
        created_at=now,
    )

    # Initial enqueue succeeds
    assert service.record_group_history(grp, coordination_index=0.75, now=now) is True
    # Duplicate enqueue with identical state is dropped
    assert service.record_group_history(grp, coordination_index=0.75, now=now) is False

    # Modified group state succeeds
    grp_modified = TrackGroup(
        group_id="GRP-ALPHA",
        member_track_ids=["TRK-1", "TRK-2", "TRK-3"],
        member_count=3,
        centroid_lat=37.775,
        centroid_lon=-122.415,
        radius_meters=180.0,
        behavioral_state="COORDINATED",
        created_at=now + timedelta(seconds=5),
    )
    assert service.record_group_history(grp_modified, coordination_index=0.92, now=now + timedelta(seconds=5)) is True

    committed = service.flush(db=database)
    assert committed == 2

    groups_in_db = list(database.scalars(select(TrackGroupHistory).order_by(TrackGroupHistory.timestamp.asc())).all())
    assert len(groups_in_db) == 2
    assert groups_in_db[0].member_count == 2
    assert groups_in_db[1].member_count == 3
    assert groups_in_db[1].coordination_index == 0.92


def test_persistence_service_behavior_event_logging(database: Session):
    service = IntelligencePersistenceService()
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)

    service.record_behavior_event(
        track_id="TRK-999",
        previous_state="NORMAL",
        new_state="LOITERING",
        duration_seconds=15.0,
        confidence=0.89,
        reasons=["Radius of gyration < 150m", "Heading variance > 80 deg"],
        now=now,
    )

    committed = service.flush(db=database)
    assert committed == 1

    event_row = database.scalar(select(BehaviorEventHistory).where(BehaviorEventHistory.track_id == "TRK-999"))
    assert event_row is not None
    assert event_row.previous_state == "NORMAL"
    assert event_row.new_state == "LOITERING"
    assert event_row.duration_seconds == 15.0
    assert len(event_row.reasons) == 2


def test_persistence_service_db_failure_isolation():
    """Simulate a broken database session; ensure service catches exception without raising to caller."""
    service = IntelligencePersistenceService()
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)

    service.record_behavior_event(
        track_id="TRK-FAIL",
        previous_state=None,
        new_state="APPROACHING",
        now=now,
    )

    class MockFailingSession:
        def add(self, item):
            pass
        def commit(self):
            from sqlalchemy.exc import OperationalError
            raise OperationalError("Database disk is full", params=None, orig=Exception("Disk full"))
        def rollback(self):
            pass

    # Flush should return 0 and increment dropped_count without raising
    result = service.flush(db=MockFailingSession())
    assert result == 0
    assert service.dropped_count == 1
