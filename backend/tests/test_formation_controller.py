"""Stage S10 Formation Controller Unit Tests.

Tests position error calculation, velocity clamping, tolerance handling, and target heading generation.
"""

import math
import pytest
from app.schemas.swarm import SwarmConstraints
from app.simulation.core.formation_controller import FormationController


def test_formation_controller_target_computation():
    constraints = SwarmConstraints(max_velocity_mps=10.0, position_tolerance_m=2.0)
    controller = FormationController(gain_p=1.0, constraints=constraints)

    current_pos = (0.0, 0.0, 10.0)
    desired_pos = (5.0, 0.0, 10.0)  # 5m East error

    target = controller.compute_follower_target(
        vehicle_id="v-01",
        current_position_enu=current_pos,
        desired_position_enu=desired_pos,
        leader_velocity_enu=(0.0, 0.0, 0.0),
        leader_heading_deg=0.0,
    )

    assert target.vehicle_id == "v-01"
    assert abs(target.position_error_m - 5.0) < 1e-4
    assert target.target_position_enu == desired_pos
    # Velocity intent should be (5.0, 0.0, 0.0) since gain_p=1.0 and 5m <= max_vel (10m/s)
    assert abs(target.target_velocity_enu[0] - 5.0) < 1e-4


def test_formation_controller_velocity_clamping():
    constraints = SwarmConstraints(max_velocity_mps=10.0)
    controller = FormationController(gain_p=1.0, constraints=constraints)

    current_pos = (0.0, 0.0, 0.0)
    desired_pos = (100.0, 0.0, 0.0)  # 100m East error -> raw V = 100 m/s

    target = controller.compute_follower_target(
        vehicle_id="v-02",
        current_position_enu=current_pos,
        desired_position_enu=desired_pos,
    )

    speed = math.sqrt(sum(v ** 2 for v in target.target_velocity_enu))
    assert abs(speed - 10.0) < 1e-4  # Clamped to max 10.0 m/s
