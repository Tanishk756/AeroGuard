"""Tests for deterministic descriptive operational analytics."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackState


def test_analytics_metrics_and_determinism(database: Session):
    sensor1 = Sensor(
        id="radar-an-01",
        name="Analytics Radar",
        source_type="RADAR",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_metadata={"latitude": 37.7749, "longitude": -122.4194},
    )
    sensor2 = Sensor(
        id="optical-an-01",
        name="Analytics Optical",
        source_type="OPTICAL",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_metadata={"latitude": 37.7749, "longitude": -122.4194},
    )
    database.add_all([sensor1, sensor2])

    base_time = datetime(2026, 8, 26, 14, 0, 0)
    track1 = Track(
        id="TRK-AN-001",
        state=TrackState.ACTIVE,
        first_seen_at=base_time,
        last_seen_at=base_time + timedelta(seconds=20),
        latitude=37.775,
        longitude=-122.419,
        source_count=2,
        confidence=0.90,
        classification="DRONE",
    )
    track2 = Track(
        id="TRK-AN-002",
        state=TrackState.ARCHIVED,
        first_seen_at=base_time,
        last_seen_at=base_time + timedelta(seconds=10),
        latitude=37.775,
        longitude=-122.419,
        source_count=1,
        confidence=0.60,
        classification="UNKNOWN",
    )
    database.add_all([track1, track2])
    database.flush()

    # Detections
    det1 = Detection(
        id="det-an-1",
        sensor_id=sensor1.id,
        source_detection_id="src-an-1",
        timestamp=base_time,
        latitude=37.775,
        longitude=-122.419,
        confidence=0.90,
        source_class=SensorSourceClass.SIMULATION,
        source_type="RADAR",
        track_id=track1.id,
    )
    det2 = Detection(
        id="det-an-2",
        sensor_id=sensor2.id,
        source_detection_id="src-an-2",
        timestamp=base_time + timedelta(seconds=5),
        latitude=37.7751,
        longitude=-122.4191,
        confidence=0.80,
        source_class=SensorSourceClass.SIMULATION,
        source_type="OPTICAL",
        track_id=track1.id,
    )
    database.add_all([det1, det2])

    # Alert
    alert = Alert(
        id="alert-an-1",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        track_id=track1.id,
        reason="Zone Breach",
        metadata_json={},
        created_at=base_time + timedelta(seconds=5),
        updated_at=base_time + timedelta(seconds=5),
    )
    database.add(alert)

    # Threat
    threat = ThreatAssessment(
        id="threat-an-1",
        track_id=track1.id,
        score=75.0,
        level=ThreatLevel.HIGH,
        factors={"speed": 0.8},
        created_at=base_time + timedelta(seconds=5),
        updated_at=base_time + timedelta(seconds=5),
    )
    database.add(threat)
    database.commit()

    service = AnalyticsService(database)
    summary1 = service.get_summary(base_time, base_time + timedelta(seconds=60))
    summary2 = service.get_summary(base_time, base_time + timedelta(seconds=60))

    # Determinism assertion
    assert summary1.model_dump() == summary2.model_dump()

    # Content assertions
    assert summary1.detections.total_detections == 2
    assert summary1.detections.by_sensor[sensor1.id] == 1
    assert summary1.detections.by_sensor[sensor2.id] == 1
    assert summary1.detections.by_modality["RADAR"] == 1
    assert summary1.detections.by_modality["OPTICAL"] == 1
    assert summary1.tracks.total_tracks == 2
    assert summary1.tracks.by_state["ACTIVE"] == 1
    assert summary1.tracks.by_state["ARCHIVED"] == 1
    assert summary1.alerts.total_alerts == 1
    assert summary1.geofence_breach_count == 1
    assert summary1.threats.total_assessed == 1
    assert summary1.threats.avg_score == 75.0
