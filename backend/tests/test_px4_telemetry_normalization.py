"""Tests for PX4 Telemetry Normalization into VehicleState."""

import pytest
from app.schemas.simulation_platform import SimulationScenarioSpec, VehicleModelConfig, AutopilotType
from app.simulation.adapters.px4 import PX4AutopilotAdapter


@pytest.mark.asyncio
async def test_px4_telemetry_normalization():
    """Verify PX4 adapter returns normalized VehicleState vectors."""
    spec = SimulationScenarioSpec(
        scenario_id="s-px4-telem",
        name="PX4 Telemetry Test",
        autopilot_type=AutopilotType.PX4,
        vehicle_config=VehicleModelConfig(vehicle_id="quad-x-px4", autopilot=AutopilotType.PX4)
    )
    adapter = PX4AutopilotAdapter(spec)
    await adapter.prepare()
    await adapter.start()

    state = await adapter.get_telemetry()
    assert state.vehicle_id == "quad-x-px4"
    assert state.flight_mode == "POSCTL"
    assert "autopilot_px4" in state.sensor_health
    assert state.sensor_health["autopilot_px4"] is True
