"""Stage S6 World Model Test Suite."""

import pytest
import app.models
from app.models.scenario_world import PersistentSimulationWorld, PersistentWorldObject


def test_simulation_world_and_objects_lifecycle(database):
    """VERIFIED: PersistentSimulationWorld and PersistentWorldObject cascade creation."""
    world = PersistentSimulationWorld(
        id="world-test-01",
        project_id="proj-default-01",
        name="Flat Ground with Obstacles",
        world_type="FLAT_GROUND",
    )
    database.add(world)
    database.commit()

    obj1 = PersistentWorldObject(
        id="wobj-01",
        world_id=world.id,
        object_type="LANDING_PAD",
        position_json={"x": 0.0, "y": 0.0, "z": 0.01},
        orientation_json={"roll": 0, "pitch": 0, "yaw": 0},
        scale_json={"x": 2.0, "y": 2.0, "z": 0.02},
        collision_enabled=True,
        visual_enabled=True,
    )
    obj2 = PersistentWorldObject(
        id="wobj-02",
        world_id=world.id,
        object_type="STATIC_BOX",
        position_json={"x": 5.0, "y": 3.0, "z": 1.5},
        orientation_json={"roll": 0, "pitch": 0, "yaw": 0},
        scale_json={"x": 2.0, "y": 2.0, "z": 3.0},
        collision_enabled=True,
        visual_enabled=True,
    )
    database.add_all([obj1, obj2])
    database.commit()
    database.refresh(world)

    assert len(world.objects) == 2
    assert world.objects[0].object_type == "LANDING_PAD"
    assert world.objects[1].position_json["x"] == 5.0
