"""Stage S12 Automated Test Suite for Multi-Vehicle Orchestration, Replay & Determinism."""

import json
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.simulation.core.deterministic_sensor_sim import DeterministicSensorSim, DeterministicSensorConfig
from app.simulation.core.multi_vehicle_orchestrator import MultiVehicleSimulationOrchestrator
from app.simulation.core.scenario_regression_suite import ScenarioRegressionSuite
from app.simulation.core.simulation_clock import ClockMode, SimulationClock
from app.simulation.core.simulation_recorder import SimulationRecorder
from app.simulation.core.swarm_replay_engine import SwarmReplayEngine


def test_simulation_clock_lifecycle():
    """Verify SimulationClock mode transitions, stepping, and deterministic tick math."""
    clock = SimulationClock(dt_seconds=0.1, mode=ClockMode.DETERMINISTIC)
    clock.start(initial_sim_time=0.0)
    assert clock.is_running is True
    assert clock.sim_time_seconds == 0.0

    t1 = clock.tick()
    assert round(t1, 1) == 0.1
    assert clock.tick_count == 1

    clock.step(5)
    assert round(clock.sim_time_seconds, 1) == 0.6
    assert clock.tick_count == 6

    clock.pause()
    assert clock.is_running is False
    assert clock.mode == ClockMode.PAUSED

    clock.seek(5.0)
    assert clock.sim_time_seconds == 5.0
    assert clock.tick_count == 50


def test_deterministic_sensor_sim():
    """Verify seeded deterministic sensor generator produces identical output for identical seeds."""
    sim1 = DeterministicSensorSim(config=DeterministicSensorConfig(seed=12345))
    sim2 = DeterministicSensorSim(config=DeterministicSensorConfig(seed=12345))

    # Mock state
    from app.schemas.simulation_platform import VehicleState, PositionVector, VelocityVector, AttitudeVector
    state = VehicleState(
        timestamp_utc="2026-09-11T00:00:00Z",
        sim_time_seconds=1.0,
        vehicle_id="veh-test",
        position=PositionVector(latitude=37.7749, longitude=-122.4194, altitude_relative=15.0),
        velocity=VelocityVector(vx=1.0, vy=0.0, vz=0.0),
        attitude=AttitudeVector(roll_deg=0.0, pitch_deg=0.0, yaw_deg=45.0),
    )

    gps1 = sim1.generate_gps_sample("veh-test", 1.0, state)
    gps2 = sim2.generate_gps_sample("veh-test", 1.0, state)

    assert gps1 is not None and gps2 is not None
    assert gps1.latitude == gps2.latitude
    assert gps1.longitude == gps2.longitude
    assert gps1.altitude_m == gps2.altitude_m

    imu1 = sim1.generate_imu_sample("veh-test", 1.0, state)
    imu2 = sim2.generate_imu_sample("veh-test", 1.0, state)
    assert imu1 is not None and imu2 is not None
    assert imu1.orientation == imu2.orientation


def test_multi_vehicle_orchestrator_execution():
    """Verify orchestrator multi-vehicle registration, snapshot recording, and safety engine tick."""
    orchestrator = MultiVehicleSimulationOrchestrator(
        scenario_id="test_scen",
        dt_seconds=0.1,
        random_seed=42,
    )
    orchestrator.initialize_swarm(["v1", "v2", "v3", "v4"])
    assert len(orchestrator.vehicles) == 4

    orchestrator.start()
    snap = orchestrator.step(10)

    assert snap is not None
    assert snap.tick_count == 10
    assert round(snap.sim_time_seconds, 1) == 1.0
    assert len(snap.vehicles_state) == 4
    assert snap.swarm_state is not None
    assert snap.telemetry_snapshot is not None
    assert snap.snapshot_hash is not None


def test_phase12_determinism_verification():
    """Phase 12 Core Requirement: Two independent simulation runs with identical seeds MUST produce identical hash."""
    orc1 = MultiVehicleSimulationOrchestrator(scenario_id="det_test", dt_seconds=0.1, random_seed=999)
    orc1.initialize_swarm(["v1", "v2", "v3", "v4"])
    orc1.start()
    for _ in range(30):
        orc1.step(1)
    hash1 = orc1.recorder.get_metadata().recording_hash

    orc2 = MultiVehicleSimulationOrchestrator(scenario_id="det_test", dt_seconds=0.1, random_seed=999)
    orc2.initialize_swarm(["v1", "v2", "v3", "v4"])
    orc2.start()
    for _ in range(30):
        orc2.step(1)
    hash2 = orc2.recorder.get_metadata().recording_hash

    assert hash1 == hash2, "Deterministic simulation failed: recording hashes do not match."


def test_swarm_replay_engine_navigation():
    """Verify replay engine play, pause, step, and seek operations."""
    orc = MultiVehicleSimulationOrchestrator(scenario_id="replay_test", dt_seconds=0.1, random_seed=42)
    orc.initialize_swarm(["v1", "v2"])
    orc.start()
    for _ in range(20):
        orc.step(1)

    replay = SwarmReplayEngine(orc.recorder)
    st = replay.get_replay_state()
    assert st.total_ticks == 20

    s_play = replay.play()
    assert s_play.playback_status == "PLAYING"

    s_pause = replay.pause()
    assert s_pause.playback_status == "PAUSED"

    snap_seek = replay.seek_time(1.0)
    assert snap_seek is not None
    assert round(snap_seek.sim_time_seconds, 1) == 1.0


def test_phase13_scenario_regression_suite_a_to_l():
    """Phase 13: Execute every scenario (A through L) and verify consistent completion."""
    res_a = ScenarioRegressionSuite.run_scenario_a_single_vehicle(ticks=10)
    assert res_a["hash"] is not None

    res_b = ScenarioRegressionSuite.run_scenario_b_4_vehicle_formation(ticks=10)
    assert res_b["hash"] is not None

    res_c = ScenarioRegressionSuite.run_scenario_c_8_vehicle_heterogeneous(ticks=10)
    assert res_c["hash"] is not None

    res_d = ScenarioRegressionSuite.run_scenario_d_16_vehicle_swarm(ticks=10)
    assert res_d["hash"] is not None

    res_e = ScenarioRegressionSuite.run_scenario_e_telemetry_dropout(ticks=10)
    assert res_e["hash"] is not None

    res_f = ScenarioRegressionSuite.run_scenario_f_leader_loss(ticks=25)
    assert res_f["new_leader"] is not None

    res_g = ScenarioRegressionSuite.run_scenario_g_formation_deviation(ticks=20)
    assert res_g["hash"] is not None

    res_h = ScenarioRegressionSuite.run_scenario_h_separation_violation(ticks=20)
    assert res_h["hash"] is not None

    res_i = ScenarioRegressionSuite.run_scenario_i_mission_completion(ticks=10)
    assert res_i["hash"] is not None

    res_j = ScenarioRegressionSuite.run_scenario_j_mission_abort_safety(ticks=20)
    assert res_j["hash"] is not None

    res_k = ScenarioRegressionSuite.run_scenario_k_sensor_dropout(ticks=10)
    assert res_k["hash"] is not None

    res_l = ScenarioRegressionSuite.run_scenario_l_communication_degradation(ticks=10)
    assert res_l["hash"] is not None


def test_32_vehicle_scale_performance():
    """Phase 14 Scaling Benchmark: Verify 32 vehicles orchestrate cleanly without errors."""
    orc = MultiVehicleSimulationOrchestrator(scenario_id="perf_32", dt_seconds=0.1, random_seed=42)
    vids = [f"veh-{i+1:02d}" for i in range(32)]
    orc.initialize_swarm(vids)
    orc.start()
    snap = orc.step(5)
    assert snap is not None
    assert len(snap.vehicles_state) == 32


def test_simulation_orchestration_api_endpoints():
    """Phase 15 API Test: Verify REST endpoints for init, start, pause, step, snapshot, and replay."""
    client = TestClient(app)

    init_res = client.post("/api/v1/simulation/orchestrator/init", json={
        "scenario_id": "api_test",
        "vehicle_count": 4,
        "dt_seconds": 0.1,
        "random_seed": 42
    })
    assert init_res.status_code == 200
    assert init_res.json()["status"] == "INITIALIZED"

    start_res = client.post("/api/v1/simulation/orchestrator/start")
    assert start_res.status_code == 200
    assert start_res.json()["status"] == "RUNNING"

    step_res = client.post("/api/v1/simulation/orchestrator/step", json={"count": 5})
    assert step_res.status_code == 200
    snap_data = step_res.json()
    assert snap_data["tick_count"] == 5

    pause_res = client.post("/api/v1/simulation/orchestrator/pause")
    assert pause_res.status_code == 200

    snap_res = client.get("/api/v1/simulation/orchestrator/snapshot")
    assert snap_res.status_code == 200

    reg_res = client.get("/api/v1/simulation/orchestrator/regression/run/A?ticks=10")
    assert reg_res.status_code == 200
    assert reg_res.json()["scenario"] == "A_SINGLE_VEHICLE"
