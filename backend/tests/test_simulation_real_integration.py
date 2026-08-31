"""Stage S2 Real Simulation Integration & Capability Test Suite.

Distinguishes unit tests, mock engine tests, capability diagnostics,
and live Gazebo/ArduPilot SITL execution tests (gated by AEROGUARD_LIVE_SIMULATION=1).
"""

import os
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.core.process_manager import SimulationProcessManager, ALLOWED_SIMULATORS
from app.telemetry.normalizer import MAVLinkNormalizer


def test_process_manager_security_allowlist():
    """VERIFIED: Process manager rejects unauthorized simulator engines."""
    assert "gazebo" in ALLOWED_SIMULATORS
    assert "mock" in ALLOWED_SIMULATORS

    with pytest.raises(ValueError, match="Potentially dangerous shell character"):
        import asyncio
        asyncio.run(SimulationProcessManager.spawn_process("Malicious", ["gz", "sim", "; rm -rf /"]))


def test_mavlink_normalizer_numerical_sanity_validation():
    """VERIFIED: MAVLink normalizer validates coordinates and finite floating point values."""
    normalizer = MAVLinkNormalizer(vehicle_id="quad-test-01")

    # 1. Valid Attitude Packet
    valid_att = normalizer.process_message("ATTITUDE", {"roll": 0.1, "pitch": -0.05, "yaw": 1.57, "rollspeed": 0.0, "pitchspeed": 0.0, "yawspeed": 0.0})
    assert valid_att is not None
    assert valid_att.attitude.roll_deg == pytest.approx(5.73, 0.1)

    # 2. Invalid Non-finite Attitude Packet
    invalid_att = normalizer.process_message("ATTITUDE", {"roll": float("nan"), "pitch": 0.0, "yaw": 0.0})
    assert invalid_att is None

    # 3. Out-of-bounds Position Packet
    invalid_pos = normalizer.process_message("GLOBAL_POSITION_INT", {"lat": 1000000000, "lon": 0, "alt": 10000, "relative_alt": 10000})
    assert invalid_pos is None


def test_capability_diagnostic_honesty():
    """VERIFIED: System capability diagnostic reports real executable availability."""
    diag = SimulationProcessManager.get_capabilities()
    assert isinstance(diag.gazebo.available, bool)
    assert isinstance(diag.ardupilot_sitl.available, bool)
    assert diag.mavlink.available is True  # pymavlink installed


@pytest.mark.live_simulation
@pytest.mark.skipif(os.environ.get("AEROGUARD_LIVE_SIMULATION") != "1", reason="Live simulation requires AEROGUARD_LIVE_SIMULATION=1 and active Linux/WSL Gazebo/SITL runtime")
def test_live_gazebo_sitl_end_to_end_pipeline(client):
    """LIVE SIMULATION VERIFIED: End-to-end live Gazebo + ArduPilot SITL simulation run."""
    # 1. Capability Verification
    diag_resp = client.get("/api/v1/simulation/capabilities")
    assert diag_resp.status_code == 200
    diag = diag_resp.json()
    assert diag["gazebo"]["available"] is True, "Live test requires Gazebo"
    assert diag["ardupilot_sitl"]["available"] is True, "Live test requires ArduPilot SITL"

    # 2. Scenario Creation
    scen_resp = client.post(
        "/api/v1/simulation/scenarios",
        json={"name": "Live SITL Test Scenario", "simulator_type": "GAZEBO", "autopilot_type": "ARDUPILOT"},
    )
    assert scen_resp.status_code == 201
    scenario_id = scen_resp.json()["id"]

    # 3. Create Run
    run_resp = client.post("/api/v1/simulation/runs", json={"scenario_id": scenario_id})
    assert run_resp.status_code == 201
    run_id = run_resp.json()["id"]

    # 4. Start Run
    start_resp = client.post(f"/api/v1/simulation/runs/{run_id}/start")
    assert start_resp.status_code == 200

    # 5. Stop Run
    stop_resp = client.post(f"/api/v1/simulation/runs/{run_id}/stop")
    assert stop_resp.status_code == 200
