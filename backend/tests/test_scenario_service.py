"""Integration tests for scenario execution service, lifecycle state machine, and pipeline integration."""

from datetime import UTC, datetime
from uuid import uuid4
import pytest
from sqlalchemy import select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database.base import Base
from app.database.session import create_database_engine
from app.models.alert import Alert, AlertType
from app.models.detection import Detection
from app.models.geofence import Geofence
from app.models.scenario import Scenario, ScenarioStatus
from app.models.sensor import SensorSourceClass
from app.models.threat import ThreatAssessment
from app.models.track import Track, TrackState
from app.schemas.scenario import (
    ScenarioConfiguration,
    ScenarioSensorDefinition,
    ScenarioTargetDefinition,
    ScenarioWaypoint,
)
from app.services.auth import create_user
from app.services.rbac import seed_rbac
from app.simulation.service import ScenarioExecutionService


def create_test_scenario(database, user_id: str, name: str = "Test Scenario", seed: int = 100) -> Scenario:
    config = ScenarioConfiguration(
        seed=seed,
        duration_seconds=30.0,
        tick_rate_hz=1.0,
        start_time=datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC),
        targets=[
            ScenarioTargetDefinition(
                target_id="uav-01",
                initial_latitude=37.7749,
                initial_longitude=-122.4194,
                initial_altitude=120.0,
                velocity=20.0,
                heading=0.0,
                classification="uav",
            )
        ],
        sensors=[
            ScenarioSensorDefinition(
                sensor_id="sim-radar-01",
                modality="radar",
                latitude=37.7740,
                longitude=-122.4200,
                range_meters=5000.0,
                detection_probability=1.0,
                position_uncertainty_meters=2.0,
            )
        ],
    )
    now = datetime.now(UTC).replace(tzinfo=None)
    scenario = Scenario(
        id=str(uuid4()),
        name=name,
        description="Integration test scenario",
        status=ScenarioStatus.READY,
        created_by_user_id=user_id,
        source_class=SensorSourceClass.SIMULATION,
        configuration_metadata=config.model_dump(mode="json"),
        created_at=now,
        updated_at=now,
    )
    database.add(scenario)
    database.commit()
    database.refresh(scenario)
    return scenario


def test_scenario_lifecycle_state_machine(database, rbac_user):
    scenario = create_test_scenario(database, rbac_user.id)
    service = ScenarioExecutionService(database)

    # 1. Initial status READY
    status = service.get_status(scenario.id)
    assert status.status == ScenarioStatus.READY
    assert status.is_paused is False
    assert status.tick_count == 0

    # 2. Start scenario -> RUNNING
    status = service.start_scenario(scenario.id)
    assert status.status == ScenarioStatus.RUNNING
    assert status.is_paused is False

    # 3. Pause scenario -> RUNNING with is_paused=True
    status = service.pause_scenario(scenario.id)
    assert status.is_paused is True

    # 4. Resume scenario -> RUNNING with is_paused=False
    status = service.resume_scenario(scenario.id)
    assert status.is_paused is False

    # 5. Stop scenario -> READY with is_stopped=True
    status = service.stop_scenario(scenario.id)
    assert status.status == ScenarioStatus.READY

    # Cannot resume stopped without reset
    with pytest.raises(ValueError, match="Cannot resume a stopped scenario"):
        service.resume_scenario(scenario.id)

    # Reset scenario -> fresh state
    status = service.reset_scenario(scenario.id)
    assert status.status == ScenarioStatus.READY
    assert status.tick_count == 0


def test_scenario_stepping_and_pipeline_execution(database, rbac_user):
    scenario = create_test_scenario(database, rbac_user.id, seed=42)
    service = ScenarioExecutionService(database)

    # Step 5 ticks
    status = service.step(scenario.id, ticks=5)
    assert status.tick_count == 5
    assert status.generated_detections_count == 5
    assert status.processed_detections_count == 5

    # Verify detections persisted in database
    detections = database.scalars(select(Detection).where(Detection.sensor_id == "sim-radar-01")).all()
    assert len(detections) == 5

    # Verify tracks created and associated
    tracks = database.scalars(select(Track)).all()
    assert len(tracks) == 1
    track = tracks[0]
    # In F3, 5 detections confirms track to ACTIVE
    assert track.state == TrackState.ACTIVE
    assert track.classification == "uav"

    # Verify threat assessment computed
    threat = database.scalar(select(ThreatAssessment).where(ThreatAssessment.track_id == track.id))
    assert threat is not None
    assert threat.score >= 0.0

    # Verify detection alert created
    alerts = database.scalars(select(Alert).where(Alert.track_id == track.id)).all()
    assert len(alerts) >= 1
    assert any(a.type == AlertType.TRACK_DETECTED for a in alerts)


def test_scenario_end_to_end_geofence_breach(database, rbac_user):
    now = datetime.now(UTC).replace(tzinfo=None)
    # Create Geofence directly in path of the UAV target (due North from 37.7749)
    geofence = Geofence(
        id=str(uuid4()),
        name="Critical Perimeter",
        enabled=True,
        geometry={
            "type": "bbox",
            "min_lat": 37.7750,
            "max_lat": 37.7770,
            "min_lon": -122.4210,
            "max_lon": -122.4180,
        },
        min_altitude=0.0,
        max_altitude=500.0,
        metadata_json={},
        created_at=now,
        updated_at=now,
    )
    database.add(geofence)
    database.commit()

    scenario = create_test_scenario(database, rbac_user.id, seed=777)
    service = ScenarioExecutionService(database)

    # Step 10 ticks -> target moves ~200m North directly inside the bounding box
    status = service.step(scenario.id, ticks=10)
    assert status.tick_count == 10

    # Check for GEOFENCE_BREACH alert
    alerts = database.scalars(select(Alert)).all()
    breach_alerts = [a for a in alerts if a.type == AlertType.GEOFENCE_BREACH]
    assert len(breach_alerts) >= 1
    assert breach_alerts[0].severity in ("HIGH", "CRITICAL")


def test_scenario_determinism_across_runs(database, rbac_user):
    seed = 88888
    # Run 1 on database
    scenario1 = create_test_scenario(database, rbac_user.id, name="Run 1", seed=seed)
    service1 = ScenarioExecutionService(database)
    status1 = service1.step(scenario1.id, ticks=6)

    dets1 = database.scalars(
        select(Detection).order_by(Detection.timestamp.asc(), Detection.id.asc())
    ).all()
    det_records1 = [(d.source_detection_id, d.latitude, d.longitude, d.confidence, d.velocity, d.heading) for d in dets1]
    tracks1 = database.scalars(select(Track)).all()
    track_states1 = [(t.state, t.classification, t.source_count, round(t.latitude, 4), round(t.longitude, 4)) for t in tracks1]
    threats1 = database.scalars(select(ThreatAssessment)).all()
    threat_records1 = [(th.score, th.level) for th in threats1]
    alerts1 = database.scalars(select(Alert)).all()
    alert_records1 = [(a.type, a.severity, a.status) for a in alerts1]

    # Run 2 on an isolated fresh database
    engine2 = create_database_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine2)
    session2 = sessionmaker(bind=engine2, autoflush=False, autocommit=False)()
    try:
        seed_rbac(session2)
        user2 = create_user(session2, "user2", "User 2", "u2@example.invalid", "test-pass-123")
        scenario2 = create_test_scenario(session2, user2.id, name="Run 2", seed=seed)
        service2 = ScenarioExecutionService(session2)
        status2 = service2.step(scenario2.id, ticks=6)

        dets2 = session2.scalars(
            select(Detection).order_by(Detection.timestamp.asc(), Detection.id.asc())
        ).all()
        det_records2 = [(d.source_detection_id, d.latitude, d.longitude, d.confidence, d.velocity, d.heading) for d in dets2]
        tracks2 = session2.scalars(select(Track)).all()
        track_states2 = [(t.state, t.classification, t.source_count, round(t.latitude, 4), round(t.longitude, 4)) for t in tracks2]
        threats2 = session2.scalars(select(ThreatAssessment)).all()
        threat_records2 = [(th.score, th.level) for th in threats2]
        alerts2 = session2.scalars(select(Alert)).all()
        alert_records2 = [(a.type, a.severity, a.status) for a in alerts2]

        assert det_records1 == det_records2
        assert track_states1 == track_states2
        assert threat_records1 == threat_records2
        assert alert_records1 == alert_records2
        assert status1.generated_detections_count == status2.generated_detections_count
    finally:
        session2.close()
        Base.metadata.drop_all(engine2)
        engine2.dispose()
