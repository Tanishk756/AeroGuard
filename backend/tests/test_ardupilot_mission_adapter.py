"""Stage S7 ArduPilot Mission Adapter Test Suite."""

import pytest
from app.schemas.mission import MissionItemSpec
from app.simulation.core.mission_compiler import MissionCompiler
from app.simulation.core.ardupilot_mission_adapter import ArduPilotMissionAdapter, MAV_CMD_NAV_TAKEOFF, MAV_CMD_NAV_WAYPOINT, MAV_CMD_NAV_LAND


def test_ardupilot_mission_adapter_translation():
    """VERIFIED: ArduPilotMissionAdapter translates CompiledMission items to MAV_CMD commands."""
    items = [
        MissionItemSpec(sequence=1, command_type="TAKEOFF", altitude_m=20.0),
        MissionItemSpec(sequence=2, command_type="WAYPOINT", latitude=37.7749, longitude=-122.4194, altitude_m=25.0, acceptance_radius_m=3.0),
        MissionItemSpec(sequence=3, command_type="LAND", altitude_m=0.0),
    ]

    compiled = MissionCompiler.compile_mission(
        mission_id="msn-ap-01", version=1, vehicle_id="veh-01", scenario_id="scen-01", items=items
    )
    ap_items = ArduPilotMissionAdapter.translate_to_ardupilot(compiled)

    assert len(ap_items) == 3
    assert ap_items[0].command == MAV_CMD_NAV_TAKEOFF
    assert ap_items[1].command == MAV_CMD_NAV_WAYPOINT
    assert ap_items[1].param2 == 3.0
    assert ap_items[2].command == MAV_CMD_NAV_LAND
