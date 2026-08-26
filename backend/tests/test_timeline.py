"""Tests for unified operational timeline normalization and ordering."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.history.service import HistoryService
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory, TrackState
from app.schemas.history import TimelineEventType


def test_timeline_normalization_and_deterministic_sorting(database: Session):
    sensor = Sensor(
        id="radar-time-01",
        name="Timeline Radar",
        source_type="RADAR",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_metadata={"latitude": 37.7749, "longitude": -122.4194},
    )
    database.add(sensor)

    base_time = datetime(2026, 8, 26, 12, 0, 0)
    track = Track(
        id="TRK-TIME-001",
        state=TrackState.ACTIVE,
        first_seen_at=base_time,
        last_seen_at=base_time + timedelta(seconds=10),
        latitude=37.775,
        longitude=-122.419,
        source_count=1,
        confidence=0.95,
    )
    database.add(track)
    database.flush()

    # Create entities at the exact same timestamp (base_time + 10s)
    t_shared = base_time + timedelta(seconds=10)

    det = Detection(
        id="det-time-shared",
        sensor_id=sensor.id,
        source_detection_id="src-time-shared",
        timestamp=t_shared,
        latitude=37.775,
        longitude=-122.419,
        confidence=0.95,
        source_class=SensorSourceClass.SIMULATION,
        source_type="RADAR",
        track_id=track.id,
    )
    database.add(det)

    th = TrackHistory(
        id="th-time-shared",
        track_id=track.id,
        sequence=1,
        timestamp=t_shared,
        latitude=37.775,
        longitude=-122.419,
        confidence=0.95,
        state=TrackState.ACTIVE,
        provenance=SensorSourceClass.SIMULATION,
        source_detection_ids=[det.id],
    )
    database.add(th)

    threat = ThreatAssessment(
        id="threat-time-shared",
        track_id=track.id,
        score=80.0,
        level=ThreatLevel.CRITICAL,
        factors={},
        created_at=t_shared,
        updated_at=t_shared,
    )
    database.add(threat)

    alert = Alert(
        id="alert-time-shared",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        track_id=track.id,
        reason="Breach",
        metadata_json={},
        created_at=t_shared,
        updated_at=t_shared,
        resolved_at=t_shared + timedelta(seconds=5),
    )
    database.add(alert)
    database.commit()

    service = HistoryService(database)
    items, total = service.get_timeline()
    assert total >= 4

    # Check that for items sharing t_shared, precedence is:
    # DETECTION (1) -> TRACK_UPDATE (2) -> GEOFENCE_EVENT (3) -> THREAT_ASSESSMENT (4) -> ALERT_RAISED (5)
    shared_items = [item for item in items if item.timestamp.replace(tzinfo=None) == t_shared]
    event_types = [item.event_type for item in shared_items]

    assert TimelineEventType.DETECTION in event_types
    assert TimelineEventType.TRACK_UPDATE in event_types
    assert TimelineEventType.GEOFENCE_EVENT in event_types
    assert TimelineEventType.THREAT_ASSESSMENT in event_types
    assert TimelineEventType.ALERT_RAISED in event_types

    # Verify detection comes before threat assessment
    det_idx = event_types.index(TimelineEventType.DETECTION)
    threat_idx = event_types.index(TimelineEventType.THREAT_ASSESSMENT)
    assert det_idx < threat_idx
