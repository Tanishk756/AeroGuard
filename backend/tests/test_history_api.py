"""Tests for History REST API endpoints."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory, TrackState
from app.models.user import User


def _seed_api_history_dataset(db: Session) -> tuple[Sensor, Track]:
    sensor = Sensor(
        id="radar-api-01",
        name="API Radar",
        source_type="RADAR",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_metadata={"latitude": 37.7749, "longitude": -122.4194},
    )
    db.add(sensor)

    t0 = datetime(2026, 8, 26, 20, 0, 0)
    track = Track(
        id="TRK-API-001",
        state=TrackState.ACTIVE,
        first_seen_at=t0,
        last_seen_at=t0 + timedelta(seconds=10),
        latitude=37.7749,
        longitude=-122.4194,
        source_count=1,
        confidence=0.90,
    )
    db.add(track)
    db.flush()

    det = Detection(
        id="det-api-1",
        sensor_id=sensor.id,
        source_detection_id="src-api-1",
        timestamp=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.90,
        source_class=SensorSourceClass.SIMULATION,
        source_type="RADAR",
        track_id=track.id,
    )
    db.add(det)

    th = TrackHistory(
        id="th-api-1",
        track_id=track.id,
        sequence=1,
        timestamp=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.90,
        state=TrackState.ACTIVE,
        provenance=SensorSourceClass.SIMULATION,
        source_detection_ids=[det.id],
    )
    db.add(th)

    alert = Alert(
        id="alert-api-1",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        track_id=track.id,
        reason="Zone Warning",
        metadata_json={},
        created_at=t0,
        updated_at=t0,
    )
    db.add(alert)

    threat = ThreatAssessment(
        id="threat-api-1",
        track_id=track.id,
        score=65.0,
        level=ThreatLevel.MEDIUM,
        factors={},
        created_at=t0,
        updated_at=t0,
    )
    db.add(threat)
    db.commit()

    return sensor, track


from sqlalchemy import select

from app.models.role import Role


def assign_role(database, user, role_name: str):
    role = database.scalar(select(Role).where(Role.name == role_name))
    if role not in user.roles:
        user.roles.append(role)
        database.commit()


def test_history_api_authentication_and_authorization(client: TestClient, database: Session):
    # Unauthenticated
    res = client.get("/api/v1/history/detections")
    assert res.status_code == 401

    res = client.get("/api/v1/history/tracks/TRK-001")
    assert res.status_code == 401

    res = client.get("/api/v1/history/timeline")
    assert res.status_code == 401


def test_history_api_endpoints_with_authorized_user(
    client: TestClient, database: Session, rbac_user: User
):
    sensor, track = _seed_api_history_dataset(database)
    assign_role(database, rbac_user, "OPERATIONS_ADMIN")
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )

    # 1. Historical detections
    res = client.get("/api/v1/history/detections?limit=10")
    assert res.status_code == 200
    data = res.json()
    assert data["total_count"] >= 1
    assert len(data["items"]) >= 1

    # 2. Historical track points
    res = client.get(f"/api/v1/history/tracks/{track.id}")
    assert res.status_code == 200
    points = res.json()
    assert len(points) == 1
    assert points[0]["sequence"] == 1

    # 3. Track state at T
    res = client.get(f"/api/v1/history/tracks/{track.id}/state?as_of_time=2026-08-26T20:05:00Z")
    assert res.status_code == 200
    st_data = res.json()
    assert st_data["found"]
    assert st_data["state_point"]["sequence"] == 1

    # 4. Historical alerts
    res = client.get("/api/v1/history/alerts")
    assert res.status_code == 200
    assert res.json()["total_count"] >= 1

    # 5. Historical threats
    res = client.get("/api/v1/history/threats")
    assert res.status_code == 200
    assert res.json()["total_count"] >= 1

    # 6. Operational timeline
    res = client.get("/api/v1/history/timeline")
    assert res.status_code == 200
    tl_data = res.json()
    assert tl_data["total_count"] >= 1
    assert len(tl_data["items"]) >= 1

    # 7. Time validation rejection (start > end)
    res_bad = client.get("/api/v1/history/detections?start_time=2026-08-26T21:00:00Z&end_time=2026-08-26T20:00:00Z")
    assert res_bad.status_code == 400
