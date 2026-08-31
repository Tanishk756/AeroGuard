"""Stage S5 Dynamic Gazebo SDF Generator Engine.

Generates Gazebo Harmonic 8.15 XML SDF 1.9 models dynamically from CompiledVehicleModel data.
"""

import hashlib
from typing import Tuple
from app.simulation.core.vehicle_compiler import CompiledVehicleModel
from app.core.telemetry import GAZEBO_MODEL_GENERATION_TOTAL


class GazeboVehicleGenerator:
    """Generates dynamic Gazebo Harmonic SDF 1.9 XML artifacts from compiled vehicle specifications."""

    @classmethod
    def generate_sdf(cls, model: CompiledVehicleModel) -> Tuple[str, str]:
        GAZEBO_MODEL_GENERATION_TOTAL.inc()

        mass = model.total_mass_kg
        ixx = model.inertia["ixx"]
        iyy = model.inertia["iyy"]
        izz = model.inertia["izz"]
        arm_m = model.arm_length_m

        # Dynamic Motor Plugins XML Blocks
        motor_plugins_xml = ""
        for idx, (mx, my, mz) in enumerate(model.motor_positions):
            motor_num = idx + 1
            turning_dir = "ccw" if motor_num in (1, 2) else "cw"
            motor_plugins_xml += f"""
    <plugin filename="gz-sim-multicopter-motor-model-system" name="gz::sim::systems::MulticopterMotorModel">
      <robotNamespace>aeroguard/{model.vehicle_id}</robotNamespace>
      <jointName>rotor_{motor_num}_joint</jointName>
      <linkName>rotor_{motor_num}</linkName>
      <turningDirection>{turning_dir}</turningDirection>
      <timeConstantUp>0.0125</timeConstantUp>
      <timeConstantDown>0.025</timeConstantDown>
      <maxRotVelocity>{int(model.estimated_max_rpm * 0.1047)}</maxRotVelocity>
      <motorConstant>8.548e-06</motorConstant>
      <momentConstant>0.016</momentConstant>
      <commandSubTopic>gazebo/command/motor_speed</commandSubTopic>
      <motorNumber>{idx}</motorNumber>
    </plugin>"""

        sdf_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sdf version="1.9">
  <model name="aeroguard_vehicle_{model.vehicle_id}">
    <pose>0 0 0.2 0 0 0</pose>
    <link name="base_link">
      <inertial>
        <mass>{mass}</mass>
        <pose>{model.center_of_mass['x']} {model.center_of_mass['y']} {model.center_of_mass['z']} 0 0 0</pose>
        <inertia>
          <ixx>{ixx}</ixx>
          <ixy>0.0</ixy>
          <ixz>0.0</ixz>
          <iyy>{iyy}</iyy>
          <iyz>0.0</iyz>
          <izz>{izz}</izz>
        </inertia>
      </inertial>

      <visual name="main_frame_visual">
        <geometry>
          <box>
            <size>{arm_m * 2.0} {arm_m * 2.0} 0.05</size>
          </box>
        </geometry>
        <material>
          <ambient>0.1 0.1 0.1 1.0</ambient>
          <diffuse>0.2 0.2 0.2 1.0</diffuse>
        </material>
      </visual>

      <collision name="main_frame_collision">
        <geometry>
          <box>
            <size>{arm_m * 2.0} {arm_m * 2.0} 0.05</size>
          </box>
        </geometry>
      </collision>

      <!-- IMU Sensor Plugin -->
      <sensor name="imu_sensor" type="imu">
        <always_on>true</always_on>
        <update_rate>250</update_rate>
        <visualize>false</visualize>
      </sensor>

      <!-- GPS / NavSat Sensor Plugin -->
      <sensor name="navsat_sensor" type="navsat">
        <always_on>true</always_on>
        <update_rate>10</update_rate>
      </sensor>
    </link>

    {motor_plugins_xml}
  </model>
</sdf>
"""

        sdf_hash = hashlib.sha256(sdf_xml.encode("utf-8")).hexdigest()
        return sdf_xml, sdf_hash
