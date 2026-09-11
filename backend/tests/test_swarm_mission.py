"""Stage S10 Multi-Vehicle Swarm Mission Translator Unit Tests.

Tests translation of swarm directives into vehicle-specific CompiledMissions with formation slot offsets.
"""

import pytest
from app.schemas.swarm import FormationConfiguration, FormationType, SwarmConfiguration, SwarmConstraints, SwarmMemberConfig, SwarmRole
from app.simulation.core.swarm_mission_translator import SwarmMissionDirective, SwarmMissionTranslator


def test_swarm_mission_translation_takeoff_waypoint_land():
    swarm_config = SwarmConfiguration(
        swarm_id="swm-mission-01",
        name="Mission Test Swarm",
        formation=FormationConfiguration(formation_type=FormationType.LINE, spacing_m=10.0),
        members=[
            SwarmMemberConfig(vehicle_id="v1", role=SwarmRole.LEADER, slot_index=0),
            SwarmMemberConfig(vehicle_id="v2", role=SwarmRole.FOLLOWER, slot_index=1),
        ],
    )

    directives = [
        SwarmMissionDirective(command_type="TAKEOFF_ALL", altitude_m=10.0),
        SwarmMissionDirective(command_type="FORMATION_WAYPOINT", latitude=37.7750, longitude=-122.4190, altitude_m=20.0, heading_deg=0.0),
        SwarmMissionDirective(command_type="LAND_ALL"),
    ]

    compiled_missions = SwarmMissionTranslator.compile_swarm_mission(
        swarm_config=swarm_config,
        scenario_id="scen-01",
        directives=directives,
        ref_lat=37.7749,
        ref_lon=-122.4194,
    )

    assert "v1" in compiled_missions
    assert "v2" in compiled_missions

    v1_msn = compiled_missions["v1"]
    v2_msn = compiled_missions["v2"]

    assert len(v1_msn.items) == 3
    assert len(v2_msn.items) == 3

    # Check TAKEOFF command
    assert v1_msn.items[0].command_type == "TAKEOFF"
    assert v2_msn.items[0].command_type == "TAKEOFF"

    # Check WAYPOINT command offset
    # In Line formation with heading=0 deg (North), slot 1 has +10m East offset (+Y_b).
    # Therefore v2 longitude should be shifted East relative to v1.
    assert v2_msn.items[1].longitude > v1_msn.items[1].longitude
