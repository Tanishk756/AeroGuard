"""Tests for PX4 SITL Autopilot Adapter."""

import pytest
from app.schemas.simulation_platform import SimulationScenarioSpec, AutopilotType, SimulationRunStatus
from app.simulation.adapters.px4 import PX4AutopilotAdapter


@pytest.mark.asyncio
async def test_px4_adapter_lifecycle():
    """Verify PX4 SITL adapter prepare, start, pause, resume, and stop lifecycle."""
    spec = SimulationScenarioSpec(scenario_id="s-px4-1", name="PX4 Lifecycle Test", autopilot_type=AutopilotType.PX4)
    adapter = PX4AutopilotAdapter(spec)

    prep = await adapter.prepare()
    assert prep is True

    start = await adapter.start()
    assert start is True
    assert adapter.status == SimulationRunStatus.RUNNING

    pause = await adapter.pause()
    assert pause is True
    assert adapter.status == SimulationRunStatus.PAUSED

    resume = await adapter.resume()
    assert resume is True
    assert adapter.status == SimulationRunStatus.RUNNING

    stop = await adapter.stop()
    assert stop is True
    assert adapter.status == SimulationRunStatus.STOPPED


@pytest.mark.asyncio
async def test_px4_mission_upload_and_commands():
    """Verify PX4 mission upload and automated takeoff/landing command execution."""
    spec = SimulationScenarioSpec(scenario_id="s-px4-2", name="PX4 Mission Test", autopilot_type=AutopilotType.PX4)
    adapter = PX4AutopilotAdapter(spec)

    upload = await adapter.upload_mission({
        "items": [
            {"sequence": 1, "command_type": "TAKEOFF", "latitude": 37.7749, "longitude": -122.4194, "altitude_m": 15.0},
            {"sequence": 2, "command_type": "WAYPOINT", "latitude": 37.7755, "longitude": -122.4190, "altitude_m": 20.0},
        ]
    })
    assert upload["status"] == "ACCEPTED"
    assert upload["items_uploaded"] == 2

    takeoff = await adapter.takeoff(15.0)
    assert takeoff is True
    assert adapter.current_mode == "AUTO.TAKEOFF"

    land = await adapter.land()
    assert land is True
    assert adapter.current_mode == "AUTO.LAND"
