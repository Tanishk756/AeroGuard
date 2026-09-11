"""Tests for Stage S9 Autopilot Hardware Abstraction Layer Base Contracts."""

import pytest
from app.schemas.simulation_platform import SimulationScenarioSpec, AutopilotType
from app.simulation.core.autopilot_abstraction import AutopilotCapability, AutopilotHealthStatus
from app.simulation.adapters.ardupilot import ArduPilotSITLAdapter
from app.simulation.adapters.px4 import PX4AutopilotAdapter


@pytest.mark.asyncio
async def test_ardupilot_adapter_contracts():
    """Verify ArduPilotSITLAdapter capabilities, health check, and mode setting."""
    spec = SimulationScenarioSpec(scenario_id="s1", name="ArduPilot Scenario", autopilot_type=AutopilotType.ARDUPILOT)
    adapter = ArduPilotSITLAdapter(spec)

    caps = adapter.get_capabilities()
    assert AutopilotCapability.WAYPOINT_MISSION in caps
    assert AutopilotCapability.SET_MODE_GUIDED in caps

    health = await adapter.check_health()
    assert health.autopilot_type == AutopilotType.ARDUPILOT
    assert isinstance(health.ready, bool)

    ok_mode = await adapter.set_flight_mode("GUIDED")
    assert ok_mode is True
    assert adapter.current_mode == "GUIDED"

    arm_ok = await adapter.arm()
    assert arm_ok is True
    assert adapter.is_armed is True


@pytest.mark.asyncio
async def test_px4_adapter_contracts():
    """Verify PX4AutopilotAdapter capabilities, health check, and mode setting."""
    spec = SimulationScenarioSpec(scenario_id="s2", name="PX4 Scenario", autopilot_type=AutopilotType.PX4)
    adapter = PX4AutopilotAdapter(spec)

    caps = adapter.get_capabilities()
    assert AutopilotCapability.WAYPOINT_MISSION in caps
    assert AutopilotCapability.SET_MODE_OFFBOARD in caps

    health = await adapter.check_health()
    assert health.autopilot_type == AutopilotType.PX4

    ok_mode = await adapter.set_flight_mode("AUTO.MISSION")
    assert ok_mode is True
    assert adapter.current_mode == "AUTO.MISSION"

    arm_ok = await adapter.arm()
    assert arm_ok is True
    assert adapter.is_armed is True
