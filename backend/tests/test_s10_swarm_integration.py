"""Stage S10 Multi-Vehicle Swarm & Formation Control End-to-End Integration & Performance Tests.

Tests REST API operations, database persistence, state transitions, heterogeneous autopilot blending,
and performance determinism benchmarks up to 16 vehicles.
"""

import time
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.main import app
from app.database.session import get_db
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.models.swarm import PersistentSwarm

from app.schemas.simulation_platform import PositionVector, VehicleState, VelocityVector
from app.schemas.swarm import FormationType, SwarmConfiguration, SwarmConstraints, SwarmRole
from app.simulation.core.swarm_engine import SwarmEngine


def test_swarm_api_crud_lifecycle(client, database):

    # 1. Create components & vehicles in DB
    fc = PersistentHardwareComponent(id="comp-fc-01", manufacturer="Holybro", model="Pixhawk 4", category="flight_controller", mass_g=68.0)
    frame = PersistentHardwareComponent(id="comp-frame-01", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="comp-motor-01", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="comp-esc-01", manufacturer="Holybro", model="Tekko32", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="comp-prop-01", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="comp-bat-01", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)

    database.add_all([fc, frame, motor, esc, prop, bat])
    database.commit()

    v1_id = "v-api-01"
    v2_id = "v-api-02"

    v1 = PersistentVehicle(
        id=v1_id,
        name="Test Vehicle 1",
        vehicle_type="quadcopter",
        frame_id=frame.id,
        motor_id=motor.id,
        esc_id=esc.id,
        propeller_id=prop.id,
        battery_id=bat.id,
        flight_controller_id=fc.id,
    )
    v2 = PersistentVehicle(
        id=v2_id,
        name="Test Vehicle 2",
        vehicle_type="quadcopter",
        frame_id=frame.id,
        motor_id=motor.id,
        esc_id=esc.id,
        propeller_id=prop.id,
        battery_id=bat.id,
        flight_controller_id=fc.id,
    )
    database.add_all([v1, v2])
    database.commit()


    # Create Swarm via API
    res = client.post(
        "/api/v1/simulation/swarms",
        json={
            "name": "API Test Swarm Alpha",
            "description": "Integration test swarm",
            "formation_type": "LINE",
            "formation_spacing_m": 10.0,
            "min_separation_m": 5.0,
            "member_vehicle_ids": [v1_id, v2_id],
        },
    )

    assert res.status_code == 201
    swarm_data = res.json()
    swarm_id = swarm_data["id"]
    assert swarm_data["name"] == "API Test Swarm Alpha"
    assert swarm_data["formation_type"] == "LINE"
    assert len(swarm_data["members"]) == 2

    # 2. Get Swarm details
    res_get = client.get(f"/api/v1/simulation/swarms/{swarm_id}")
    assert res_get.status_code == 200
    assert res_get.json()["id"] == swarm_id

    # 3. Change Formation to V_FORMATION
    res_form = client.post(
        f"/api/v1/simulation/swarms/{swarm_id}/formation",
        json={"formation_type": "V_FORMATION", "formation_spacing_m": 15.0},
    )
    assert res_form.status_code == 200
    assert res_form.json()["formation_type"] == "V_FORMATION"
    assert res_form.json()["formation_spacing_m"] == 15.0

    # 4. Query Swarm State & Health
    res_state = client.get(f"/api/v1/simulation/swarms/{swarm_id}/state")
    assert res_state.status_code == 200
    state_json = res_state.json()
    assert state_json["swarm_id"] == swarm_id
    assert state_json["formation_type"] == "V_FORMATION"

    res_health = client.get(f"/api/v1/simulation/swarms/{swarm_id}/health")
    assert res_health.status_code == 200
    health_json = res_health.json()
    assert "health" in health_json

    # 5. Delete Swarm
    res_del = client.delete(f"/api/v1/simulation/swarms/{swarm_id}")
    assert res_del.status_code == 204


def test_swarm_performance_and_determinism_scaling():
    """Benchmark determinism and state update scaling for 4, 8, and 16 vehicles."""
    now = time.time()

    for num_vehicles in [4, 8, 16]:
        config = SwarmConfiguration(
            swarm_id=f"swm-perf-{num_vehicles}",
            name=f"Perf Swarm {num_vehicles}",
            formation={"formation_type": FormationType.V_FORMATION, "spacing_m": 10.0},
        )
        engine = SwarmEngine(config)

        # Register members
        for idx in range(num_vehicles):
            role = SwarmRole.LEADER if idx == 0 else SwarmRole.FOLLOWER
            autopilot = "ARDUPILOT" if idx % 2 == 0 else "PX4"
            engine.register_member(f"perf-v-{idx:02d}", role=role, autopilot_type=autopilot)

        # Inject telemetry for all members
        for idx in range(num_vehicles):
            vid = f"perf-v-{idx:02d}"
            v_state = VehicleState(
                timestamp_utc="2026-09-11T00:00:00Z",
                sim_time_seconds=1.0,
                vehicle_id=vid,
                position=PositionVector(latitude=0.0001 * idx, longitude=-0.0001 * idx, altitude_relative=10.0),
                velocity=VelocityVector(vx=0.0, vy=0.0, vz=0.0),
            )
            engine.update_vehicle_telemetry(v_state, current_time_s=now)

        # Benchmark step timing and determinism
        t_start = time.perf_counter()
        state_run_1 = engine.step(current_time_s=now)
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        # Run second step with identical inputs for determinism check
        state_run_2 = engine.step(current_time_s=now)

        assert state_run_1.health == state_run_2.health
        assert len(state_run_1.vehicle_states) == num_vehicles
        assert t_elapsed_ms < 50.0  # Must execute under 50ms per step
