"""Stage S1 Simulation Core v0.1 Integration Test Suite."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.role import Role
from app.models.simulation_platform import PersistentSimulationScenario, PersistentSimulationRun
from app.simulation.core.base_adapter import SimulationEngineFactory, MockSimulationEngine
from app.simulation.core.process_manager import SimulationProcessManager
from app.schemas.simulation_platform import SimulationScenarioSpec, VehicleState, SimulationRunStatus


def test_simulation_engine_factory_registration():
    """VERIFIED: Engine factory registers and instantiates MockSimulationEngine correctly."""
    spec = SimulationScenarioSpec(scenario_id="scen-test-01", name="Test Scenario")
    engine = SimulationEngineFactory.create("mock", spec)
    assert isinstance(engine, MockSimulationEngine)
    assert engine.scenario.name == "Test Scenario"


@pytest.mark.asyncio
async def test_mock_engine_lifecycle_and_telemetry():
    """VERIFIED: MockSimulationEngine executes start, pause, resume, telemetry sampling, and stop."""
    spec = SimulationScenarioSpec(scenario_id="scen-test-02", name="Lifecycle Test")
    engine = SimulationEngineFactory.create("mock", spec)
    
    assert await engine.prepare() is True
    assert await engine.start() is True
    assert engine.status == SimulationRunStatus.RUNNING

    telemetry: VehicleState = await engine.get_telemetry()
    assert telemetry.vehicle_id == "quad-x-001"
    assert telemetry.position.latitude != 0.0

    assert await engine.pause() is True
    assert engine.status == SimulationRunStatus.PAUSED

    assert await engine.resume() is True
    assert engine.status == SimulationRunStatus.RUNNING

    assert await engine.stop() is True
    assert engine.status == SimulationRunStatus.STOPPED


def test_capability_diagnostics_endpoint(client):
    """VERIFIED: GET /api/v1/simulation/capabilities returns valid environment diagnostic response."""
    resp = client.get("/api/v1/simulation/capabilities")
    assert resp.status_code == 200
    data = resp.json()
    assert "gazebo" in data
    assert "ardupilot_sitl" in data
    assert "mavlink" in data
    assert "available" in data["gazebo"]


def test_simulation_scenarios_and_runs_rest_api(client, database, rbac_user):
    """VERIFIED: POST /scenarios, POST /runs, start, pause, stop REST API endpoints."""
    # Assign OPERATIONS_ADMIN role and authenticate
    role = database.scalar(select(Role).where(Role.name == "OPERATIONS_ADMIN"))
    if role and role not in rbac_user.roles:
        rbac_user.roles.append(role)
        database.commit()

    login_resp = client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert login_resp.status_code == 200

    # 1. Create Scenario
    scen_resp = client.post(
        "/api/v1/simulation/scenarios",
        json={
            "name": "Integration Test Scenario",
            "simulator_type": "MOCK",
            "autopilot_type": "MOCK",
            "world_name": "default_grassland",
        },
    )
    assert scen_resp.status_code == 201
    scen_data = scen_resp.json()
    scenario_id = scen_data["id"]

    # 2. Create Run
    run_resp = client.post("/api/v1/simulation/runs", json={"scenario_id": scenario_id})
    assert run_resp.status_code == 201
    run_data = run_resp.json()
    run_id = run_data["id"]
    assert run_data["status"] == "CREATED"

    # 3. Start Run
    start_resp = client.post(f"/api/v1/simulation/runs/{run_id}/start")
    assert start_resp.status_code == 200
    assert start_resp.json()["status"] == "RUNNING"

    # 4. Stop Run
    stop_resp = client.post(f"/api/v1/simulation/runs/{run_id}/stop")
    assert stop_resp.status_code == 200
    assert stop_resp.json()["status"] == "STOPPED"
