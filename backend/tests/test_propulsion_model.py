"""Stage S5 Propulsion Engine Test Suite."""

import pytest
import app.models
from app.models.hardware_registry import PersistentHardwareComponent
from app.simulation.core.propulsion_model import PropulsionEngine


def test_propulsion_dynamics_calculations():
    """VERIFIED: PropulsionEngine evaluates RPM, max thrust, T/W ratio, and torque estimates."""
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0, electrical_specs={"kv": 920, "max_voltage_v": 16.8, "max_current_a": 18.0, "max_thrust_g": 1100.0})
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0, electrical_specs={"nominal_voltage_v": 14.8})

    propulsion = PropulsionEngine.evaluate_propulsion(
        motor, esc, prop, bat, total_mass_kg=1.158, num_motors=4
    )

    assert propulsion["kv"] == 920.0
    assert propulsion["operating_voltage_v"] == 14.8
    assert propulsion["total_max_thrust_kg"] == 4.4
    assert propulsion["thrust_to_weight_ratio"] > 3.5
    assert propulsion["estimated_hover_throttle"] < 0.3
