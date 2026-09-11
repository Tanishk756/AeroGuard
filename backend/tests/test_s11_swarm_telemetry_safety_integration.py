"""Stage S11 Swarm Telemetry Stream Fusion & Safety-Action Integration & Performance Tests.

Tests REST API operations, safety event auditing, policy creation, and performance benchmarks up to 32 vehicles.
"""

import time
import pytest
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.models.swarm import PersistentSwarm
from app.schemas.simulation_platform import PositionVector, VehicleState
from app.schemas.swarm_telemetry import SwarmVehicleTelemetry
from app.simulation.core.swarm_aggregation import SwarmAggregationEngine
from app.simulation.core.swarm_safety_action_engine import SwarmSafetyActionEngine
from app.simulation.core.swarm_telemetry_fusion import SwarmTelemetryFusionEngine


def test_swarm_telemetry_and_safety_api_lifecycle(client, database):
    # Seed Swarm in DB
    fc = PersistentHardwareComponent(id="comp-fc-s11", manufacturer="Holybro", model="Pixhawk 4", category="flight_controller", mass_g=68.0)
    frame = PersistentHardwareComponent(id="comp-frame-s11", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="comp-motor-s11", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="comp-esc-s11", manufacturer="Holybro", model="Tekko32", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="comp-prop-s11", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="comp-bat-s11", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    database.add_all([fc, frame, motor, esc, prop, bat])
    database.commit()

    v1 = PersistentVehicle(id="v-s11-01", name="S11 Veh 1", vehicle_type="quadcopter", frame_id=frame.id, motor_id=motor.id, esc_id=esc.id, propeller_id=prop.id, battery_id=bat.id, flight_controller_id=fc.id)
    v2 = PersistentVehicle(id="v-s11-02", name="S11 Veh 2", vehicle_type="quadcopter", frame_id=frame.id, motor_id=motor.id, esc_id=esc.id, propeller_id=prop.id, battery_id=bat.id, flight_controller_id=fc.id)
    database.add_all([v1, v2])
    database.commit()

    swarm = PersistentSwarm(
        id="swm-s11-01",
        name="S11 Test Swarm",
        leader_vehicle_id=v1.id,
        formation_type="LINE",
        formation_spacing_m=10.0,
        min_separation_m=5.0,
    )
    database.add(swarm)
    database.commit()

    # 1. Create Safety Policy via API
    res_pol = client.post(
        f"/api/v1/simulation/swarms/{swarm.id}/safety/policies",
        json={
            "name": "Strict High Altitude Policy",
            "min_separation_m": 6.0,
            "warning_separation_m": 10.0,
            "critical_separation_m": 4.0,
        },
    )
    assert res_pol.status_code == 201
    pol_data = res_pol.json()
    assert pol_data["name"] == "Strict High Altitude Policy"

    # 2. Get Safety Policies
    res_list = client.get(f"/api/v1/simulation/swarms/{swarm.id}/safety/policies")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1

    # 3. Trigger Explicit Safety Evaluation
    res_eval = client.post(f"/api/v1/simulation/swarms/{swarm.id}/safety/eval")
    assert res_eval.status_code == 200

    # 4. Get Auditable Safety Events Log
    res_events = client.get(f"/api/v1/simulation/swarms/{swarm.id}/safety/events")
    assert res_events.status_code == 200


def test_swarm_telemetry_scaling_benchmark_32_vehicles():
    """Benchmark telemetry stream fusion & state aggregation scaling for 4, 8, 16, and 32 vehicles."""
    now = time.time()

    for num_vehicles in [4, 8, 16, 32]:
        fusion = SwarmTelemetryFusionEngine(history_limit_per_vehicle=50)

        # Ingest telemetry for N vehicles
        for i in range(num_vehicles):
            vid = f"v-scale-{i:02d}"
            v_state = VehicleState(
                timestamp_utc="2026-09-11T00:00:00Z",
                sim_time_seconds=1.0,
                vehicle_id=vid,
                position=PositionVector(latitude=0.0001 * i, longitude=-0.0001 * i, altitude_relative=10.0),
            )
            fusion.ingest_vehicle_state("swm-scale", v_state, current_time_s=now)

        t_start = time.perf_counter()
        telemetry_map = fusion.get_active_telemetry_map()
        snapshot = SwarmAggregationEngine.compute_swarm_snapshot("swm-scale", 1, telemetry_map, current_time_s=now)
        t_elapsed_ms = (time.perf_counter() - t_start) * 1000.0

        assert len(snapshot.active_vehicle_ids) == num_vehicles
        assert t_elapsed_ms < 50.0  # Fusion + aggregation must complete within 50ms for up to 32 vehicles
