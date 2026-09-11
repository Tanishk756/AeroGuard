"""Stage S8 Dynamic Gazebo Sensor Generator Engine.

Compiles SensorInstanceSpec items into valid Gazebo Harmonic SDF 1.9 sensor XML elements.
"""

from typing import List
from app.schemas.sensor_payload import SensorInstanceSpec


class GazeboSensorGenerator:
    """Generates SDF 1.9 XML sensor definitions for Gazebo Harmonic."""

    @classmethod
    def generate_sensors_xml(cls, sensors: List[SensorInstanceSpec]) -> str:
        sensors_xml = ""

        for sensor in sensors:
            pos = sensor.position
            ori = sensor.orientation
            pose_str = f"{pos.get('x', 0.0)} {pos.get('y', 0.0)} {pos.get('z', 0.0)} {ori.get('roll', 0.0)} {ori.get('pitch', 0.0)} {ori.get('yaw', 0.0)}"

            if sensor.sensor_type == "IMU":
                sensors_xml += f"""
      <sensor name="{sensor.name or 'imu_sensor'}" type="imu">
        <always_on>true</always_on>
        <update_rate>{sensor.update_rate_hz}</update_rate>
        <pose>{pose_str}</pose>
        <imu>
          <angular_velocity>
            <x><noise type="gaussian"><mean>0</mean><stddev>0.0002</stddev></noise></x>
            <y><noise type="gaussian"><mean>0</mean><stddev>0.0002</stddev></noise></y>
            <z><noise type="gaussian"><mean>0</mean><stddev>0.0002</stddev></noise></z>
          </angular_velocity>
          <linear_acceleration>
            <x><noise type="gaussian"><mean>0</mean><stddev>0.01</stddev></noise></x>
            <y><noise type="gaussian"><mean>0</mean><stddev>0.01</stddev></noise></y>
            <z><noise type="gaussian"><mean>0</mean><stddev>0.01</stddev></noise></z>
          </linear_acceleration>
        </imu>
      </sensor>"""

            elif sensor.sensor_type in ("GPS", "GNSS"):
                sensors_xml += f"""
      <sensor name="{sensor.name or 'navsat_sensor'}" type="navsat">
        <always_on>true</always_on>
        <update_rate>{sensor.update_rate_hz}</update_rate>
        <pose>{pose_str}</pose>
      </sensor>"""

            elif sensor.sensor_type in ("RANGEFINDER", "LIDAR"):
                sensors_xml += f"""
      <sensor name="{sensor.name or 'rangefinder_sensor'}" type="gpu_lidar">
        <always_on>true</always_on>
        <update_rate>{sensor.update_rate_hz}</update_rate>
        <pose>{pose_str}</pose>
        <ray>
          <scan>
            <horizontal><samples>1</samples><resolution>1</resolution><min_angle>0</min_angle><max_angle>0</max_angle></horizontal>
          </scan>
          <range><min>0.1</min><max>40.0</max><resolution>0.01</resolution></range>
        </ray>
      </sensor>"""

            elif sensor.sensor_type == "CAMERA":
                sensors_xml += f"""
      <sensor name="{sensor.name or 'camera_sensor'}" type="camera">
        <always_on>true</always_on>
        <update_rate>{sensor.update_rate_hz}</update_rate>
        <pose>{pose_str}</pose>
        <camera>
          <horizontal_fov>1.46608</horizontal_fov>
          <image><width>1920</width><height>1080</height><format>R8G8B8</format></image>
          <clip><near>0.1</near><far>1000.0</far></clip>
        </camera>
      </sensor>"""

        return sensors_xml
