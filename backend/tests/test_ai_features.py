"""Unit tests for AeroGuard AI kinematic feature extraction."""

from datetime import UTC, datetime, timedelta
import math
import pytest

from ai.features.kinematics import (
    angular_difference_deg,
    calculate_bearing_deg,
    extract_kinematic_features,
    haversine_distance,
)
from ai.schemas import TrackPoint


def test_angular_difference_and_bearing():
    """Verify spherical angular differences and bearing calculations."""
    assert angular_difference_deg(10.0, 30.0) == 20.0
    assert angular_difference_deg(350.0, 10.0) == 20.0
    assert angular_difference_deg(10.0, 350.0) == -20.0
    assert angular_difference_deg(180.0, 180.0) == 0.0

    # Due North bearing
    assert pytest.approx(calculate_bearing_deg(37.0, -122.0, 38.0, -122.0), 0.1) == 0.0
    # Due East bearing
    assert pytest.approx(calculate_bearing_deg(37.0, -122.0, 37.0, -121.0), 0.1) == 90.0


def test_extract_features_empty_and_single_point():
    """Verify empty and single-point edge cases."""
    empty_feat = extract_kinematic_features([])
    assert empty_feat.sample_count == 0
    assert empty_feat.speed_mps == 0.0

    now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    single_p = TrackPoint(
        timestamp=now,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=150.0,
        velocity=18.5,
        heading=90.0,
        confidence=0.9,
    )
    single_feat = extract_kinematic_features([single_p])
    assert single_feat.sample_count == 1
    assert single_feat.speed_mps == 18.5
    assert single_feat.heading_deg == 90.0
    assert single_feat.directional_consistency == 1.0
    assert single_feat.timespan_seconds == 0.0


def test_extract_features_straight_line_flight():
    """Verify straight line flight produces high directional consistency and low turn rate."""
    base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    points = []
    # 10 points moving east at ~20 m/s (~0.0002 deg lon per second at lat 37.7)
    for i in range(10):
        points.append(
            TrackPoint(
                timestamp=base_time + timedelta(seconds=i),
                latitude=37.7749,
                longitude=-122.4194 + (i * 0.000227),  # ~20 m/s
                altitude=100.0,
                velocity=20.0,
                heading=90.0,
            )
        )

    feat = extract_kinematic_features(points)
    assert feat.sample_count == 10
    assert feat.timespan_seconds == 9.0
    assert feat.directional_consistency >= 0.98
    assert feat.turn_rate_dps <= 1.0
    assert feat.loiter_radius_meters is None
    assert feat.vertical_speed_mps == 0.0


def test_extract_features_rapid_climb_and_dive():
    """Verify vertical climb and descent rate feature extraction."""
    base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    # Rapid climb: 100m to 250m over 10 seconds (+15 m/s)
    points_climb = [
        TrackPoint(
            timestamp=base_time + timedelta(seconds=i),
            latitude=37.7749,
            longitude=-122.4194,
            altitude=100.0 + (i * 15.0),
            velocity=10.0,
            heading=0.0,
        )
        for i in range(10)
    ]
    feat_climb = extract_kinematic_features(points_climb)
    assert feat_climb.vertical_speed_mps == 15.0
    assert feat_climb.altitude_variance > 0.0

    # Rapid dive: 250m to 50m over 10 seconds (-20 m/s)
    points_dive = [
        TrackPoint(
            timestamp=base_time + timedelta(seconds=i),
            latitude=37.7749,
            longitude=-122.4194,
            altitude=250.0 - (i * 20.0),
            velocity=10.0,
            heading=0.0,
        )
        for i in range(10)
    ]
    feat_dive = extract_kinematic_features(points_dive)
    assert feat_dive.vertical_speed_mps == -20.0


def test_extract_features_loitering_pattern():
    """Verify circular loitering pattern detection and radius calculation."""
    base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    center_lat, center_lon = 37.7749, -122.4194
    radius_m = 200.0
    # Approximate 200m in degrees
    lat_deg_per_m = 1.0 / 111139.0
    lon_deg_per_m = 1.0 / (111139.0 * math.cos(math.radians(center_lat)))

    points = []
    num_points = 24
    for i in range(num_points):
        theta = (2.0 * math.pi * i) / (num_points - 1)
        lat = center_lat + (radius_m * math.sin(theta) * lat_deg_per_m)
        lon = center_lon + (radius_m * math.cos(theta) * lon_deg_per_m)
        points.append(
            TrackPoint(
                timestamp=base_time + timedelta(seconds=i * 2),
                latitude=lat,
                longitude=lon,
                altitude=120.0,
                velocity=15.0,
                heading=math.degrees(theta + math.pi / 2.0) % 360.0,
            )
        )

    feat = extract_kinematic_features(points)
    assert feat.directional_consistency < 0.2
    assert feat.loiter_radius_meters is not None
    assert 180.0 <= feat.loiter_radius_meters <= 220.0


def test_extract_features_acceleration_variance():
    """Verify speed variation and acceleration variance detection."""
    base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    points = [
        TrackPoint(
            timestamp=base_time + timedelta(seconds=i),
            latitude=37.7749 + (i * 0.0001),
            longitude=-122.4194,
            altitude=100.0,
            velocity=5.0 + (i * 3.0),  # accelerating from 5 m/s to 32 m/s (+3 m/s^2)
            heading=0.0,
        )
        for i in range(10)
    ]
    feat = extract_kinematic_features(points)
    assert feat.acceleration_mps2 == 3.0
    assert feat.speed_variance > 50.0


def test_extract_features_resilience_to_duplicate_timestamps_and_none():
    """Verify robustness to duplicate timestamps, zero deltas, and missing altitudes."""
    base_time = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    points = [
        TrackPoint(
            timestamp=base_time,
            latitude=37.7749,
            longitude=-122.4194,
            altitude=None,
            velocity=12.0,
            heading=45.0,
        ),
        # Duplicate timestamp (zero delta)
        TrackPoint(
            timestamp=base_time,
            latitude=37.7749,
            longitude=-122.4194,
            altitude=None,
            velocity=12.0,
            heading=45.0,
        ),
        TrackPoint(
            timestamp=base_time + timedelta(seconds=5),
            latitude=37.7750,
            longitude=-122.4193,
            altitude=None,
            velocity=12.0,
            heading=45.0,
        ),
    ]

    feat = extract_kinematic_features(points)
    assert feat.sample_count == 3
    assert feat.timespan_seconds == 5.0
    assert feat.vertical_speed_mps == 0.0
    assert feat.altitude_variance == 0.0
