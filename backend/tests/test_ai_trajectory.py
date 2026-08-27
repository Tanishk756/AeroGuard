"""Unit tests for AeroGuard AI trajectory prediction and geofence ingress estimation."""

from datetime import UTC, datetime
import pytest

from ai.schemas import TrajectoryPrediction
from ai.trajectory.predictor import (
    advance_position_wgs84,
    estimate_geofence_ingress,
    haversine_distance,
    predict_trajectory,
)


def test_advance_position_wgs84():
    """Verify forward great-circle coordinate displacement."""
    lat, lon = 37.7749, -122.4194
    # Move 1000m North (heading 0.0)
    next_lat, next_lon = advance_position_wgs84(lat, lon, 0.0, 1000.0)
    dist = haversine_distance(lat, lon, next_lat, next_lon)
    assert pytest.approx(dist, 1.0) == 1000.0
    assert next_lat > lat
    assert pytest.approx(next_lon, 0.0001) == lon


def test_predict_trajectory_constant_velocity():
    """Verify constant-velocity trajectory projection."""
    now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    pred = predict_trajectory(
        track_id="TRK-100",
        current_lat=37.7749,
        current_lon=-122.4194,
        current_alt=150.0,
        speed_mps=20.0,
        heading_deg=90.0,  # East
        horizon_seconds=30.0,
        step_interval_seconds=5.0,
        start_time=now,
    )

    assert pred.track_id == "TRK-100"
    assert pred.prediction_horizon_seconds == 30.0
    assert pred.model_type == "CONSTANT_VELOCITY"
    assert len(pred.waypoints) == 6  # 5s, 10s, 15s, 20s, 25s, 30s

    wp_last = pred.waypoints[-1]
    assert wp_last.time_offset_seconds == 30.0
    assert wp_last.longitude > -122.4194  # Moved East
    assert wp_last.uncertainty_radius_meters > pred.waypoints[0].uncertainty_radius_meters


def test_predict_trajectory_constant_acceleration():
    """Verify constant-acceleration trajectory projection."""
    pred = predict_trajectory(
        track_id="TRK-101",
        current_lat=37.7749,
        current_lon=-122.4194,
        current_alt=100.0,
        speed_mps=10.0,
        heading_deg=0.0,
        acceleration_mps2=3.0,  # +3 m/s^2
        horizon_seconds=20.0,
        step_interval_seconds=5.0,
    )

    assert pred.model_type == "CONSTANT_ACCELERATION"
    # Total distance in 20s: v0*t + 0.5*a*t^2 = 10*20 + 0.5*3*400 = 200 + 600 = 800m
    total_dist = haversine_distance(
        37.7749, -122.4194, pred.waypoints[-1].latitude, pred.waypoints[-1].longitude
    )
    assert pytest.approx(total_dist, 25.0) == 800.0


def test_predict_trajectory_stationary_target():
    """Verify stationary target projection keeps coordinates constant while expanding uncertainty."""
    pred = predict_trajectory(
        track_id="TRK-102",
        current_lat=37.7749,
        current_lon=-122.4194,
        speed_mps=0.0,
        heading_deg=None,
        horizon_seconds=30.0,
        step_interval_seconds=10.0,
    )

    assert len(pred.waypoints) == 3
    for wp in pred.waypoints:
        assert wp.latitude == 37.7749
        assert wp.longitude == -122.4194
    assert pred.waypoints[-1].uncertainty_radius_meters > pred.waypoints[0].uncertainty_radius_meters


def test_geofence_ingress_estimation_approaching():
    """Verify ingress detection when predicted path crosses an active geofence boundary."""
    # Geofence situated North of target: lat 37.7800 to 37.7900
    geofence = {
        "id": "GEO-01",
        "name": "Northern Defense Perimeter",
        "geometry_type": "BBOX",
        "geometry": {
            "min_lat": 37.7800,
            "max_lat": 37.7900,
            "min_lon": -122.4500,
            "max_lon": -122.4000,
        },
    }

    # Target starting at 37.7749 moving North at 30 m/s
    # Distance to 37.7800 is ~567 meters -> time to breach ~19 seconds
    pred = predict_trajectory(
        track_id="TRK-200",
        current_lat=37.7749,
        current_lon=-122.4194,
        speed_mps=30.0,
        heading_deg=0.0,
        horizon_seconds=60.0,
        step_interval_seconds=5.0,
    )

    estimates = estimate_geofence_ingress(
        track_id="TRK-200",
        trajectory=pred,
        geofences=[geofence],
        current_lat=37.7749,
        current_lon=-122.4194,
    )

    assert len(estimates) == 1
    est = estimates[0]
    assert est.geofence_id == "GEO-01"
    assert est.status == "APPROACHING"
    assert est.estimated_time_to_breach_seconds is not None
    assert 15.0 <= est.estimated_time_to_breach_seconds <= 25.0
    assert est.intersection_latitude is not None


def test_geofence_ingress_estimation_already_inside():
    """Verify ingress detection when target is already inside geofence."""
    geofence = {
        "id": "GEO-02",
        "name": "Core Facility Zone",
        "geometry_type": "BBOX",
        "geometry": {
            "min_lat": 37.7000,
            "max_lat": 37.8000,
            "min_lon": -122.5000,
            "max_lon": -122.4000,
        },
    }

    pred = predict_trajectory(
        track_id="TRK-201",
        current_lat=37.7500,
        current_lon=-122.4500,
        speed_mps=15.0,
        heading_deg=90.0,
        horizon_seconds=30.0,
    )

    estimates = estimate_geofence_ingress(
        track_id="TRK-201",
        trajectory=pred,
        geofences=[geofence],
        current_lat=37.7500,
        current_lon=-122.4500,
    )

    assert len(estimates) == 1
    est = estimates[0]
    assert est.status == "INSIDE"
    assert est.estimated_time_to_breach_seconds == 0.0


def test_geofence_ingress_estimation_diverging_or_no_intersection():
    """Verify ingress detection when target is heading away from geofence."""
    geofence = {
        "id": "GEO-03",
        "name": "North Guard Zone",
        "geometry_type": "BBOX",
        "geometry": {
            "min_lat": 37.8000,
            "max_lat": 37.8500,
            "min_lon": -122.4500,
            "max_lon": -122.4000,
        },
    }

    # Heading South (180.0) away from North zone
    pred = predict_trajectory(
        track_id="TRK-202",
        current_lat=37.7749,
        current_lon=-122.4194,
        speed_mps=20.0,
        heading_deg=180.0,
        horizon_seconds=60.0,
    )

    estimates = estimate_geofence_ingress(
        track_id="TRK-202",
        trajectory=pred,
        geofences=[geofence],
        current_lat=37.7749,
        current_lon=-122.4194,
    )

    assert len(estimates) == 1
    assert estimates[0].status == "NO_INTERSECTION"
    assert estimates[0].estimated_time_to_breach_seconds is None
