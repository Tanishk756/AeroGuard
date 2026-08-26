"""Tests for deterministic read-only historical replay engine."""

from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.audit import AuditEvent
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory, TrackState
from app.replay.engine import ReplayEngine
from app.replay.models import ReplayConfig
from app.schemas.replay import ReplayFilter, ReplayRequest


def _seed_replay_dataset(db: Session) -> tuple[datetime, datetime]:
    sensor = Sensor(
        id="radar-rep-01",
        name="Replay Radar",
        source_type="RADAR",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_metadata={"latitude": 37.7749, "longitude": -122.4194},
    )
    db.add(sensor)

    start_time = datetime(2026, 8, 26, 16, 0, 0)
    end_time = datetime(2026, 8, 26, 16, 0, 30)

    track = Track(
        id="TRK-REP-001",
        state=TrackState.ACTIVE,
        first_seen_at=start_time,
        last_seen_at=end_time,
        latitude=37.7749,
        longitude=-122.4194,
        source_count=1,
        confidence=0.95,
        classification="DRONE",
    )
    db.add(track)
    db.flush()

    for i in range(6):
        t = start_time + timedelta(seconds=i * 5)
        det = Detection(
            id=f"det-rep-{i}",
            sensor_id=sensor.id,
            source_detection_id=f"src-rep-{i}",
            timestamp=t,
            latitude=37.7749 + i * 0.001,
            longitude=-122.4194 + i * 0.001,
            altitude=50.0 + i * 5.0,
            confidence=0.95,
            source_class=SensorSourceClass.SIMULATION,
            source_type="RADAR",
            track_id=track.id,
        )
        db.add(det)
        hist = TrackHistory(
            id=f"th-rep-{i}",
            track_id=track.id,
            sequence=i + 1,
            timestamp=t,
            latitude=det.latitude,
            longitude=det.longitude,
            altitude=det.altitude,
            confidence=det.confidence,
            state=TrackState.ACTIVE,
            provenance=SensorSourceClass.SIMULATION,
            source_detection_ids=[det.id],
        )
        db.add(hist)

    alert = Alert(
        id="alert-rep-01",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        track_id=track.id,
        reason="Approaching geofence",
        metadata_json={},
        created_at=start_time + timedelta(seconds=10),
        updated_at=start_time + timedelta(seconds=10),
    )
    db.add(alert)

    threat = ThreatAssessment(
        id="threat-rep-01",
        track_id=track.id,
        score=72.0,
        level=ThreatLevel.HIGH,
        factors={"proximity": 0.8},
        created_at=start_time + timedelta(seconds=10),
        updated_at=start_time + timedelta(seconds=10),
    )
    db.add(threat)
    db.commit()

    return start_time, end_time


def test_replay_engine_stepping_and_read_only_guarantee(database: Session):
    start_time, end_time = _seed_replay_dataset(database)

    # Capture initial table counts
    det_count_before = database.scalar(select(func.count(Detection.id)))
    track_count_before = database.scalar(select(func.count(Track.id)))
    hist_count_before = database.scalar(select(func.count(TrackHistory.id)))
    alert_count_before = database.scalar(select(func.count(Alert.id)))
    threat_count_before = database.scalar(select(func.count(ThreatAssessment.id)))
    audit_count_before = database.scalar(select(func.count(AuditEvent.id)))

    config = ReplayConfig(
        start_time=start_time,
        end_time=end_time,
        step_interval_seconds=5.0,
        filters=ReplayFilter(),
    )
    engine = ReplayEngine(database, config)

    # Initial snapshot at start
    s0 = engine.get_snapshot_at(start_time, step_idx=0)
    assert s0.step_index == 0
    assert not s0.is_complete
    assert len(s0.active_tracks) == 1
    assert s0.active_tracks[0].altitude == 50.0

    # Advance 2 steps (t = start + 10s)
    s2 = engine.step(steps=2)
    assert s2.step_index == 2
    assert len(s2.active_alerts) == 1
    assert len(s2.active_threats) == 1
    assert s2.active_tracks[0].altitude == 60.0

    # Advance to end
    s_end = engine.step(steps=4)
    assert s_end.is_complete
    assert s_end.active_tracks[0].altitude == 75.0

    # Reset
    engine.reset()
    assert engine.step_index == 0
    assert engine.current_time == start_time

    # Verify zero database mutations
    assert database.scalar(select(func.count(Detection.id))) == det_count_before
    assert database.scalar(select(func.count(Track.id))) == track_count_before
    assert database.scalar(select(func.count(TrackHistory.id))) == hist_count_before
    assert database.scalar(select(func.count(Alert.id))) == alert_count_before
    assert database.scalar(select(func.count(ThreatAssessment.id))) == threat_count_before
    assert database.scalar(select(func.count(AuditEvent.id))) == audit_count_before
