"""Tests for Stage S8 Sensor Failure Injection Engine."""

from app.simulation.core.failure_injection import SimulationFailureInjector


def test_sensor_failure_injection():
    """Verify injecting GPS and IMU faults and retrieving active fault records."""
    run_id = "run-test-s8-fault"
    SimulationFailureInjector.clear_faults(run_id)

    # 1. Inject GPS failure
    fault1 = SimulationFailureInjector.inject_sensor_failure(run_id, "GPS", "DISCONNECTED")
    assert fault1["fault_type"] == "SENSOR_GPS_DISCONNECTED"
    assert fault1["active"] is True

    # 2. Inject IMU failure
    fault2 = SimulationFailureInjector.inject_sensor_failure(run_id, "IMU", "NOISE_SPIKE")
    assert fault2["fault_type"] == "SENSOR_IMU_NOISE_SPIKE"

    # 3. Retrieve active faults
    active = SimulationFailureInjector.get_active_faults(run_id)
    assert len(active) == 2

    # 4. Clear faults
    SimulationFailureInjector.clear_faults(run_id)
    assert len(SimulationFailureInjector.get_active_faults(run_id)) == 0
