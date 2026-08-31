"""Stage S7 Mission Compiler Test Suite."""

import pytest
from app.schemas.mission import MissionItemSpec
from app.simulation.core.mission_compiler import MissionCompiler


def test_mission_compiler_sha256_checksum():
    """VERIFIED: MissionCompiler produces deterministic CompiledMission with cryptographic SHA256 hash."""
    items = [
        MissionItemSpec(sequence=1, command_type="TAKEOFF", altitude_m=20.0),
        MissionItemSpec(sequence=2, command_type="WAYPOINT", latitude=37.7749, longitude=-122.4194, altitude_m=25.0),
    ]

    compiled1 = MissionCompiler.compile_mission(
        mission_id="msn-comp-01", version=1, vehicle_id="veh-01", scenario_id="scen-01", items=items
    )
    compiled2 = MissionCompiler.compile_mission(
        mission_id="msn-comp-01", version=1, vehicle_id="veh-01", scenario_id="scen-01", items=items
    )

    assert compiled1.compiled_mission_hash == compiled2.compiled_mission_hash
    assert len(compiled1.compiled_mission_hash) == 64
    assert len(compiled1.items) == 2
