"""Stage S6 Dynamic Gazebo World Generator Engine.

Compiles SimulationWorld entities, environment, weather, and physics specs into valid Gazebo Harmonic SDF 1.9 world files.
"""

import hashlib
import math
from typing import List, Tuple
from app.models.scenario_world import PersistentSimulationWorld, PersistentWorldObject
from app.schemas.scenario_world import (
    EnvironmentConfiguration,
    WeatherConfiguration,
    PhysicsConfiguration,
    WorldObjectSpec,
)
from app.core.telemetry import WORLD_GENERATION_TOTAL


class GazeboWorldGenerator:
    """Generates dynamic Gazebo Harmonic SDF 1.9 XML world files from scenario specifications."""

    @classmethod
    def generate_world_sdf(
        cls,
        world_name: str,
        objects: List[PersistentWorldObject],
        environment: EnvironmentConfiguration,
        weather: WeatherConfiguration,
        physics: PhysicsConfiguration,
    ) -> Tuple[str, str]:
        WORLD_GENERATION_TOTAL.inc()

        # 1. Calculate Wind Vector Components (vx, vy)
        wind_angle_rad = math.radians(weather.wind_direction_deg)
        wind_vx = round(weather.wind_speed_m_s * math.cos(wind_angle_rad), 3)
        wind_vy = round(weather.wind_speed_m_s * math.sin(wind_angle_rad), 3)

        # 2. Render Static World Objects XML
        objects_xml = ""
        for idx, obj in enumerate(objects):
            pos = obj.position_json
            ori = obj.orientation_json
            scale = obj.scale_json
            obj_name = f"world_obj_{idx+1}_{obj.object_type.lower()}"

            if obj.object_type == "STATIC_BOX":
                geom_xml = f"<box><size>{scale['x']} {scale['y']} {scale['z']}</size></box>"
                color_xml = "<ambient>0.5 0.5 0.5 1</ambient><diffuse>0.7 0.7 0.7 1</diffuse>"
            elif obj.object_type == "STATIC_CYLINDER":
                geom_xml = f"<cylinder><radius>{scale['x']/2.0}</radius><length>{scale['z']}</length></cylinder>"
                color_xml = "<ambient>0.2 0.4 0.8 1</ambient><diffuse>0.3 0.5 0.9 1</diffuse>"
            elif obj.object_type == "LANDING_PAD":
                geom_xml = f"<box><size>{scale['x']} {scale['y']} 0.02</size></box>"
                color_xml = "<ambient>0.9 0.8 0.1 1</ambient><diffuse>1.0 0.9 0.2 1</diffuse>"
            else:
                geom_xml = f"<box><size>{scale['x']} {scale['y']} {scale['z']}</size></box>"
                color_xml = "<ambient>0.4 0.4 0.4 1</ambient><diffuse>0.6 0.6 0.6 1</diffuse>"

            objects_xml += f"""
    <model name="{obj_name}">
      <static>true</static>
      <pose>{pos['x']} {pos['y']} {pos['z']} {ori['roll']} {ori['pitch']} {ori['yaw']}</pose>
      <link name="link">
        <visual name="visual">
          <geometry>{geom_xml}</geometry>
          <material>{color_xml}</material>
        </visual>
        <collision name="collision">
          <geometry>{geom_xml}</geometry>
        </collision>
      </link>
    </model>"""

        # 3. Construct Complete World SDF XML
        world_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<sdf version="1.9">
  <world name="{world_name}">
    <physics name="default_physics" type="ignored">
      <max_step_size>{physics.step_size_s}</max_step_size>
      <real_time_factor>{physics.real_time_factor}</real_time_factor>
      <real_time_update_rate>{physics.simulation_rate_hz}</real_time_update_rate>
    </physics>

    <!-- Wind Effects Plugin -->
    <plugin filename="gz-sim-wind-effects-system" name="gz::sim::systems::WindEffects">
      <horizontal>
        <magnitude>{weather.wind_speed_m_s}</magnitude>
        <direction>{weather.wind_direction_deg}</direction>
      </horizontal>
      <force_vector>{wind_vx} {wind_vy} 0.0</force_vector>
    </plugin>

    <!-- Sun Directional Light -->
    <light type="directional" name="sun">
      <cast_shadows>true</cast_shadows>
      <pose>0 0 10 0 0 0</pose>
      <diffuse>0.8 0.8 0.8 1</diffuse>
      <specular>0.2 0.2 0.2 1</specular>
      <direction>-0.5 0.1 -0.9</direction>
    </light>

    <!-- Ground Plane Model -->
    <model name="ground_plane">
      <static>true</static>
      <link name="ground_link">
        <collision name="ground_collision">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>1000 1000</size>
            </plane>
          </geometry>
        </collision>
        <visual name="ground_visual">
          <geometry>
            <plane>
              <normal>0 0 1</normal>
              <size>1000 1000</size>
            </plane>
          </geometry>
          <material>
            <ambient>0.3 0.5 0.3 1</ambient>
            <diffuse>0.3 0.5 0.3 1</diffuse>
          </material>
        </visual>
      </link>
    </model>

    {objects_xml}
  </world>
</sdf>
"""

        world_hash = hashlib.sha256(world_xml.encode("utf-8")).hexdigest()
        return world_xml, world_hash
