"""Stage F1 operational model and contract tests."""

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError
from sqlalchemy import inspect, select
from sqlalchemy.exc import IntegrityError

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.geofence import Geofence
from app.models.scenario import Scenario
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory, TrackState
from app.schemas.detection import DetectionSchema
from app.schemas.geofence import GeofenceSchema
from app.schemas.sensor import SensorSchema
from app.schemas.threat import ThreatAssessmentSchema

NOW = datetime(2026, 1, 1, tzinfo=UTC)


def make_sensor(database) -> Sensor:
    sensor = Sensor(name="Test Sensor", source_type="synthetic", source_class=SensorSourceClass.SIMULATION)
    database.add(sensor)
    database.flush()
    return sensor


def make_track(database) -> Track:
    track = Track(first_seen_at=NOW.replace(tzinfo=None), last_seen_at=NOW.replace(tzinfo=None), latitude=10, longitude=20, confidence=0.8)
    database.add(track)
    database.flush()
    return track


def test_operational_tables_indexes_and_relationships(database, rbac_user):
    tables = inspect(database.bind).get_table_names()
    assert {"sensors", "detections", "tracks", "track_history", "alerts", "threat_assessments", "scenarios", "geofences"}.issubset(tables)
    assert {index["name"] for index in inspect(database.bind).get_indexes("detections")} >= {"ix_detections_timestamp", "ix_detections_sensor_timestamp", "ix_detections_track_id"}

    sensor = make_sensor(database)
    track = make_track(database)
    detection = Detection(sensor=sensor, source_detection_id="source-1", timestamp=NOW.replace(tzinfo=None), latitude=10, longitude=20, confidence=0.8, source_class=SensorSourceClass.SIMULATION, source_type="synthetic", track=track)
    history = TrackHistory(track=track, sequence=0, timestamp=NOW.replace(tzinfo=None), latitude=10, longitude=20, confidence=0.8, state=TrackState.NEW, provenance=SensorSourceClass.SIMULATION, source_detection_ids=["source-1"])
    alert = Alert(type=AlertType.TRACK_DETECTED, severity=AlertSeverity.LOW, status=AlertStatus.OPEN, track=track, sensor=sensor, reason="test")
    assessment = ThreatAssessment(track=track, score=10, level=ThreatLevel.LOW, factors={"confidence": 0.8})
    scenario = Scenario(name="Test", description="Test scenario", created_by_user_id=rbac_user.id)
    geofence = Geofence(name="Test zone", geometry={"type": "bbox", "min_lat": 1, "min_lon": 2, "max_lat": 3, "max_lon": 4})
    database.add_all([detection, history, alert, assessment, scenario, geofence])
    database.commit()
    assert detection.metadata == {}
    assert track.history == [history]
    assert detection.track is track
    assert assessment.track is track
    assert scenario.created_by.id == rbac_user.id


def test_detection_source_id_is_idempotent_per_sensor(database):
    sensor = make_sensor(database)
    values = dict(sensor_id=sensor.id, source_detection_id="duplicate", timestamp=NOW.replace(tzinfo=None), latitude=0, longitude=0, confidence=0.5, source_class=SensorSourceClass.REAL, source_type="radar")
    database.add_all([Detection(**values), Detection(**values)])
    with pytest.raises(IntegrityError):
        database.commit()
    database.rollback()


def test_detection_and_history_are_immutable(database):
    sensor = make_sensor(database)
    track = make_track(database)
    detection = Detection(sensor=sensor, timestamp=NOW.replace(tzinfo=None), latitude=0, longitude=0, confidence=0.5, source_class=SensorSourceClass.REAL, source_type="radar")
    history = TrackHistory(track=track, sequence=0, timestamp=NOW.replace(tzinfo=None), latitude=0, longitude=0, confidence=0.5, state=TrackState.NEW, provenance=SensorSourceClass.REAL)
    database.add_all([detection, history])
    database.commit()
    detection.latitude = 1
    with pytest.raises(ValueError):
        database.commit()
    database.rollback()
    history.state = TrackState.ACTIVE
    with pytest.raises(ValueError):
        database.commit()


@pytest.mark.parametrize("payload", [
    {"sensor_id": "s", "timestamp": NOW, "latitude": 91, "longitude": 0, "confidence": 0.5, "source_class": "REAL", "source_type": "x"},
    {"sensor_id": "s", "timestamp": NOW, "latitude": 0, "longitude": 0, "confidence": 2, "source_class": "REAL", "source_type": "x"},
    {"sensor_id": "s", "timestamp": NOW, "latitude": 0, "longitude": 0, "heading": 360, "confidence": 0.5, "source_class": "REAL", "source_type": "x"},
    {"sensor_id": "s", "timestamp": NOW, "latitude": 0, "longitude": 0, "horizontal_uncertainty": -1, "confidence": 0.5, "source_class": "REAL", "source_type": "x"},
])
def test_detection_schema_rejects_invalid_values(payload):
    with pytest.raises(ValidationError):
        DetectionSchema(**payload)


def test_strict_schema_bounds_and_geometry():
    with pytest.raises(ValidationError):
        SensorSchema(name="x", source_type="x", source_class="REAL", configuration_metadata={"x": "a" * 513})
    with pytest.raises(ValidationError):
        ThreatAssessmentSchema(track_id="t", score=101, level="HIGH")
    with pytest.raises(ValidationError):
        GeofenceSchema(name="x", geometry={"type": "bbox", "min_lat": 4, "min_lon": 2, "max_lat": 3, "max_lon": 5})
