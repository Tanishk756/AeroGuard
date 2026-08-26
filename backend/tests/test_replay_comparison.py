"""Tests for deterministic replay comparison."""

from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory, TrackState
from app.replay.comparison import compare_replay_runs
from app.schemas.replay import (
    ReplayComparisonRequest,
    ReplayFilter,
    ReplayRequest,
)


def test_replay_comparison_identical_and_differing_runs(database: Session):
    sensor = Sensor(
        id="radar-comp-01",
        name="Comp Radar",
        source_type="RADAR",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_metadata={"latitude": 37.7749, "longitude": -122.4194},
    )
    database.add(sensor)

    t0 = datetime(2026, 8, 26, 18, 0, 0)
    track = Track(
        id="TRK-COMP-001",
        state=TrackState.ACTIVE,
        first_seen_at=t0,
        last_seen_at=t0 + timedelta(seconds=20),
        latitude=37.7749,
        longitude=-122.4194,
        source_count=1,
        confidence=0.90,
    )
    database.add(track)
    database.flush()

    for i in range(3):
        t = t0 + timedelta(seconds=i * 5)
        det = Detection(
            id=f"det-comp-{i}",
            sensor_id=sensor.id,
            source_detection_id=f"src-comp-{i}",
            timestamp=t,
            latitude=37.7749,
            longitude=-122.4194,
            confidence=0.90,
            source_class=SensorSourceClass.SIMULATION,
            source_type="RADAR",
            track_id=track.id,
        )
        database.add(det)

    alert = Alert(
        id="alert-comp-01",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.MEDIUM,
        status=AlertStatus.OPEN,
        track_id=track.id,
        reason="Zone Warning",
        metadata_json={},
        created_at=t0 + timedelta(seconds=5),
        updated_at=t0 + timedelta(seconds=5),
    )
    database.add(alert)
    database.commit()

    # 1. Identical comparison (two queries over the exact same window)
    req1 = ReplayRequest(
        start_time=t0,
        end_time=t0 + timedelta(seconds=15),
        step_interval_seconds=1.0,
        filters=ReplayFilter(),
    )
    req2 = ReplayRequest(
        start_time=t0,
        end_time=t0 + timedelta(seconds=15),
        step_interval_seconds=1.0,
        filters=ReplayFilter(),
    )
    report = compare_replay_runs(database, ReplayComparisonRequest(request_1=req1, request_2=req2))
    assert report.identical
    assert report.total_detections_match
    assert report.total_tracks_match
    assert report.total_alerts_match
    assert len(report.differences) == 0

    # 2. Differing comparison (run 2 has a shorter window with fewer detections/alerts)
    req_short = ReplayRequest(
        start_time=t0,
        end_time=t0 + timedelta(seconds=2),
        step_interval_seconds=1.0,
        filters=ReplayFilter(),
    )
    report_diff = compare_replay_runs(
        database, ReplayComparisonRequest(request_1=req1, request_2=req_short)
    )
    assert not report_diff.identical
    assert not report_diff.total_detections_match
    assert not report_diff.total_alerts_match
    assert len(report_diff.differences) > 0
