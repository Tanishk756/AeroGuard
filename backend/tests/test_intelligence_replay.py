"""Tests for historical defensive intelligence reconstruction during Replay (Stage HI1)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy.orm import Session

from ai.schemas import (
    BehaviorClassification,
    BehavioralState,
    CoordinatedFormation,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    TrackGroup,
)
from app.history.intelligence import IntelligencePersistenceService
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.track import Track, TrackHistory, TrackState
from app.replay.engine import ReplayEngine
from app.replay.models import ReplayConfig
from app.schemas.replay import ReplayFilter, ReplayRequest


@pytest.fixture
def seed_scenario_and_intelligence(database: Session):
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)

    # 1. Create a sensor and 2 tracks
    sensor = Sensor(
        id="SNS-TEST",
        name="Radar Alpha",
        source_class=SensorSourceClass.SIMULATION,
        source_type="RADAR",
        status=SensorStatus.ACTIVE,
    )
    database.add(sensor)

    t1 = Track(
        id="TRK-ALPHA",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now + timedelta(seconds=10),
        latitude=37.7750,
        longitude=-122.4190,
        altitude=150.0,
        velocity=20.0,
        heading=90.0,
        confidence=0.95,
        classification="UAS",
    )
    t2 = Track(
        id="TRK-BRAVO",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now + timedelta(seconds=10),
        latitude=37.7753,
        longitude=-122.4187,
        altitude=150.0,
        velocity=20.0,
        heading=90.0,
        confidence=0.95,
        classification="UAS",
    )
    database.add_all([t1, t2])

    # Add track histories across T=0 to T=10
    for s in range(11):
        ts = now + timedelta(seconds=s)
        h1 = TrackHistory(
            track_id="TRK-ALPHA",
            sequence=s + 1,
            timestamp=ts,
            latitude=37.7750 + (s * 0.0001),
            longitude=-122.4190 + (s * 0.0001),
            altitude=150.0,
            velocity=20.0,
            heading=90.0,
            confidence=0.95,
            state=TrackState.ACTIVE,
            provenance=SensorSourceClass.SIMULATION,
        )
        h2 = TrackHistory(
            track_id="TRK-BRAVO",
            sequence=s + 1,
            timestamp=ts,
            latitude=37.7753 + (s * 0.0001),
            longitude=-122.4187 + (s * 0.0001),
            altitude=150.0,
            velocity=20.0,
            heading=90.0,
            confidence=0.95,
            state=TrackState.ACTIVE,
            provenance=SensorSourceClass.SIMULATION,
        )
        database.add_all([h1, h2])

    database.commit()

    # 2. Persist historical intelligence snapshots
    persistence = IntelligencePersistenceService()

    # Snapshot at T=0
    summary_t0 = MultiTrackIntelligenceSummary(
        groups=[
            TrackGroup(
                group_id="GRP-SWARM-1",
                member_track_ids=["TRK-ALPHA", "TRK-BRAVO"],
                member_count=2,
                centroid_lat=37.7751,
                centroid_lon=-122.4188,
                radius_meters=45.0,
                behavioral_state="COORDINATED",
                updated_at=now,
            )
        ],
        behaviors=[
            BehaviorClassification(
                track_id="TRK-ALPHA",
                state=BehavioralState.COORDINATED,
                confidence=0.95,
                duration_seconds=5.0,
                reason="Synchronized parallel flight",
                evaluated_at=now,
            ),
            BehaviorClassification(
                track_id="TRK-BRAVO",
                state=BehavioralState.COORDINATED,
                confidence=0.95,
                duration_seconds=5.0,
                reason="Synchronized parallel flight",
                evaluated_at=now,
            ),
        ],
        formations=[
            CoordinatedFormation(
                formation_id="FMT-001",
                group_id="GRP-SWARM-1",
                member_track_ids=["TRK-ALPHA", "TRK-BRAVO"],
                synchronization_index=0.94,
                heading_dispersion_deg=2.1,
                velocity_dispersion_mps=0.3,
                confidence=0.95,
                evaluated_at=now,
            )
        ],
        priorities=[
            ThreatPriorityAssessment(
                track_id="TRK-ALPHA",
                priority_score=72.0,
                priority_level="HIGH",
                confidence=0.92,
                reason="Coordinated swarm approaching perimeter",
                evaluated_at=now,
            ),
            ThreatPriorityAssessment(
                track_id="TRK-BRAVO",
                priority_score=72.0,
                priority_level="HIGH",
                confidence=0.92,
                reason="Coordinated swarm approaching perimeter",
                evaluated_at=now,
            ),
        ],
        evaluated_at=now,
    )

    # Snapshot at T=5: Formation escalates
    summary_t5 = MultiTrackIntelligenceSummary(
        groups=[
            TrackGroup(
                group_id="GRP-SWARM-1",
                member_track_ids=["TRK-ALPHA", "TRK-BRAVO"],
                member_count=2,
                centroid_lat=37.7756,
                centroid_lon=-122.4183,
                radius_meters=42.0,
                behavioral_state="APPROACHING",
                updated_at=now + timedelta(seconds=5),
            )
        ],
        behaviors=[
            BehaviorClassification(
                track_id="TRK-ALPHA",
                state=BehavioralState.APPROACHING,
                confidence=0.98,
                duration_seconds=10.0,
                reason="Direct approach vector toward defense asset",
                evaluated_at=now + timedelta(seconds=5),
            )
        ],
        formations=summary_t0.formations,
        priorities=[
            ThreatPriorityAssessment(
                track_id="TRK-ALPHA",
                priority_score=88.5,
                priority_level="CRITICAL",
                confidence=0.95,
                reason="Critical breach risk from swarm lead",
                evaluated_at=now + timedelta(seconds=5),
            )
        ],
        evaluated_at=now + timedelta(seconds=5),
    )

    persistence.record_summary_snapshot(summary_t0, force=True, now=now)
    persistence.record_group_history(summary_t0.groups[0], coordination_index=0.94, now=now)
    persistence.record_summary_snapshot(summary_t5, force=True, now=now + timedelta(seconds=5))
    persistence.record_group_history(summary_t5.groups[0], coordination_index=0.96, now=now + timedelta(seconds=5))

    persistence.flush(db=database)
    return now


def test_replay_engine_reconstructs_historical_intelligence(database: Session, seed_scenario_and_intelligence):
    base_time = seed_scenario_and_intelligence

    req = ReplayRequest(
        start_time=base_time,
        end_time=base_time + timedelta(seconds=10),
        step_interval_seconds=1.0,
        filters=ReplayFilter(include_intelligence=True),
    )
    config = ReplayConfig.from_request(req)
    engine = ReplayEngine(database, config)

    # 1. Step at T=0
    snap_0 = engine.get_snapshot_at(base_time, step_idx=0)
    assert len(snap_0.active_tracks) == 2
    assert snap_0.intelligence is not None
    assert len(snap_0.intelligence.groups) == 1
    assert snap_0.intelligence.groups[0].group_id == "GRP-SWARM-1"
    assert len(snap_0.intelligence.formations) == 1
    assert snap_0.intelligence.formations[0].synchronization_index == 0.94
    assert len(snap_0.group_hulls) == 1
    assert snap_0.metrics["groups_count"] == 1
    assert snap_0.metrics["formations_count"] == 1

    # 2. Step at T=5 (escalation to CRITICAL)
    snap_5 = engine.get_snapshot_at(base_time + timedelta(seconds=5), step_idx=5)
    assert snap_5.intelligence is not None
    assert snap_5.intelligence.priorities[0].priority_level == "CRITICAL"
    assert snap_5.intelligence.priorities[0].priority_score == 88.5
    assert snap_5.intelligence.behaviors[0].state == BehavioralState.APPROACHING


def test_replay_engine_filters_intelligence_by_track_id(database: Session, seed_scenario_and_intelligence):
    base_time = seed_scenario_and_intelligence

    # Filter strictly for TRK-ALPHA
    req = ReplayRequest(
        start_time=base_time,
        end_time=base_time + timedelta(seconds=5),
        step_interval_seconds=1.0,
        filters=ReplayFilter(track_ids=["TRK-ALPHA"], include_intelligence=True),
    )
    config = ReplayConfig.from_request(req)
    engine = ReplayEngine(database, config)

    snap = engine.get_snapshot_at(base_time, step_idx=0)
    assert len(snap.active_tracks) == 1
    assert snap.active_tracks[0].track_id == "TRK-ALPHA"
    assert snap.intelligence is not None
    assert len(snap.intelligence.behaviors) == 1
    assert snap.intelligence.behaviors[0].track_id == "TRK-ALPHA"


def test_replay_engine_graceful_when_no_intelligence_exists(database: Session):
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
    req = ReplayRequest(
        start_time=now,
        end_time=now + timedelta(seconds=5),
        step_interval_seconds=1.0,
        filters=ReplayFilter(include_intelligence=True),
    )
    config = ReplayConfig.from_request(req)
    engine = ReplayEngine(database, config)

    snap = engine.get_snapshot_at(now, step_idx=0)
    assert snap.intelligence is None
    assert snap.group_hulls == []
    assert snap.metrics["groups_count"] == 0
    assert snap.metrics["formations_count"] == 0
