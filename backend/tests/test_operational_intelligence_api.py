"""API integration tests for alerts, threats, and geofences endpoints."""

from datetime import datetime, timedelta

from sqlalchemy import select

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.geofence import Geofence
from app.models.role import Role
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackState


def assign_role(database, user, role_name: str = "OPERATOR"):
    role = database.scalar(select(Role).where(Role.name == role_name))
    user.roles.append(role)
    database.commit()


def test_threats_api_authentication_and_authorization(client, database, rbac_user):
    t0 = datetime(2026, 8, 26, 12, 0, 0)
    track = Track(
        id="track-api-th-1",
        state=TrackState.ACTIVE,
        first_seen_at=t0,
        last_seen_at=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.85,
        classification="UAV",
    )
    threat = ThreatAssessment(
        id="th-api-1",
        track_id=track.id,
        score=75.5,
        level=ThreatLevel.HIGH,
        factors={"score": 75.5, "level": "HIGH"},
        created_at=t0,
        updated_at=t0,
    )
    database.add_all([track, threat])
    database.commit()

    # 1. Unauthenticated requests -> 401
    assert client.get("/api/v1/threats").status_code == 401
    assert client.get(f"/api/v1/threats/{track.id}").status_code == 401

    # 2. Authenticated user without threats.read -> 403
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert client.get("/api/v1/threats").status_code == 403
    assert client.get(f"/api/v1/threats/{track.id}").status_code == 403

    # 3. Grant OPERATOR role (which has threats.read) -> 200
    assign_role(database, rbac_user, "OPERATOR")
    res_list = client.get("/api/v1/threats")
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data["items"]) >= 1
    assert any(item["track_id"] == track.id for item in data["items"])

    res_detail = client.get(f"/api/v1/threats/{track.id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["track_id"] == track.id
    assert res_detail.json()["level"] == "HIGH"

    # 4. 404 on unknown track
    assert client.get("/api/v1/threats/non-existent-track").status_code == 404


def test_threats_api_filtering_and_pagination(client, database, rbac_user):
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    t0 = datetime(2026, 8, 26, 12, 0, 0)
    for i in range(3):
        tr = Track(
            id=f"track-th-page-{i}",
            state=TrackState.ACTIVE,
            first_seen_at=t0,
            last_seen_at=t0 + timedelta(seconds=i),
            latitude=37.7749,
            longitude=-122.4194,
            confidence=0.85,
        )
        th = ThreatAssessment(
            id=f"th-page-{i}",
            track_id=tr.id,
            score=30.0 + i * 25.0,  # 30 (MED), 55 (HIGH), 80 (CRIT)
            level=ThreatLevel.MEDIUM if i == 0 else (ThreatLevel.HIGH if i == 1 else ThreatLevel.CRITICAL),
            factors={"score": 30.0 + i * 25.0},
            created_at=t0 + timedelta(seconds=i),
            updated_at=t0 + timedelta(seconds=i),
        )
        database.add_all([tr, th])
    database.commit()

    # Filter by level
    res_crit = client.get("/api/v1/threats?level=CRITICAL")
    assert res_crit.status_code == 200
    assert len(res_crit.json()["items"]) >= 1

    # Filter by min_score
    res_min = client.get("/api/v1/threats?min_score=50.0")
    assert res_min.status_code == 200
    assert len(res_min.json()["items"]) >= 2

    # Pagination: limit=1
    res_p1 = client.get("/api/v1/threats?limit=1")
    assert res_p1.status_code == 200
    p1_data = res_p1.json()
    assert len(p1_data["items"]) == 1
    assert p1_data["next_cursor"] is not None

    res_p2 = client.get(f"/api/v1/threats?limit=1&cursor={p1_data['next_cursor']}")
    assert res_p2.status_code == 200
    p2_data = res_p2.json()
    assert len(p2_data["items"]) == 1
    assert p2_data["items"][0]["id"] != p1_data["items"][0]["id"]


def test_alerts_api_authentication_and_authorization(client, database, rbac_user):
    t0 = datetime(2026, 8, 26, 12, 0, 0)
    track = Track(
        id="t-al-api-1",
        state=TrackState.ACTIVE,
        first_seen_at=t0,
        last_seen_at=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.85,
    )
    alert = Alert(
        id="alert-api-1",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        track_id=track.id,
        reason="Breach alert",
        metadata_json={"geofence_id": "g-1"},
        created_at=t0,
        updated_at=t0,
    )
    database.add_all([track, alert])
    database.commit()

    # 1. Unauthenticated requests -> 401
    assert client.get("/api/v1/alerts").status_code == 401
    assert client.get(f"/api/v1/alerts/{alert.id}").status_code == 401

    # 2. Authenticated user without alerts.read -> 403
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert client.get("/api/v1/alerts").status_code == 403
    assert client.get(f"/api/v1/alerts/{alert.id}").status_code == 403

    # 3. Grant OPERATOR role (which has alerts.read) -> 200
    assign_role(database, rbac_user, "OPERATOR")
    res_list = client.get("/api/v1/alerts")
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data["items"]) >= 1
    assert any(item["id"] == alert.id for item in data["items"])

    res_detail = client.get(f"/api/v1/alerts/{alert.id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == alert.id

    # 4. 404 on missing alert
    assert client.get("/api/v1/alerts/non-existent-alert").status_code == 404


def test_alerts_api_filtering_and_pagination(client, database, rbac_user):
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    t0 = datetime(2026, 8, 26, 12, 0, 0)
    a1 = Alert(
        id="alert-f-1",
        type=AlertType.TRACK_DETECTED,
        severity=AlertSeverity.LOW,
        status=AlertStatus.OPEN,
        reason="Track detected",
        metadata_json={},
        created_at=t0,
        updated_at=t0,
    )
    a2 = Alert(
        id="alert-f-2",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        reason="Breach",
        metadata_json={},
        created_at=t0 + timedelta(seconds=10),
        updated_at=t0 + timedelta(seconds=10),
    )
    database.add_all([a1, a2])
    database.commit()

    # Filter by severity
    res_crit = client.get("/api/v1/alerts?severity=CRITICAL")
    assert res_crit.status_code == 200
    assert len(res_crit.json()["items"]) >= 1
    assert any(item["id"] == "alert-f-2" for item in res_crit.json()["items"])

    # Filter by type
    res_type = client.get("/api/v1/alerts?type=TRACK_DETECTED")
    assert res_type.status_code == 200
    assert len(res_type.json()["items"]) >= 1
    assert any(item["id"] == "alert-f-1" for item in res_type.json()["items"])


def test_geofences_api_authentication_and_authorization(client, database, rbac_user):
    t0 = datetime(2026, 8, 26, 12, 0, 0)
    geo = Geofence(
        id="geo-api-1",
        name="API Perimeter",
        enabled=True,
        geometry={"type": "bbox", "min_lat": 37.0, "max_lat": 38.0, "min_lon": -123.0, "max_lon": -122.0},
        min_altitude=0.0,
        max_altitude=500.0,
        metadata_json={"tag": "critical"},
        created_at=t0,
        updated_at=t0,
    )
    database.add(geo)
    database.commit()

    # 1. Unauthenticated requests -> 401
    assert client.get("/api/v1/geofences").status_code == 401
    assert client.get(f"/api/v1/geofences/{geo.id}").status_code == 401

    # 2. Authenticated user without scenarios.read -> 403
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert client.get("/api/v1/geofences").status_code == 403
    assert client.get(f"/api/v1/geofences/{geo.id}").status_code == 403

    # 3. Grant OPERATOR role (which has scenarios.read) -> 200
    assign_role(database, rbac_user, "OPERATOR")
    res_list = client.get("/api/v1/geofences")
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["name"] == "API Perimeter"
    assert data["items"][0]["geometry"]["type"] == "bbox"

    res_detail = client.get(f"/api/v1/geofences/{geo.id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == geo.id

    # 4. 404 on missing geofence
    assert client.get("/api/v1/geofences/non-existent-geofence").status_code == 404
