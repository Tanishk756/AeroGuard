"""Stage S6 Vehicle Spawn Configuration Test Suite."""

import pytest
from app.schemas.scenario_world import VehicleSpawnConfiguration


def test_vehicle_spawn_configuration_defaults_and_override():
    """VERIFIED: VehicleSpawnConfiguration formats position, orientation, altitude, and heading."""
    spawn = VehicleSpawnConfiguration(
        position=[10.0, -5.0, 1.5],
        orientation=[0.0, 0.0, 45.0],
        altitude_m=1.5,
        heading_deg=45.0,
    )
    assert spawn.position == [10.0, -5.0, 1.5]
    assert spawn.orientation == [0.0, 0.0, 45.0]
    assert spawn.altitude_m == 1.5
    assert spawn.heading_deg == 45.0
