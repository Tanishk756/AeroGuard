"""Unit tests for 2D/3D geofence evaluation, bounding boxes, polygons, and altitude containment."""

import pytest

from app.geofencing.engine import (
    _point_in_bbox,
    _point_in_polygon,
    evaluate_geofence,
)
from app.models.geofence import Geofence


def test_point_in_bbox_containment():
    bbox = {"min_lat": 37.0, "max_lat": 38.0, "min_lon": -123.0, "max_lon": -122.0}
    # Inside
    assert _point_in_bbox(37.5, -122.5, bbox) is True
    # Boundary points
    assert _point_in_bbox(37.0, -122.5, bbox) is True
    assert _point_in_bbox(38.0, -122.0, bbox) is True
    # Outside
    assert _point_in_bbox(36.9, -122.5, bbox) is False
    assert _point_in_bbox(37.5, -121.9, bbox) is False


def test_point_in_polygon_ray_casting():
    # Triangle: (0,0), (0,10), (10,0) in (lon, lat)
    coords = [[0.0, 0.0], [0.0, 10.0], [10.0, 0.0], [0.0, 0.0]]
    # Point inside (lat=2, lon=2)
    assert _point_in_polygon(2.0, 2.0, coords) is True
    # Point outside (lat=8, lon=8)
    assert _point_in_polygon(8.0, 8.0, coords) is False
    # Point outside completely
    assert _point_in_polygon(-1.0, 2.0, coords) is False


def test_geofence_altitude_containment_and_indeterminate():
    geo_3d = Geofence(
        id="geo-3d-1",
        name="No Fly Zone 3D",
        enabled=True,
        geometry={"type": "bbox", "min_lat": 37.0, "max_lat": 38.0, "min_lon": -123.0, "max_lon": -122.0},
        min_altitude=50.0,
        max_altitude=200.0,
        metadata_json={},
    )

    # 1. Point inside horizontal and altitude bounds (alt=100m) -> inside=True
    res_inside = evaluate_geofence(37.5, -122.5, 100.0, geo_3d)
    assert res_inside.inside is True
    assert res_inside.horizontal_inside is True
    assert res_inside.vertical_inside is True
    assert res_inside.altitude_indeterminate is False

    # 2. Point inside horizontal but below min_altitude (alt=30m) -> inside=False
    res_below = evaluate_geofence(37.5, -122.5, 30.0, geo_3d)
    assert res_below.inside is False
    assert res_below.horizontal_inside is True
    assert res_below.vertical_inside is False

    # 3. Point inside horizontal but missing altitude -> altitude_indeterminate=True
    res_indet = evaluate_geofence(37.5, -122.5, None, geo_3d)
    assert res_indet.altitude_indeterminate is True
    assert res_indet.horizontal_inside is True


def test_geofence_disabled_and_malformed_geometry():
    geo_disabled = Geofence(
        id="geo-dis",
        name="Disabled Zone",
        enabled=False,
        geometry={"type": "bbox", "min_lat": 37.0, "max_lat": 38.0, "min_lon": -123.0, "max_lon": -122.0},
        metadata_json={},
    )
    res = evaluate_geofence(37.5, -122.5, 100.0, geo_disabled)
    assert res.inside is False
    assert res.reason == "GEOFENCE_DISABLED"

    geo_malformed = Geofence(
        id="geo-mal",
        name="Malformed Zone",
        enabled=True,
        geometry="not-a-dict",  # Malformed
        metadata_json={},
    )
    res_mal = evaluate_geofence(37.5, -122.5, 100.0, geo_malformed)
    assert res_mal.inside is False
    assert res_mal.reason == "MALFORMED_GEOMETRY"


def test_geofence_boundary_distance_calculation():
    geo = Geofence(
        id="geo-dist-1",
        name="Distance Test Zone",
        enabled=True,
        geometry={"type": "bbox", "min_lat": 37.0, "max_lat": 38.0, "min_lon": -123.0, "max_lon": -122.0},
        metadata_json={},
    )

    # Point ~11.1km north of 38.0 lat (at lat 38.1)
    res_outside = evaluate_geofence(38.1, -122.5, 100.0, geo)
    assert res_outside.inside is False
    assert 10_000 < res_outside.distance_to_boundary_meters < 12_000

    # Point strictly inside
    res_inside = evaluate_geofence(37.5, -122.5, 100.0, geo)
    assert res_inside.inside is True
    assert res_inside.distance_to_boundary_meters > 0
