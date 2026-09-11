"""Stage S10 Formation Geometry & Coordinate Conversion Engine.

Provides deterministic calculation of vehicle formation slots and coordinate transformations
between Body, Local ENU (East-North-Up), NED (North-East-Down), and Geodetic (WGS84) frames.
"""

import math
from typing import Dict, List, Tuple
from app.schemas.swarm import FormationConfiguration, FormationSlot, FormationType, SwarmRole

# Earth radius constant (WGS84 mean radius in meters)
EARTH_RADIUS_M = 6378137.0


class FormationGeometry:
    """Deterministic geometry engine for multi-vehicle swarm formations."""

    @staticmethod
    def generate_slots(
        formation_type: FormationType,
        num_vehicles: int,
        spacing_m: float = 10.0,
        altitude_offset_m: float = 0.0,
    ) -> Dict[int, FormationSlot]:
        """Generate deterministic body-frame relative slots for N vehicles.

        Slot 0 is always assigned to the Leader at relative offset (0, 0, 0).
        Follower slots 1..N-1 are positioned relative to the Leader in body frame:
          +X_b = Forward (along direction of heading)
          +Y_b = Right (perpendicular to heading)
          +Z_b = Up (vertical height)
        """
        slots: Dict[int, FormationSlot] = {}
        if num_vehicles <= 0:
            return slots

        # Leader slot at index 0
        slots[0] = FormationSlot(
            slot_index=0,
            role=SwarmRole.LEADER,
            relative_offset_enu=(0.0, 0.0, 0.0),
            heading_offset_deg=0.0,
        )

        if num_vehicles == 1:
            return slots

        num_followers = num_vehicles - 1

        for k in range(1, num_vehicles):
            if formation_type == FormationType.LINE:
                # Line abreast (perpendicular to flight direction):
                # k=1: right +S, k=2: left -S, k=3: right +2S, k=4: left -2S ...
                side = 1.0 if (k % 2 != 0) else -1.0
                multiplier = math.ceil(k / 2.0)
                x_b = 0.0
                y_b = side * multiplier * spacing_m
                z_b = altitude_offset_m * (k % 3 - 1)

            elif formation_type == FormationType.COLUMN:
                # Single file behind leader along -X_b axis
                x_b = -float(k) * spacing_m
                y_b = 0.0
                z_b = 0.0

            elif formation_type == FormationType.V_FORMATION:
                # V-shape apex at leader
                # k=1: left wing (-1S, -1S), k=2: right wing (-1S, +1S), k=3: left (-2S, -2S), etc.
                wing_index = math.ceil(k / 2.0)
                side = -1.0 if (k % 2 != 0) else 1.0
                x_b = -float(wing_index) * spacing_m
                y_b = side * float(wing_index) * spacing_m
                z_b = 0.0

            elif formation_type == FormationType.GRID:
                # 2D rectangular grid behind leader
                cols = max(2, int(math.ceil(math.sqrt(num_vehicles))))
                row = (k) // cols
                col = (k) % cols - (cols // 2)
                x_b = -float(row) * spacing_m
                y_b = float(col) * spacing_m
                z_b = 0.0

            elif formation_type == FormationType.CIRCLE:
                # Circular ring around center
                radius = max(spacing_m, (num_followers * spacing_m) / (2.0 * math.pi))
                angle_rad = 2.0 * math.pi * float(k - 1) / float(num_followers)
                x_b = radius * math.cos(angle_rad)
                y_b = radius * math.sin(angle_rad)
                z_b = 0.0

            else:
                x_b = 0.0
                y_b = float(k) * spacing_m
                z_b = 0.0

            slots[k] = FormationSlot(
                slot_index=k,
                role=SwarmRole.FOLLOWER,
                relative_offset_enu=(x_b, y_b, z_b),
                heading_offset_deg=0.0,
            )

        return slots

    @staticmethod
    def body_offset_to_enu(
        body_offset: Tuple[float, float, float],
        heading_deg: float,
    ) -> Tuple[float, float, float]:
        """Transform body frame offset (x_forward, y_right, z_up) to Local ENU (East, North, Up).

        Heading convention: Azimuth in degrees (0 = North, 90 = East, 180 = South, 270 = West).
        """
        x_b, y_b, z_b = body_offset
        heading_rad = math.radians(heading_deg)

        sin_h = math.sin(heading_rad)
        cos_h = math.cos(heading_rad)

        # Forward (+X_b) unit vector in ENU = (sin_h, cos_h, 0)
        # Right (+Y_b) unit vector in ENU = (cos_h, -sin_h, 0)
        e = x_b * sin_h + y_b * cos_h
        n = x_b * cos_h - y_b * sin_h
        u = z_b

        return (e, n, u)

    @staticmethod
    def enu_to_body_offset(
        enu_offset: Tuple[float, float, float],
        heading_deg: float,
    ) -> Tuple[float, float, float]:
        """Transform Local ENU offset (East, North, Up) back to body frame (x_forward, y_right, z_up)."""
        e, n, u = enu_offset
        heading_rad = math.radians(heading_deg)

        sin_h = math.sin(heading_rad)
        cos_h = math.cos(heading_rad)

        x_b = e * sin_h + n * cos_h
        y_b = e * cos_h - n * sin_h
        z_b = u

        return (x_b, y_b, z_b)

    @staticmethod
    def enu_to_ned(enu: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Convert East-North-Up to North-East-Down."""
        e, n, u = enu
        return (n, e, -u)

    @staticmethod
    def ned_to_enu(ned: Tuple[float, float, float]) -> Tuple[float, float, float]:
        """Convert North-East-Down to East-North-Up."""
        n, e, d = ned
        return (e, n, -d)

    @staticmethod
    def enu_to_geodetic(
        ref_lat: float,
        ref_lon: float,
        ref_alt: float,
        enu_x: float,
        enu_y: float,
        enu_z: float,
    ) -> Tuple[float, float, float]:
        """Convert Local ENU offset (meters) relative to ref (lat, lon, alt) to WGS84 Geodetic coordinates."""
        d_lat = (enu_y / EARTH_RADIUS_M) * (180.0 / math.pi)
        d_lon = (enu_x / (EARTH_RADIUS_M * math.cos(math.radians(ref_lat)))) * (180.0 / math.pi)

        target_lat = ref_lat + d_lat
        target_lon = ref_lon + d_lon
        target_alt = ref_alt + enu_z

        return (target_lat, target_lon, target_alt)

    @staticmethod
    def geodetic_to_enu(
        ref_lat: float,
        ref_lon: float,
        ref_alt: float,
        lat: float,
        lon: float,
        alt: float,
    ) -> Tuple[float, float, float]:
        """Convert WGS84 Geodetic coordinate (lat, lon, alt) to Local ENU offset (meters) relative to ref."""
        d_lat = lat - ref_lat
        d_lon = lon - ref_lon

        enu_y = (d_lat * math.pi / 180.0) * EARTH_RADIUS_M
        enu_x = (d_lon * math.pi / 180.0) * (EARTH_RADIUS_M * math.cos(math.radians(ref_lat)))
        enu_z = alt - ref_alt

        return (enu_x, enu_y, enu_z)

    @classmethod
    def calculate_desired_slot_position(
        cls,
        leader_position_enu: Tuple[float, float, float],
        leader_heading_deg: float,
        slot: FormationSlot,
    ) -> Tuple[float, float, float]:
        """Calculate absolute ENU target position for a formation slot given leader ENU position and heading."""
        enu_offset = cls.body_offset_to_enu(slot.relative_offset_enu, leader_heading_deg)
        return (
            leader_position_enu[0] + enu_offset[0],
            leader_position_enu[1] + enu_offset[1],
            leader_position_enu[2] + enu_offset[2],
        )
