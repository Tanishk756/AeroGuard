"""Stage S10 Formation Geometry Unit Tests.

Tests deterministic formation slot generation for 5 formations, coordinate transformations across frames,
and geodetic conversions.
"""

import math
import pytest
from app.schemas.swarm import FormationType, SwarmRole
from app.simulation.core.formation_geometry import FormationGeometry


def test_slot_generation_line():
    slots = FormationGeometry.generate_slots(FormationType.LINE, num_vehicles=4, spacing_m=10.0)
    assert len(slots) == 4
    assert slots[0].role == SwarmRole.LEADER
    assert slots[0].relative_offset_enu == (0.0, 0.0, 0.0)

    # Slot 1: right (+10m along Y_b)
    assert slots[1].relative_offset_enu[1] == 10.0
    # Slot 2: left (-10m along Y_b)
    assert slots[2].relative_offset_enu[1] == -10.0
    # Slot 3: right (+20m along Y_b)
    assert slots[3].relative_offset_enu[1] == 20.0


def test_slot_generation_column():
    slots = FormationGeometry.generate_slots(FormationType.COLUMN, num_vehicles=3, spacing_m=15.0)
    assert len(slots) == 3
    # Single file behind leader (-X_b)
    assert slots[1].relative_offset_enu[0] == -15.0
    assert slots[2].relative_offset_enu[0] == -30.0


def test_slot_generation_v_formation():
    slots = FormationGeometry.generate_slots(FormationType.V_FORMATION, num_vehicles=5, spacing_m=10.0)
    assert len(slots) == 5
    # Apex at slot 0 (0,0,0)
    # Wing 1: slot 1 (-10, -10, 0), slot 2 (-10, +10, 0)
    assert slots[1].relative_offset_enu == (-10.0, -10.0, 0.0)
    assert slots[2].relative_offset_enu == (-10.0, 10.0, 0.0)


def test_slot_generation_grid():
    slots = FormationGeometry.generate_slots(FormationType.GRID, num_vehicles=4, spacing_m=10.0)
    assert len(slots) == 4
    assert slots[0].relative_offset_enu == (0.0, 0.0, 0.0)


def test_slot_generation_circle():
    slots = FormationGeometry.generate_slots(FormationType.CIRCLE, num_vehicles=5, spacing_m=10.0)
    assert len(slots) == 5
    # Circle slots around center
    radius = slots[1].relative_offset_enu[0] ** 2 + slots[1].relative_offset_enu[1] ** 2
    assert radius > 0.0


def test_body_to_enu_rotations():
    # Forward 10m (+X_b=10) with Heading = 0 deg (North) -> ENU (0, 10, 0)
    e, n, u = FormationGeometry.body_offset_to_enu((10.0, 0.0, 0.0), heading_deg=0.0)
    assert abs(e - 0.0) < 1e-5
    assert abs(n - 10.0) < 1e-5

    # Forward 10m (+X_b=10) with Heading = 90 deg (East) -> ENU (10, 0, 0)
    e, n, u = FormationGeometry.body_offset_to_enu((10.0, 0.0, 0.0), heading_deg=90.0)
    assert abs(e - 10.0) < 1e-5
    assert abs(n - 0.0) < 1e-5


def test_enu_ned_conversions():
    enu = (10.0, 20.0, 30.0)  # East=10, North=20, Up=30
    ned = FormationGeometry.enu_to_ned(enu)
    assert ned == (20.0, 10.0, -30.0)  # North=20, East=10, Down=-30

    back_enu = FormationGeometry.ned_to_enu(ned)
    assert back_enu == enu


def test_geodetic_enu_transformations():
    ref_lat, ref_lon, ref_alt = 37.7749, -122.4194, 100.0
    enu_x, enu_y, enu_z = 50.0, -30.0, 15.0

    lat, lon, alt = FormationGeometry.enu_to_geodetic(ref_lat, ref_lon, ref_alt, enu_x, enu_y, enu_z)
    back_x, back_y, back_z = FormationGeometry.geodetic_to_enu(ref_lat, ref_lon, ref_alt, lat, lon, alt)

    assert abs(back_x - enu_x) < 1e-4
    assert abs(back_y - enu_y) < 1e-4
    assert abs(back_z - enu_z) < 1e-4
