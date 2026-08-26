"""Concurrency, idempotency, and immutability tests for track management."""

from datetime import datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.association import TrackAssociation, TrackAssociationDecision
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.track import Track, TrackHistory, TrackState
from app.tracking.service import TrackingService


def create_sensor(database):
    sensor = Sensor(
        id="sensor-conc-1",
        name="Concurrency Sensor",
        source_type="radar",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
    )
    database.add(sensor)
    database.commit()
    return sensor


def create_detection(database, detection_id: str, sensor_id: str = "sensor-conc-1"):
    det = Detection(
        id=detection_id,
        sensor_id=sensor_id,
        source_detection_id=f"src-{detection_id}",
        timestamp=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        altitude=100.0,
        velocity=15.0,
        heading=90.0,
        confidence=0.8,
        classification="UAV",
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    database.add(det)
    database.commit()
    return det


def test_concurrent_duplicate_detection_processing(database):
    sensor = create_sensor(database)
    det = create_detection(database, "det-race-1", sensor_id=sensor.id)

    service1 = TrackingService(database)
    service2 = TrackingService(database)

    # First service processes the detection
    res1 = service1.process_detection(det)
    assert res1.decision.decision == TrackAssociationDecision.NEW_TRACK

    # Second service processes the exact same detection
    res2 = service2.process_detection(det)
    assert res2.decision.decision == TrackAssociationDecision.DUPLICATE
    assert res2.track.id == res1.track.id

    # Verify exactly 1 track and 1 association exists
    tracks = database.scalars(select(Track)).all()
    assert len(tracks) == 1
    assocs = database.scalars(select(TrackAssociation)).all()
    assert len(assocs) == 1


def test_concurrent_track_creation(database):
    sensor = create_sensor(database)
    det1 = create_detection(database, "det-t1", sensor_id=sensor.id)
    # Create det2 far away so it creates its own track
    det2 = Detection(
        id="det-t2",
        sensor_id=sensor.id,
        source_detection_id="src-det-t2",
        timestamp=datetime(2026, 8, 26, 12, 0, 0),
        latitude=40.7128,
        longitude=-74.0060,
        confidence=0.8,
        classification="UAV",
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    database.add(det2)
    database.commit()

    service = TrackingService(database)
    res1 = service.process_detection(det1)
    res2 = service.process_detection(det2)

    assert res1.track.id != res2.track.id
    assert res1.decision.decision == TrackAssociationDecision.NEW_TRACK
    assert res2.decision.decision == TrackAssociationDecision.NEW_TRACK


def test_association_and_history_immutability(database):
    sensor = create_sensor(database)
    det = create_detection(database, "det-immut-1", sensor_id=sensor.id)

    service = TrackingService(database)
    res = service.process_detection(det)

    assoc = database.scalar(
        select(TrackAssociation).where(TrackAssociation.track_id == res.track.id)
    )
    hist = database.scalar(
        select(TrackHistory).where(TrackHistory.track_id == res.track.id)
    )

    # Attempting to mutate TrackAssociation must fail
    assoc.reason = "modified reason"
    with pytest.raises(ValueError, match="Track associations are immutable"):
        database.commit()
    database.rollback()

    # Attempting to delete TrackAssociation must fail
    database.delete(assoc)
    with pytest.raises(ValueError, match="Track associations are immutable"):
        database.commit()
    database.rollback()

    # Attempting to mutate TrackHistory must fail
    hist.state = TrackState.ACTIVE
    with pytest.raises(ValueError, match="Track history is immutable"):
        database.commit()
    database.rollback()

    # Attempting to delete TrackHistory must fail
    database.delete(hist)
    with pytest.raises(ValueError, match="Track history is immutable"):
        database.commit()
    database.rollback()

    # Attempting to mutate Detection must fail
    det.confidence = 0.99
    with pytest.raises(ValueError, match="Detections are immutable"):
        database.commit()
    database.rollback()


def test_unique_detection_association_constraint(database):
    sensor = create_sensor(database)
    det = create_detection(database, "det-uniq-1", sensor_id=sensor.id)

    service = TrackingService(database)
    res = service.process_detection(det)

    # Attempting to insert another TrackAssociation for the same detection_id must fail
    duplicate_assoc = TrackAssociation(
        detection_id=det.id,
        track_id=res.track.id,
        sensor_id=sensor.id,
        timestamp=det.timestamp,
        decision=TrackAssociationDecision.ASSOCIATED,
        reason="Duplicate entry",
    )
    database.add(duplicate_assoc)
    with pytest.raises(IntegrityError):
        database.flush()
    database.rollback()
