"""Stage S5 Motor Failure Injection Test Suite."""

import pytest
from app.simulation.core.failure_injection import SimulationFailureInjector


def test_motor_failure_injection_lifecycle():
    """VERIFIED: SimulationFailureInjector records active motor fault events."""
    run_id = "run-fail-test-01"
    fault = SimulationFailureInjector.inject_motor_failure(run_id, motor_index=1, severity=1.0)

    assert fault["run_id"] == run_id
    assert fault["motor_index"] == 1
    assert fault["fault_type"] == "MOTOR_FAILURE"
    assert fault["severity"] == 1.0

    active_faults = SimulationFailureInjector.get_active_faults(run_id)
    assert len(active_faults) == 1
    assert active_faults[0]["target"] == "motor_1"

    SimulationFailureInjector.clear_faults(run_id)
    assert len(SimulationFailureInjector.get_active_faults(run_id)) == 0
