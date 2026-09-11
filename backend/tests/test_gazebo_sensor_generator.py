"""Tests for Gazebo Harmonic SDF 1.9 Sensor Generation."""

from app.schemas.sensor_payload import SensorInstanceSpec
from app.simulation.core.sdf_sensor_generator import GazeboSensorGenerator


def test_gazebo_sensor_xml_generation():
    """Verify generating SDF XML elements for IMU, GPS, LiDAR, and Camera sensors."""
    sensors = [
        SensorInstanceSpec(
            vehicle_id="v1",
            sensor_type="IMU",
            name="main_imu",
            mass_g=15.0,
            power_w=0.5,
            position={"x": 0.0, "y": 0.0, "z": 0.05},
            orientation={"roll": 0, "pitch": 0, "yaw": 0},
            update_rate_hz=250.0,
        ),
        SensorInstanceSpec(
            vehicle_id="v1",
            sensor_type="GPS",
            name="navsat_gps",
            mass_g=30.0,
            power_w=0.8,
            position={"x": 0.0, "y": 0.0, "z": 0.12},
            orientation={"roll": 0, "pitch": 0, "yaw": 0},
            update_rate_hz=10.0,
        ),
        SensorInstanceSpec(
            vehicle_id="v1",
            sensor_type="RANGEFINDER",
            name="downward_rangefinder",
            mass_g=40.0,
            power_w=1.2,
            position={"x": 0.0, "y": 0.0, "z": -0.02},
            orientation={"roll": 0, "pitch": 90, "yaw": 0},
            update_rate_hz=50.0,
        ),
        SensorInstanceSpec(
            vehicle_id="v1",
            sensor_type="CAMERA",
            name="fpv_cam",
            mass_g=25.0,
            power_w=1.5,
            position={"x": 0.08, "y": 0.0, "z": 0.02},
            orientation={"roll": 0, "pitch": 0, "yaw": 0},
            update_rate_hz=30.0,
        ),
    ]

    xml = GazeboSensorGenerator.generate_sensors_xml(sensors)
    assert '<sensor name="main_imu" type="imu">' in xml
    assert '<update_rate>250.0</update_rate>' in xml
    assert '<sensor name="navsat_gps" type="navsat">' in xml
    assert '<sensor name="downward_rangefinder" type="gpu_lidar">' in xml
    assert '<sensor name="fpv_cam" type="camera">' in xml
