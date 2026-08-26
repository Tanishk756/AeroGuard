"""Tests for bounded historical queries layer."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.history.queries import (
    get_track_state_at,
    query_historical_alerts,
    query_historical_detections,
    query_historical_threats,
    query_historical_track_points,
    validate_time_window,
)
from app.history.service import HistoryService
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory, TrackState
from app.models.user import User


def _seed_test_history_data(db: Session) -> tuple[Sensor, Track, list[Detection]]:
    sensor = Sensor(
        id="radar-hist-01",
        name="Historical Radar",
        source_type="RADAR",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_metadata={"latitude": 37.7749, "longitude": -122.4194},
    )
    db.add(sensor)

    base_time = datetime(2026, 8, 26, 10, 0, 0)
    track = Track(
        id="TRK-HIST-001",
        state=TrackState.ACTIVE,
        first_seen_at=base_time,
        last_seen_at=base_time + timedelta(seconds=30),
        latitude=37.7749,
        longitude=-122.4194,
        source_count=1,
        confidence=0.92,
        classification="DRONE",
    )
    db.add(track)
    db.flush()

    detections = []
    for i in range(5):
        t = base_time + timedelta(seconds=i * 5)
        det = Detection(
            id=f"det-hist-{i}",
            sensor_id=sensor.id,
            source_detection_id=f"src-hist-{i}",
            timestamp=t,
            latitude=37.7749 + i * 0.001,
            longitude=-122.4194 + i * 0.001,
            altitude=100.0 + i * 10.0,
            velocity=15.0,
            heading=45.0,
            confidence=0.90 + i * 0.01,
            classification="DRONE",
            source_class=SensorSourceClass.SIMULATION,
            source_type="RADAR",
            track_id=track.id,
        )
        db.add(det)
        detections.append(det)

        hist = TrackHistory(
            id=f"th-hist-{i}",
            track_id=track.id,
            sequence=i + 1,
            timestamp=t,
            latitude=det.latitude,
            longitude=det.longitude,
            altitude=det.altitude,
            velocity=det.velocity,
            heading=det.heading,
            confidence=det.confidence,
            state=TrackState.ACTIVE,
            provenance=SensorSourceClass.SIMULATION,
            source_detection_ids=[det.id],
        )
        db.add(hist)

    alert = Alert(
        id="alert-hist-01",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        track_id=track.id,
        sensor_id=sensor.id,
        reason="Target penetrated protected zone",
        metadata_json={"zone": "alpha"},
        created_at=base_time + timedelta(seconds=10),
        updated_at=base_time + timedelta(seconds=10),
    )
    db.add(alert)

    threat = ThreatAssessment(
        id="threat-hist-01",
        track_id=track.id,
        score=78.5,
        level=ThreatLevel.HIGH,
        factors={"proximity": 0.85, "speed": 0.70},
        created_at=base_time + timedelta(seconds=10),
        updated_at=base_time + timedelta(seconds=10),
    )
    db.add(threat)
    db.commit()

    return sensor, track, detections


def test_time_window_validation():
    t1 = datetime(2026, 8, 26, 10, 0, 0, tzinfo=UTC)
    t2 = datetime(2026, 8, 26, 12, 0, 0, tzinfo=UTC)
    s, e = validate_time_window(t1, t2)
    assert s == datetime(2026, 8, 26, 10, 0, 0)
    assert e == datetime(2026, 8, 26, 12, 0, 0)

    # Invalid: start > end
    with pytest.raises(ValueError, match="start_time must be less than or equal to end_time"):
        validate_time_window(t2, t1)

    # Invalid: exceeds max window (31 days)
    t_far = t1 + timedelta(days=31)
    with pytest.raises(ValueError, match="Time window exceeds maximum allowed limit"):
        validate_time_window(t1, t_far)


def test_query_historical_detections_and_pagination(database: Session):
    sensor, track, detections = _seed_test_history_data(database)
    service = HistoryService(database)

    # Full range query
    t_start = datetime(2026, 8, 26, 10, 0, 0)
    t_end = datetime(2026, 8, 26, 10, 0, 30)
    items, total = service.get_detections(start_time=t_start, end_time=t_end, limit=2, offset=0)
    assert total == 5
    assert len(items) == 2
    assert items[0].id == "det-hist-0"
    assert items[1].id == "det-hist-1"

    # Pagination offset
    items2, _ = service.get_detections(start_time=t_start, end_time=t_end, limit=2, offset=2)
    assert len(items2) == 2
    assert items2[0].id == "det-hist-2"

    # Sensor filter
    items_sensor, total_sensor = service.get_detections(sensor_id=sensor.id)
    assert total_sensor == 5

    items_unknown, total_unknown = service.get_detections(sensor_id="nonexistent-sensor")
    assert total_unknown == 0


def test_query_track_history_and_state_at_t(database: Session):
    _, track, _ = _seed_test_history_data(database)
    service = HistoryService(database)

    points, total = service.get_track_history(track.id)
    assert total == 5
    assert len(points) == 5
    assert [p.sequence for p in points] == [1, 2, 3, 4, 5]

    # State at time T = exact match at t=10s (seq=3)
    t_10 = datetime(2026, 8, 26, 10, 0, 10)
    st = service.get_track_state_at_time(track.id, t_10)
    assert st is not None
    assert st.sequence == 3
    assert st.altitude == 120.0

    # State at time T = between 10s and 15s (should return point at 10s)
    t_12 = datetime(2026, 8, 26, 10, 0, 12)
    st_12 = service.get_track_state_at_time(track.id, t_12)
    assert st_12 is not None
    assert st_12.sequence == 3

    # State before first observation
    t_early = datetime(2026, 8, 26, 9, 59, 0)
    st_early = service.get_track_state_at_time(track.id, t_early)
    assert st_early is None


def test_query_historical_alerts_and_threats(database: Session):
    _, track, _ = _seed_test_history_data(database)
    service = HistoryService(database)

    alerts, total_a = service.get_alerts(track_id=track.id)
    assert total_a == 1
    assert alerts[0].type == AlertType.GEOFENCE_BREACH
    assert alerts[0].severity == AlertSeverity.HIGH

    threats, total_th = service.get_threats(track_id=track.id)
    assert total_th == 1
    assert threats[0].score == 78.5
    assert threats[0].level == ThreatLevel.HIGH


def test_f6_end_to_end_pipeline_and_historical_consistency(database: Session, rbac_user: User):
    """End-to-end test executing an F5 scenario then querying all F6 historical, timeline, analytics, and replay components."""
    from app.analytics.service import AnalyticsService
    from app.models.geofence import Geofence
    from app.models.scenario import Scenario, ScenarioStatus
    from app.replay.engine import ReplayEngine
    from app.replay.models import ReplayConfig
    from app.schemas.replay import ReplayFilter, ReplayRequest
    from app.schemas.scenario import ScenarioConfiguration, ScenarioSensorDefinition, ScenarioTargetDefinition, ScenarioWaypoint
    from app.simulation.service import ScenarioExecutionService

    start_time = datetime.now(UTC).replace(microsecond=0) - timedelta(minutes=10)

    # 1. Active Geofence
    geofence = Geofence(
        id="geo-e2e-f6",
        name="E2E Geofence",
        enabled=True,
        min_altitude=0.0,
        max_altitude=500.0,
        geometry={
            "type": "Polygon",
            "coordinates": [
                [
                    [-122.4200, 37.7740],
                    [-122.4100, 37.7740],
                    [-122.4100, 37.7800],
                    [-122.4200, 37.7800],
                    [-122.4200, 37.7740],
                ]
            ],
        },
    )
    database.add(geofence)

    # 2. Scenario
    config = ScenarioConfiguration(
        seed=12345,
        duration_seconds=30.0,
        tick_rate_hz=1.0,
        start_time=start_time,
        targets=[
            ScenarioTargetDefinition(
                target_id="tgt-e2e-01",
                initial_latitude=37.7745,
                initial_longitude=-122.4190,
                initial_altitude=100.0,
                velocity=20.0,
                heading=45.0,
                classification="uav",
                waypoints=[
                    ScenarioWaypoint(latitude=37.7770, longitude=-122.4150, altitude=120.0, speed_mps=20.0)
                ],
            )
        ],
        sensors=[
            ScenarioSensorDefinition(
                sensor_id="sim-radar-e2e",
                modality="radar",
                latitude=37.7740,
                longitude=-122.4200,
                altitude=10.0,
                range_meters=10000.0,
                detection_probability=1.0,
                position_uncertainty_meters=2.0,
            )
        ],
        geofence_ids=[geofence.id],
    )
    scenario = Scenario(
        id="scen-e2e-f6",
        name="E2E F6 Test Scenario",
        description="E2E F6 Test Scenario Description",
        created_by_user_id=rbac_user.id,
        status=ScenarioStatus.READY,
        configuration_metadata=config.model_dump(mode="json"),
    )
    database.add(scenario)
    database.commit()

    # Step simulation 5 ticks
    sim_service = ScenarioExecutionService(database)
    sim_service.prepare_scenario(scenario.id)
    status_resp = sim_service.step(scenario.id, ticks=5)
    assert status_resp.tick_count == 5
    assert status_resp.processed_detections_count >= 5

    # Capture row counts after F5 execution
    det_count = database.scalar(select(func.count(Detection.id)))
    track_count = database.scalar(select(func.count(Track.id)))
    alert_count = database.scalar(select(func.count(Alert.id)))
    threat_count = database.scalar(select(func.count(ThreatAssessment.id)))

    assert det_count >= 5
    assert track_count >= 1

    # 3. F6 Historical queries
    hist_service = HistoryService(database)
    dets, total_d = hist_service.get_detections()
    assert total_d == det_count
    assert len(dets) >= 5

    track_obj = database.scalars(select(Track)).first()
    assert track_obj is not None

    track_points, total_pts = hist_service.get_track_history(track_obj.id)
    assert total_pts >= 1

    t_query = start_time + timedelta(seconds=3)
    st = hist_service.get_track_state_at_time(track_obj.id, t_query)
    assert st is not None

    alerts, total_a = hist_service.get_alerts()
    threats, total_th = hist_service.get_threats()
    timeline, total_tl = hist_service.get_timeline()
    assert total_tl >= det_count

    # 4. F6 Analytics
    analytics_service = AnalyticsService(database)
    summary = analytics_service.get_summary(
        window_start=start_time,
        window_end=start_time + timedelta(seconds=30),
    )
    assert summary.detections.total_detections == det_count
    assert summary.tracks.total_tracks == track_count

    # 5. F6 Replay
    rep_config = ReplayConfig(
        start_time=start_time,
        end_time=start_time + timedelta(seconds=30),
        step_interval_seconds=1.0,
        filters=ReplayFilter(),
    )
    rep_engine = ReplayEngine(database, rep_config)
    snap0 = rep_engine.get_snapshot_at(start_time)
    snap3 = rep_engine.step(steps=3)
    assert snap3.step_index == 3
    assert len(snap3.active_tracks) >= 1

    # Verify zero database mutations throughout all F6 queries
    assert database.scalar(select(func.count(Detection.id))) == det_count
    assert database.scalar(select(func.count(Track.id))) == track_count
    assert database.scalar(select(func.count(Alert.id))) == alert_count
    assert database.scalar(select(func.count(ThreatAssessment.id))) == threat_count
