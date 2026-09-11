"""Stage S10 Deterministic Formation Controller Engine.

Implements position and velocity feedback control for multi-vehicle swarm formation keeping.
Computes deterministic target positions and velocities for follower vehicles given leader state and slot definitions.
"""

import math
from typing import Optional, Tuple
from app.schemas.swarm import SwarmConstraints, VehicleDesiredState


class FormationController:
    """Deterministic formation controller."""

    def __init__(self, gain_p: float = 1.0, constraints: Optional[SwarmConstraints] = None):
        self.gain_p = gain_p
        self.constraints = constraints or SwarmConstraints()

    def compute_follower_target(
        self,
        vehicle_id: str,
        current_position_enu: Tuple[float, float, float],
        desired_position_enu: Tuple[float, float, float],
        leader_velocity_enu: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        leader_heading_deg: float = 0.0,
    ) -> VehicleDesiredState:
        """Compute target position and velocity for a follower vehicle.

        Position Error: e = P_desired - P_current
        Control Intent: V_cmd = K_p * e + V_leader (clamped to max_velocity_mps)
        """
        ex = desired_position_enu[0] - current_position_enu[0]
        ey = desired_position_enu[1] - current_position_enu[1]
        ez = desired_position_enu[2] - current_position_enu[2]

        position_error_m = math.sqrt(ex * ex + ey * ey + ez * ez)

        # Proportional velocity intent
        vx_cmd = self.gain_p * ex + leader_velocity_enu[0]
        vy_cmd = self.gain_p * ey + leader_velocity_enu[1]
        vz_cmd = self.gain_p * ez + leader_velocity_enu[2]

        speed = math.sqrt(vx_cmd * vx_cmd + vy_cmd * vy_cmd + vz_cmd * vz_cmd)
        max_vel = self.constraints.max_velocity_mps

        if speed > max_vel and speed > 1e-6:
            scale = max_vel / speed
            vx_cmd *= scale
            vy_cmd *= scale
            vz_cmd *= scale

        # Target heading defaults to leader heading or vector direction if moving significantly
        target_heading = leader_heading_deg
        if math.sqrt(vx_cmd * vx_cmd + vy_cmd * vy_cmd) > 0.5:
            # Azimuth in degrees: 0 = North (+Y), 90 = East (+X)
            heading_rad = math.atan2(vx_cmd, vy_cmd)
            target_heading = math.degrees(heading_rad) % 360.0

        return VehicleDesiredState(
            vehicle_id=vehicle_id,
            target_position_enu=desired_position_enu,
            target_velocity_enu=(vx_cmd, vy_cmd, vz_cmd),
            target_heading_deg=target_heading,
            position_error_m=position_error_m,
        )
