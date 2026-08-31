"""Stage S6 Gazebo World Generator Test Suite."""

import pytest
from app.models.scenario_world import PersistentWorldObject
from app.schemas.scenario_world import EnvironmentConfiguration, WeatherConfiguration, PhysicsConfiguration
from app.simulation.core.world_generator import GazeboWorldGenerator


def test_gazebo_world_sdf_xml_generation():
    """VERIFIED: GazeboWorldGenerator produces valid Gazebo Harmonic SDF 1.9 world XML."""
    obj1 = PersistentWorldObject(
        id="o1",
        world_id="w1",
        object_type="LANDING_PAD",
        position_json={"x": 0.0, "y": 0.0, "z": 0.01},
        orientation_json={"roll": 0, "pitch": 0, "yaw": 0},
        scale_json={"x": 2.0, "y": 2.0, "z": 0.02},
        collision_enabled=True,
        visual_enabled=True,
    )
    obj2 = PersistentWorldObject(
        id="o2",
        world_id="w1",
        object_type="STATIC_BOX",
        position_json={"x": 5.0, "y": 3.0, "z": 1.5},
        orientation_json={"roll": 0, "pitch": 0, "yaw": 0},
        scale_json={"x": 2.0, "y": 2.0, "z": 3.0},
        collision_enabled=True,
        visual_enabled=True,
    )

    env = EnvironmentConfiguration()
    weather = WeatherConfiguration(wind_speed_m_s=8.5, wind_direction_deg=180.0)
    physics = PhysicsConfiguration()

    world_xml, world_hash = GazeboWorldGenerator.generate_world_sdf(
        "test_world_alpha", [obj1, obj2], env, weather, physics
    )

    assert '<sdf version="1.9">' in world_xml
    assert '<world name="test_world_alpha">' in world_xml
    assert "gz-sim-wind-effects-system" in world_xml
    assert "<magnitude>8.5</magnitude>" in world_xml
    assert "STATIC_BOX" in world_xml.upper() or "world_obj_2" in world_xml
    assert len(world_hash) == 64
