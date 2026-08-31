"""Stage S5 Battery Energy Engine Test Suite."""

import pytest
import app.models
from app.models.hardware_registry import PersistentHardwareComponent
from app.simulation.core.battery_model import BatteryEnergyEngine


def test_battery_energy_calculations():
    """VERIFIED: BatteryEnergyEngine evaluates energy Wh, hover power W, current A, and flight runtime."""
    bat = PersistentHardwareComponent(
        id="b1",
        manufacturer="Tattu",
        model="4S 5000",
        category="battery",
        mass_g=450.0,
        electrical_specs={"cell_count_s": 4, "nominal_voltage_v": 14.8, "capacity_mah": 5000.0},
    )

    energy = BatteryEnergyEngine.evaluate_battery(
        bat, total_mass_kg=1.158, hover_throttle=0.26, num_motors=4
    )

    assert energy["cell_count_s"] == 4
    assert energy["nominal_voltage_v"] == 14.8
    assert energy["capacity_ah"] == 5.0
    assert energy["total_energy_wh"] == 74.0
    assert energy["estimated_hover_power_w"] > 150.0
    assert energy["estimated_hover_current_a"] > 10.0
    assert energy["estimated_runtime_min"] > 15.0
