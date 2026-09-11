"""Integration tests for Stage S9 Multi-Autopilot Hardware Abstraction Layer."""

import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_s9_autopilot_list_and_validation():
    """Verify listing supported autopilots and validating capability health status via REST API."""
    res = client.get("/api/v1/simulation/autopilots")
    assert res.status_code == 200
    data = res.json()
    assert len(data) >= 3

    types = [a["autopilot_type"] for a in data]
    assert "ARDUPILOT" in types
    assert "PX4" in types
    assert "MOCK" in types

    res_val = client.post("/api/v1/simulation/autopilots/validate", json={"autopilot_type": "PX4"})
    assert res_val.status_code == 200
    val_data = res_val.json()
    assert val_data["autopilot_type"] == "PX4"
    assert "environment_blocked" in val_data


def test_s9_mission_translation_rest_api():
    """Verify translating a compiled mission via REST API endpoint."""
    res = client.post("/api/v1/simulation/autopilots/translate-mission", json={
        "target_autopilot": "PX4",
        "compiled_mission": {
            "mission_id": "m-rest-1",
            "version": 1,
            "vehicle_id": "v1",
            "scenario_id": "s1",
            "compiled_mission_hash": "hash-abc",
            "items": [
                {"sequence": 1, "command_type": "TAKEOFF", "latitude": 37.7749, "longitude": -122.4194, "altitude_m": 12.0, "acceptance_radius_m": 2.0, "loiter_duration_s": 0.0},
                {"sequence": 2, "command_type": "WAYPOINT", "latitude": 37.7755, "longitude": -122.4190, "altitude_m": 18.0, "acceptance_radius_m": 3.0, "loiter_duration_s": 0.0},
                {"sequence": 3, "command_type": "LAND", "latitude": 37.7755, "longitude": -122.4190, "altitude_m": 0.0, "acceptance_radius_m": 2.0, "loiter_duration_s": 0.0},
            ]
        }
    })
    assert res.status_code == 200
    data = res.json()
    assert data["valid"] is True
    assert data["translated_count"] == 3
    assert data["autopilot_type"] == "PX4"
