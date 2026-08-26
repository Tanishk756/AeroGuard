"""API integration tests for scenario CRUD, execution, status, and geofence management."""

from datetime import UTC, datetime
from sqlalchemy import select

from app.models.role import Role


def assign_role(database, user, role_name: str):
    role = database.scalar(select(Role).where(Role.name == role_name))
    if role not in user.roles:
        user.roles.append(role)
        database.commit()


def get_sample_scenario_payload(name: str = "API Test Scenario"):
    return {
        "name": name,
        "description": "Scenario created via REST API",
        "configuration": {
            "seed": 42,
            "duration_seconds": 60.0,
            "tick_rate_hz": 1.0,
            "start_time": "2026-01-01T00:00:00Z",
            "targets": [
                {
                    "target_id": "tgt-api-01",
                    "initial_latitude": 37.7749,
                    "initial_longitude": -122.4194,
                    "initial_altitude": 100.0,
                    "velocity": 15.0,
                    "heading": 0.0,
                    "classification": "uav",
                }
            ],
            "sensors": [
                {
                    "sensor_id": "sim-radar-api-1",
                    "modality": "radar",
                    "latitude": 37.7740,
                    "longitude": -122.4200,
                    "range_meters": 5000.0,
                    "detection_probability": 1.0,
                    "position_uncertainty_meters": 3.0,
                }
            ],
            "geofence_ids": [],
        },
    }


def test_scenarios_api_authentication_and_authorization(client, database, rbac_user):
    # 1. Unauthenticated -> 401
    assert client.get("/api/v1/scenarios").status_code == 401
    assert client.post("/api/v1/scenarios", json=get_sample_scenario_payload()).status_code == 401

    # Login as rbac_user (no roles initially)
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    # 2. Authenticated without permissions -> 403
    assert client.get("/api/v1/scenarios").status_code == 403
    assert client.post("/api/v1/scenarios", json=get_sample_scenario_payload()).status_code == 403

    # 3. Assign RESEARCHER role (has scenarios.read, scenarios.create, scenarios.update, scenarios.run)
    assign_role(database, rbac_user, "RESEARCHER")
    create_res = client.post("/api/v1/scenarios", json=get_sample_scenario_payload())
    assert create_res.status_code == 201
    scenario_id = create_res.json()["id"]

    list_res = client.get("/api/v1/scenarios")
    assert list_res.status_code == 200
    assert len(list_res.json()["items"]) >= 1

    detail_res = client.get(f"/api/v1/scenarios/{scenario_id}")
    assert detail_res.status_code == 200
    assert detail_res.json()["id"] == scenario_id


def test_scenarios_api_crud_and_execution_lifecycle(client, database, rbac_user):
    assign_role(database, rbac_user, "OPERATIONS_ADMIN")
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )

    # 1. Create scenario
    create_res = client.post("/api/v1/scenarios", json=get_sample_scenario_payload("Lifecycle Scenario"))
    assert create_res.status_code == 201
    scenario_id = create_res.json()["id"]

    # 2. Get status
    status_res = client.get(f"/api/v1/scenarios/{scenario_id}/status")
    assert status_res.status_code == 200
    assert status_res.json()["status"] == "READY"
    assert status_res.json()["tick_count"] == 0

    # 3. Start scenario
    start_res = client.post(f"/api/v1/scenarios/{scenario_id}/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "RUNNING"

    # 4. Step scenario by 3 ticks
    step_res = client.post(f"/api/v1/scenarios/{scenario_id}/step", json={"ticks": 3})
    assert step_res.status_code == 200
    assert step_res.json()["tick_count"] == 3
    assert step_res.json()["processed_detections_count"] == 3

    # 5. Pause scenario
    pause_res = client.post(f"/api/v1/scenarios/{scenario_id}/pause")
    assert pause_res.status_code == 200
    assert pause_res.json()["is_paused"] is True

    # 6. Resume scenario
    resume_res = client.post(f"/api/v1/scenarios/{scenario_id}/resume")
    assert resume_res.status_code == 200
    assert resume_res.json()["is_paused"] is False

    # 7. Stop scenario
    stop_res = client.post(f"/api/v1/scenarios/{scenario_id}/stop")
    assert stop_res.status_code == 200

    # 8. Reset scenario
    reset_res = client.post(f"/api/v1/scenarios/{scenario_id}/reset")
    assert reset_res.status_code == 200
    assert reset_res.json()["tick_count"] == 0

    # 9. Update scenario
    update_res = client.put(f"/api/v1/scenarios/{scenario_id}", json={"name": "Renamed Scenario"})
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Renamed Scenario"

    # 10. Delete scenario
    del_res = client.delete(f"/api/v1/scenarios/{scenario_id}")
    assert del_res.status_code == 204

    # 11. 404 after deletion
    assert client.get(f"/api/v1/scenarios/{scenario_id}").status_code == 404


def test_geofences_crud_api(client, database, rbac_user):
    assign_role(database, rbac_user, "OPERATIONS_ADMIN")
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )

    # 1. Create Geofence
    payload = {
        "name": "Airfield Protection Zone",
        "enabled": True,
        "geometry": {
            "type": "polygon",
            "coordinates": [
                [37.77, -122.42],
                [37.78, -122.42],
                [37.78, -122.41],
                [37.77, -122.41],
            ],
        },
        "min_altitude": 0.0,
        "max_altitude": 400.0,
        "metadata": {"zone_type": "restricted"},
    }
    create_res = client.post("/api/v1/geofences", json=payload)
    assert create_res.status_code == 201
    geofence_id = create_res.json()["id"]
    assert create_res.json()["name"] == "Airfield Protection Zone"

    # 2. Get Geofence detail
    get_res = client.get(f"/api/v1/geofences/{geofence_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == geofence_id

    # 3. Update Geofence
    update_res = client.put(f"/api/v1/geofences/{geofence_id}", json={"name": "Expanded Zone", "enabled": False})
    assert update_res.status_code == 200
    assert update_res.json()["name"] == "Expanded Zone"
    assert update_res.json()["enabled"] is False

    # 4. Delete Geofence
    del_res = client.delete(f"/api/v1/geofences/{geofence_id}")
    assert del_res.status_code == 204
    assert client.get(f"/api/v1/geofences/{geofence_id}").status_code == 404
