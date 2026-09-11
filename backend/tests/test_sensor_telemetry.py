"""Tests for Stage S8 Normalized Telemetry and Power Budget Schemas."""

from app.schemas.sensor_payload import (
    IMUSample,
    GPSSample,
    RangefinderSample,
    CameraMetadataSample,
    PowerBudgetBreakdown,
)


def test_telemetry_and_power_schemas():
    """Verify serialization and validation of normalized sensor telemetry & power breakdown."""
    imu = IMUSample(
        timestamp=1700000000.0,
        vehicle_id="v1",
        run_id="run-101",
        sensor_instance_id="s-imu-1",
        orientation=[0.0, 0.0, 90.0],
        angular_velocity=[0.01, -0.02, 0.005],
        linear_acceleration=[0.0, 0.0, 9.81],
    )
    assert imu.source == "SIMULATOR"
    assert imu.linear_acceleration[2] == 9.81

    gps = GPSSample(
        timestamp=1700000000.0,
        vehicle_id="v1",
        run_id="run-101",
        sensor_instance_id="s-gps-1",
        latitude=37.7749,
        longitude=-122.4194,
        altitude_m=120.5,
    )
    assert gps.fix_type == 3

    rangefinder = RangefinderSample(
        timestamp=1700000000.0,
        vehicle_id="v1",
        run_id="run-101",
        sensor_instance_id="s-rf-1",
        distance_m=14.2,
    )
    assert rangefinder.max_range_m == 40.0

    cam = CameraMetadataSample(
        timestamp=1700000000.0,
        vehicle_id="v1",
        run_id="run-101",
        sensor_instance_id="s-cam-1",
    )
    assert cam.resolution == [1920, 1080]

    pb = PowerBudgetBreakdown(
        avionics_power_w=5.0,
        sensor_power_w=2.5,
        payload_power_w=8.0,
        total_non_propulsion_power_w=15.5,
        estimated_hover_power_w=215.5,
    )
    assert pb.total_non_propulsion_power_w == 15.5
