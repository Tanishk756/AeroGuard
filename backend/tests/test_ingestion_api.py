"""F2 sensor and detection API tests."""

from datetime import UTC, datetime

from sqlalchemy import select

from app.models.role import Role
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus


def create_sensor(database):
    item = Sensor(name="API Sensor", source_type="synthetic", source_class=SensorSourceClass.SIMULATION)
    database.add(item)
    database.commit()
    return item


def promote_user(database, user):
    role = database.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    user.roles.append(role)
    database.commit()


def payload():
    return {"source_detection_id": "api-1", "timestamp": datetime.now(UTC).isoformat(), "latitude": 1, "longitude": 2, "confidence": 0.7, "source_class": "SIMULATION", "source_type": "synthetic"}


def test_sensor_api_and_ingestion_rbac(client, database, rbac_user):
    item = create_sensor(database)
    assert client.get("/api/v1/sensors").status_code == 401
    client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    assert client.get("/api/v1/sensors").status_code == 403
    promote_user(database, rbac_user)
    assert client.get("/api/v1/sensors").status_code == 200
    created = client.post(f"/api/v1/sensors/{item.id}/detections", json=payload())
    assert created.status_code == 201
    assert created.json()["created"] is True
    duplicate = client.post(f"/api/v1/sensors/{item.id}/detections", json=payload())
    assert duplicate.status_code == 200
    assert duplicate.json()["created"] is False


def test_ingestion_api_rejects_unknown_disabled_and_invalid_data(client, database, rbac_user):
    item = create_sensor(database)
    client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    promote_user(database, rbac_user)
    assert client.post("/api/v1/sensors/missing/detections", json=payload()).status_code == 404
    item.status = SensorStatus.DISABLED
    database.commit()
    assert client.post(f"/api/v1/sensors/{item.id}/detections", json=payload()).status_code == 403
    invalid = payload()
    invalid["latitude"] = 91
    assert client.post(f"/api/v1/sensors/{item.id}/detections", json=invalid).status_code == 422