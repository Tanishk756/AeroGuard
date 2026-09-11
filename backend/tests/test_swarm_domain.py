"""Stage S10 Swarm Domain Model Unit Tests.

Tests swarm creation, unique vehicle IDs, role assignments, member management, and heterogeneous autopilot configurations.
"""

import pytest
from app.schemas.swarm import (
    FormationConfiguration,
    FormationType,
    SwarmConfiguration,
    SwarmConstraints,
    SwarmMemberConfig,
    SwarmRole,
)
from app.simulation.core.swarm_engine import SwarmEngine


def test_swarm_domain_creation_and_membership():
    config = SwarmConfiguration(
        swarm_id="swm-test-01",
        name="Alpha Recon Swarm",
        constraints=SwarmConstraints(min_separation_m=5.0),
    )
    engine = SwarmEngine(config)

    # Register Leader (ArduPilot)
    m1 = engine.register_member("veh-01", role=SwarmRole.LEADER, autopilot_type="ARDUPILOT")
    assert m1.vehicle_id == "veh-01"
    assert m1.role == SwarmRole.LEADER
    assert engine.config.leader_vehicle_id == "veh-01"

    # Register Followers (PX4 & ArduPilot) - Heterogeneous Swarm
    m2 = engine.register_member("veh-02", role=SwarmRole.FOLLOWER, autopilot_type="PX4")
    m3 = engine.register_member("veh-03", role=SwarmRole.FOLLOWER, autopilot_type="ARDUPILOT")

    assert len(engine.config.members) == 3
    assert engine.config.members[1].autopilot_type == "PX4"
    assert engine.config.members[2].autopilot_type == "ARDUPILOT"


def test_swarm_leader_reassignment():
    config = SwarmConfiguration(
        swarm_id="swm-test-02",
        name="Beta Swarm",
    )
    engine = SwarmEngine(config)
    engine.register_member("v-leader", role=SwarmRole.LEADER)
    engine.register_member("v-follower", role=SwarmRole.FOLLOWER)

    assert engine.config.leader_vehicle_id == "v-leader"

    # Transfer leadership
    success = engine.set_leader("v-follower")
    assert success is True
    assert engine.config.leader_vehicle_id == "v-follower"
    assert engine.config.members[0].vehicle_id == "v-follower"
    assert engine.config.members[0].role == SwarmRole.LEADER
    assert engine.config.members[1].role == SwarmRole.FOLLOWER


def test_swarm_member_removal():
    config = SwarmConfiguration(swarm_id="swm-test-03", name="Gamma Swarm")
    engine = SwarmEngine(config)
    engine.register_member("v1", role=SwarmRole.LEADER)
    engine.register_member("v2", role=SwarmRole.FOLLOWER)
    engine.register_member("v3", role=SwarmRole.FOLLOWER)

    assert len(engine.config.members) == 3

    # Remove follower
    removed = engine.remove_member("v2")
    assert removed is True
    assert len(engine.config.members) == 2
    assert [m.vehicle_id for m in engine.config.members] == ["v1", "v3"]
