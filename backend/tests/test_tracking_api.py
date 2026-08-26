"""API integration tests for track query and history endpoints."""

from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.models.detection import Detection
from app.models.role import Role
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.track import Track, TrackHistory, TrackState
from app.tracking.service import TrackingService


def create_sensor(database):
    sensor = Sensor(
        id="sensor-api-1",
        name="API Radar",
        source_type="radar",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
    )
    database.add(sensor)
    database.commit()
    return sensor


def assign_role(database, user, role_name: str = "OPERATOR"):
    role = database.scalar(select(Role).where(Role.name == role_name))
    user.roles.append(role)
    database.commit()


def test_tracks_api_authentication_and_authorization(client, database, rbac_user):
    sensor = create_sensor(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)
    det = Detection(
        id="det-api-auth-1",
        sensor_id=sensor.id,
        source_detection_id="src-api-auth-1",
        timestamp=t0,
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

    service = TrackingService(database)
    result = service.process_detection(det)
    track_id = result.track.id

    # 1. Unauthenticated requests -> 401
    assert client.get("/api/v1/tracks").status_code == 401
    assert client.get(f"/api/v1/tracks/{track_id}").status_code == 401
    assert client.get(f"/api/v1/tracks/{track_id}/history").status_code == 401

    # 2. Authenticated user without tracks.read -> 403
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert client.get("/api/v1/tracks").status_code == 403
    assert client.get(f"/api/v1/tracks/{track_id}").status_code == 403
    assert client.get(f"/api/v1/tracks/{track_id}/history").status_code == 403

    # 3. Grant OPERATOR role (which has tracks.read) -> 200
    assign_role(database, rbac_user, "OPERATOR")
    res_list = client.get("/api/v1/tracks")
    assert res_list.status_code == 200
    data = res_list.json()
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == track_id

    res_detail = client.get(f"/api/v1/tracks/{track_id}")
    assert res_detail.status_code == 200
    assert res_detail.json()["id"] == track_id
    assert res_detail.json()["state"] == "NEW"

    res_hist = client.get(f"/api/v1/tracks/{track_id}/history")
    assert res_hist.status_code == 200
    assert len(res_hist.json()["items"]) == 1
    assert res_hist.json()["items"][0]["sequence"] == 1


def test_tracks_api_filtering_and_pagination(client, database, rbac_user):
    sensor = create_sensor(database)
    service = TrackingService(database)
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Create Track 1 (UAV, NEW)
    d1 = Detection(
        id="det-page-1",
        sensor_id=sensor.id,
        source_detection_id="src-page-1",
        timestamp=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.8,
        classification="UAV",
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    database.add(d1)
    database.commit()
    r1 = service.process_detection(d1)

    # Create Track 2 (PLANE, NEW)
    d2 = Detection(
        id="det-page-2",
        sensor_id=sensor.id,
        source_detection_id="src-page-2",
        timestamp=t0 + timedelta(seconds=10),
        latitude=40.7128,
        longitude=-74.0060,
        confidence=0.9,
        classification="PLANE",
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    database.add(d2)
    database.commit()
    r2 = service.process_detection(d2)

    # Log in as OPERATOR
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    # Filter by classification
    res_uav = client.get("/api/v1/tracks?classification=UAV")
    assert res_uav.status_code == 200
    items = res_uav.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == r1.track.id

    # Filter by state
    res_state = client.get("/api/v1/tracks?state=NEW")
    assert res_state.status_code == 200
    assert len(res_state.json()["items"]) == 2

    res_active = client.get("/api/v1/tracks?state=ACTIVE")
    assert res_active.status_code == 200
    assert len(res_active.json()["items"]) == 0

    # Pagination: limit=1
    res_p1 = client.get("/api/v1/tracks?limit=1")
    assert res_p1.status_code == 200
    page1 = res_p1.json()
    assert len(page1["items"]) == 1
    assert page1["next_cursor"] is not None

    res_p2 = client.get(f"/api/v1/tracks?limit=1&cursor={page1['next_cursor']}")
    assert res_p2.status_code == 200
    page2 = res_p2.json()
    assert len(page2["items"]) == 1
    assert page2["items"][0]["id"] != page1["items"][0]["id"]


def test_tracks_api_not_found_and_validation(client, database, rbac_user):
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "VIEWER")

    # 404 on missing track
    assert client.get("/api/v1/tracks/non-existent-track-id").status_code == 404
    assert client.get("/api/v1/tracks/non-existent-track-id/history").status_code == 404

    # 400 on invalid date range
    res_bad_dates = client.get(
        "/api/v1/tracks?last_seen_from=2026-08-26T14:00:00Z&last_seen_to=2026-08-26T12:00:00Z"
    )
    assert res_bad_dates.status_code == 400
