"""Integration tests for track management, association, and lifecycle."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.models.association import TrackAssociation, TrackAssociationDecision
from app.models.audit import AuditEvent
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.track import Track, TrackHistory, TrackState
from app.tracking.association import generate_track_id
from app.tracking.lifecycle import LifecycleConfig, TrackLifecycleService
from app.tracking.service import TrackingService


def create_sensor(db, sensor_id: str = "sensor-1", name: str = "Radar 1") -> Sensor:
    s = Sensor(
        id=sensor_id,
        name=name,
        source_type="radar",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
    )
    db.add(s)
    db.commit()
    return s


def create_detection(
    db,
    detection_id: str,
    sensor_id: str = "sensor-1",
    timestamp: datetime | None = None,
    lat: float = 37.7749,
    lon: float = -122.4194,
    altitude: float | None = 100.0,
    velocity: float | None = 15.0,
    heading: float | None = 90.0,
    confidence: float = 0.8,
    classification: str | None = "UAV",
) -> Detection:
    ts = timestamp or datetime(2026, 8, 26, 12, 0, 0)
    det = Detection(
        id=detection_id,
        sensor_id=sensor_id,
        source_detection_id=f"src-{detection_id}",
        timestamp=ts,
        latitude=lat,
        longitude=lon,
        altitude=altitude,
        velocity=velocity,
        heading=heading,
        confidence=confidence,
        classification=classification,
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    db.add(det)
    db.commit()
    return det


def test_track_creation_from_unmatched_detection(database):
    sensor = create_sensor(database)
    det = create_detection(database, "det-001", sensor_id=sensor.id)

    service = TrackingService(database)
    result = service.process_detection(det)

    assert result.decision.decision == TrackAssociationDecision.NEW_TRACK
    assert result.track.state == TrackState.NEW
    assert result.track.id == generate_track_id(det.id)
    assert result.track.source_count == 1
    assert result.track.confidence == 0.8
    assert result.track.classification == "UAV"

    # Verify history entry
    histories = database.scalars(
        select(TrackHistory).where(TrackHistory.track_id == result.track.id)
    ).all()
    assert len(histories) == 1
    assert histories[0].sequence == 1
    assert histories[0].state == TrackState.NEW
    assert histories[0].source_detection_ids == [det.id]

    # Verify association entry
    assocs = database.scalars(
        select(TrackAssociation).where(TrackAssociation.track_id == result.track.id)
    ).all()
    assert len(assocs) == 1
    assert assocs[0].detection_id == det.id
    assert assocs[0].decision == TrackAssociationDecision.NEW_TRACK
    assert assocs[0].score == 1.0


def test_track_confirmation_lifecycle(database):
    sensor = create_sensor(database)
    service = TrackingService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # 1. First detection creates NEW track
    d1 = create_detection(database, "det-1", sensor_id=sensor.id, timestamp=t0)
    r1 = service.process_detection(d1)
    track_id = r1.track.id
    assert r1.track.state == TrackState.NEW

    # 2. Second detection (5s later) -> ASSOCIATED, remains NEW
    d2 = create_detection(
        database,
        "det-2",
        sensor_id=sensor.id,
        timestamp=t0 + timedelta(seconds=5),
        lat=37.7749 + 0.0005,
        lon=-122.4194,
    )
    r2 = service.process_detection(d2)
    assert r2.decision.decision == TrackAssociationDecision.ASSOCIATED
    assert r2.track.id == track_id
    assert r2.track.state == TrackState.NEW

    # 3. Third detection (10s later, within 30s window) -> confirms to ACTIVE!
    d3 = create_detection(
        database,
        "det-3",
        sensor_id=sensor.id,
        timestamp=t0 + timedelta(seconds=10),
        lat=37.7749 + 0.0010,
        lon=-122.4194,
    )
    r3 = service.process_detection(d3)
    assert r3.decision.decision == TrackAssociationDecision.ASSOCIATED
    assert r3.track.id == track_id
    assert r3.track.state == TrackState.ACTIVE

    # Verify history sequences 1, 2, 3
    histories = database.scalars(
        select(TrackHistory)
        .where(TrackHistory.track_id == track_id)
        .order_by(TrackHistory.sequence.asc())
    ).all()
    assert len(histories) == 3
    assert [h.sequence for h in histories] == [1, 2, 3]
    assert histories[2].state == TrackState.ACTIVE


def test_track_confirmation_window_expiration(database):
    sensor = create_sensor(database)
    service = TrackingService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # 1. First detection at t=0
    d1 = create_detection(database, "det-w1", sensor_id=sensor.id, timestamp=t0)
    r1 = service.process_detection(d1)
    track_id = r1.track.id

    # 2. Second detection at t=5s
    d2 = create_detection(database, "det-w2", sensor_id=sensor.id, timestamp=t0 + timedelta(seconds=5))
    service.process_detection(d2)

    # 3. Third detection at t=45s (>30s from first_seen_at)
    d3 = create_detection(database, "det-w3", sensor_id=sensor.id, timestamp=t0 + timedelta(seconds=45))
    r3 = service.process_detection(d3)

    # 45s is > 30s confirmation window, track remains NEW
    assert r3.track.state == TrackState.NEW


def test_track_lifecycle_advancement_and_history(database):
    sensor = create_sensor(database)
    tracking_service = TrackingService(database)
    lifecycle_service = TrackLifecycleService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Create and confirm a track to ACTIVE
    d1 = create_detection(database, "det-l1", sensor_id=sensor.id, timestamp=t0)
    tracking_service.process_detection(d1)
    d2 = create_detection(database, "det-l2", sensor_id=sensor.id, timestamp=t0 + timedelta(seconds=2))
    tracking_service.process_detection(d2)
    d3 = create_detection(database, "det-l3", sensor_id=sensor.id, timestamp=t0 + timedelta(seconds=4))
    r3 = tracking_service.process_detection(d3)
    track = r3.track
    assert track.state == TrackState.ACTIVE

    # Advance time: t0 + 15s (> 10s coast_timeout) -> STALE
    transitions = lifecycle_service.advance(now=t0 + timedelta(seconds=15))
    assert len(transitions) == 1
    assert transitions[0].to_state == TrackState.STALE
    database.refresh(track)
    assert track.state == TrackState.STALE

    # Advance time without exceeding lost timeout -> no transitions
    transitions_no_op = lifecycle_service.advance(now=t0 + timedelta(seconds=20))
    assert len(transitions_no_op) == 0

    # Advance time: t0 + 70s (> 60s lost_timeout from last_seen_at t0+4s) -> LOST
    transitions_lost = lifecycle_service.advance(now=t0 + timedelta(seconds=70))
    assert len(transitions_lost) == 1
    assert transitions_lost[0].to_state == TrackState.LOST
    database.refresh(track)
    assert track.state == TrackState.LOST

    # Advance time: t0 + 90000s (> 24h archive delay) -> ARCHIVED
    transitions_arch = lifecycle_service.advance(now=t0 + timedelta(seconds=90000))
    assert len(transitions_arch) == 1
    assert transitions_arch[0].to_state == TrackState.ARCHIVED
    database.refresh(track)
    assert track.state == TrackState.ARCHIVED

    # Verify history rows: 3 detection entries + 3 transition entries = 6 total
    histories = database.scalars(
        select(TrackHistory)
        .where(TrackHistory.track_id == track.id)
        .order_by(TrackHistory.sequence.asc())
    ).all()
    assert len(histories) == 6
    assert [h.sequence for h in histories] == [1, 2, 3, 4, 5, 6]
    assert [h.state for h in histories] == [
        TrackState.NEW,
        TrackState.NEW,
        TrackState.ACTIVE,
        TrackState.STALE,
        TrackState.LOST,
        TrackState.ARCHIVED,
    ]


def test_stale_track_reentry(database):
    sensor = create_sensor(database)
    tracking_service = TrackingService(database)
    lifecycle_service = TrackLifecycleService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Establish ACTIVE track with last detection at t0 + 2s
    for i in range(3):
        d = create_detection(
            database,
            f"det-re-{i}",
            sensor_id=sensor.id,
            timestamp=t0 + timedelta(seconds=i),
        )
        tracking_service.process_detection(d)

    # Advance into STALE at t0 + 12.5s (> 10s after t0 + 2s)
    transitions = lifecycle_service.advance(now=t0 + timedelta(seconds=12, milliseconds=500))
    assert len(transitions) == 1
    assert transitions[0].to_state == TrackState.STALE

    # Associated detection while STALE at t0 + 11.5s (9.5s after t0+2s, within 10s max_time_delta)
    d_reentry = create_detection(
        database,
        "det-reentry",
        sensor_id=sensor.id,
        timestamp=t0 + timedelta(seconds=11, milliseconds=500),
        lat=37.7749 + 0.0005,
        lon=-122.4194,
    )
    result = tracking_service.process_detection(d_reentry)
    assert result.decision.decision == TrackAssociationDecision.ASSOCIATED
    assert result.track.state == TrackState.ACTIVE


def test_closed_tracks_never_reopen(database):
    sensor = create_sensor(database)
    tracking_service = TrackingService(database)
    lifecycle_service = TrackLifecycleService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Create and confirm track to ACTIVE
    for i in range(3):
        d = create_detection(
            database,
            f"det-arch-init-{i}",
            sensor_id=sensor.id,
            timestamp=t0 + timedelta(seconds=i),
        )
        r = tracking_service.process_detection(d)

    archived_track_id = r.track.id
    assert r.track.state == TrackState.ACTIVE

    # Transition ACTIVE -> STALE -> LOST -> ARCHIVED over time
    lifecycle_service.advance(now=t0 + timedelta(seconds=15))
    lifecycle_service.advance(now=t0 + timedelta(seconds=80))
    lifecycle_service.advance(now=t0 + timedelta(seconds=100000))

    database.refresh(r.track)
    assert r.track.state == TrackState.ARCHIVED

    # New detection at same location long after
    d_new = create_detection(
        database,
        "det-arch-new",
        sensor_id=sensor.id,
        timestamp=t0 + timedelta(seconds=100005),
        lat=37.7749,
        lon=-122.4194,
    )
    r_new = tracking_service.process_detection(d_new)

    # Must NOT reopen archived track -> creates a distinct NEW track
    assert r_new.track.id != archived_track_id
    assert r_new.decision.decision == TrackAssociationDecision.NEW_TRACK
    assert r_new.track.state == TrackState.NEW

    database.refresh(r.track)
    assert r.track.state == TrackState.ARCHIVED


def test_distinct_sensors_increment_source_count(database):
    s1 = create_sensor(database, "sensor-alpha", "Radar Alpha")
    s2 = create_sensor(database, "sensor-beta", "Radar Beta")
    service = TrackingService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Sensor 1 creates track -> source_count = 1
    d1 = create_detection(database, "det-s1", sensor_id=s1.id, timestamp=t0)
    r1 = service.process_detection(d1)
    assert r1.track.source_count == 1

    # Sensor 1 associates -> source_count remains 1
    d2 = create_detection(database, "det-s2", sensor_id=s1.id, timestamp=t0 + timedelta(seconds=2))
    r2 = service.process_detection(d2)
    assert r2.track.source_count == 1

    # Sensor 2 associates -> source_count becomes 2
    d3 = create_detection(database, "det-s3", sensor_id=s2.id, timestamp=t0 + timedelta(seconds=4))
    r3 = service.process_detection(d3)
    assert r3.track.source_count == 2


def test_deterministic_tie_breaking_multiple_candidates(database):
    sensor = create_sensor(database)
    service = TrackingService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Create candidate track A (lat 37.7750, 100m away)
    dA = create_detection(database, "det-cand-A", sensor_id=sensor.id, timestamp=t0, lat=37.7750, lon=-122.4194)
    rA = service.process_detection(dA)

    # Create candidate track B (lat 37.7800, 500m away)
    dB = create_detection(database, "det-cand-B", sensor_id=sensor.id, timestamp=t0, lat=37.7800, lon=-122.4194)
    rB = service.process_detection(dB)

    # New detection close to Track A (lat 37.7751, ~11m from A, ~500m from B)
    d_match = create_detection(
        database,
        "det-cand-match",
        sensor_id=sensor.id,
        timestamp=t0 + timedelta(seconds=1),
        lat=37.7751,
        lon=-122.4194,
    )
    r_match = service.process_detection(d_match)

    # Must deterministically select Track A
    assert r_match.decision.decision == TrackAssociationDecision.ASSOCIATED
    assert r_match.track.id == rA.track.id


def test_idempotent_duplicate_processing(database):
    sensor = create_sensor(database)
    service = TrackingService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    det = create_detection(database, "det-dup-1", sensor_id=sensor.id, timestamp=t0)
    res1 = service.process_detection(det)
    assert res1.decision.decision == TrackAssociationDecision.NEW_TRACK

    # Duplicate processing of exact same detection
    res2 = service.process_detection(det)
    assert res2.decision.decision == TrackAssociationDecision.DUPLICATE
    assert res2.track.id == res1.track.id

    # Verify no duplicate history or association entries
    histories = database.scalars(
        select(TrackHistory).where(TrackHistory.track_id == res1.track.id)
    ).all()
    assert len(histories) == 1

    assocs = database.scalars(
        select(TrackAssociation).where(TrackAssociation.track_id == res1.track.id)
    ).all()
    assert len(assocs) == 1


def test_no_audit_event_created_for_tracking(database):
    sensor = create_sensor(database)
    service = TrackingService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    initial_audit_count = database.scalar(select(func.count(AuditEvent.id))) or 0

    det1 = create_detection(database, "det-audit-1", sensor_id=sensor.id, timestamp=t0)
    service.process_detection(det1)

    det2 = create_detection(database, "det-audit-2", sensor_id=sensor.id, timestamp=t0 + timedelta(seconds=2))
    service.process_detection(det2)

    after_audit_count = database.scalar(select(func.count(AuditEvent.id))) or 0
    assert after_audit_count == initial_audit_count
