"""Synthetic sensor observation models with range, FOV, and noise generation."""

import math
import random
from datetime import datetime

from app.models.sensor import SensorSourceClass
from app.schemas.ingestion import RawDetection
from app.schemas.scenario import ScenarioSensorDefinition
from app.simulation.trajectories import (
    EARTH_RADIUS_METERS,
    TargetKinematicState,
    calculate_bearing_deg,
    haversine_distance,
)


def is_bearing_in_fov(bearing_deg: float, fov_start_deg: float, fov_span_deg: float) -> bool:
    """Check if a bearing in [0, 360) is within an azimuth field-of-view span."""
    offset = (bearing_deg - fov_start_deg + 360.0) % 360.0
    return offset <= fov_span_deg


class SyntheticSensor:
    def __init__(self, definition: ScenarioSensorDefinition):
        self.sensor_id = definition.sensor_id
        self.modality = definition.modality.lower()
        self.latitude = float(definition.latitude)
        self.longitude = float(definition.longitude)
        self.altitude = float(definition.altitude) if definition.altitude is not None else None
        self.range_meters = float(definition.range_meters)
        self.detection_probability = float(definition.detection_probability)
        self.position_uncertainty_meters = float(definition.position_uncertainty_meters)
        self.altitude_uncertainty_meters = (
            float(definition.altitude_uncertainty_meters)
            if definition.altitude_uncertainty_meters is not None
            else None
        )
        self.velocity_uncertainty_mps = (
            float(definition.velocity_uncertainty_mps)
            if definition.velocity_uncertainty_mps is not None
            else None
        )
        self.fov_azimuth_start_deg = (
            float(definition.fov_azimuth_start_deg)
            if definition.fov_azimuth_start_deg is not None
            else None
        )
        self.fov_azimuth_span_deg = (
            float(definition.fov_azimuth_span_deg)
            if definition.fov_azimuth_span_deg is not None
            else None
        )

    def evaluate_target(
        self,
        target: TargetKinematicState,
        sim_time: datetime,
        tick_index: int,
        prng: random.Random,
    ) -> RawDetection | None:
        """Evaluate synthetic sensor detection of a target during a simulation tick."""
        if not target.is_active:
            return None

        # 1. Range Gating
        dist_m = haversine_distance(self.latitude, self.longitude, target.latitude, target.longitude)
        if dist_m > self.range_meters:
            return None

        # 2. Field-of-View Gating
        if self.fov_azimuth_start_deg is not None and self.fov_azimuth_span_deg is not None:
            bearing = calculate_bearing_deg(self.latitude, self.longitude, target.latitude, target.longitude)
            if not is_bearing_in_fov(bearing, self.fov_azimuth_start_deg, self.fov_azimuth_span_deg):
                return None

        # 3. Detection Probability
        if prng.random() > self.detection_probability:
            return None

        # 4. Deterministic Measurement Noise Generation
        # Position noise: Gaussian in meters converted to delta lat/lon
        noise_x = prng.gauss(0.0, self.position_uncertainty_meters)
        noise_y = prng.gauss(0.0, self.position_uncertainty_meters)

        delta_lat = (noise_y / EARTH_RADIUS_METERS) * (180.0 / math.pi)
        lat_cos = max(math.cos(math.radians(target.latitude)), 0.01)
        delta_lon = (noise_x / (EARTH_RADIUS_METERS * lat_cos)) * (180.0 / math.pi)

        meas_lat = max(-90.0, min(90.0, target.latitude + delta_lat))
        meas_lon = (target.longitude + delta_lon + 540.0) % 360.0 - 180.0

        # Altitude noise
        meas_alt: float | None = None
        if self.altitude_uncertainty_meters is not None and target.altitude is not None:
            noise_alt = prng.gauss(0.0, self.altitude_uncertainty_meters)
            meas_alt = max(0.0, round(target.altitude + noise_alt, 2))
        elif target.altitude is not None and self.modality in ("radar", "optical"):
            # Use baseline uncertainty for sensors measuring altitude
            noise_alt = prng.gauss(0.0, 5.0)
            meas_alt = max(0.0, round(target.altitude + noise_alt, 2))

        # Velocity noise
        meas_vel: float | None = None
        if self.velocity_uncertainty_mps is not None:
            noise_vel = prng.gauss(0.0, self.velocity_uncertainty_mps)
            meas_vel = max(0.0, round(target.velocity + noise_vel, 2))
        elif self.modality == "radar":
            noise_vel = prng.gauss(0.0, 1.0)
            meas_vel = max(0.0, round(target.velocity + noise_vel, 2))

        # Heading noise (handle wrap-around)
        noise_head = prng.gauss(0.0, 2.0)
        meas_head = round((target.heading + noise_head) % 360.0, 2)

        # Realistic confidence based on range ratio
        range_ratio = dist_m / max(self.range_meters, 1.0)
        base_confidence = max(0.40, min(0.95, 0.90 * (1.0 - 0.40 * range_ratio)))

        return RawDetection(
            source_detection_id=f"sim-{self.sensor_id}-{target.target_id}-{tick_index}",
            timestamp=sim_time,
            sensor_id=self.sensor_id,
            latitude=round(meas_lat, 7),
            longitude=round(meas_lon, 7),
            altitude=meas_alt,
            velocity=meas_vel,
            heading=meas_head,
            confidence=round(base_confidence, 4),
            horizontal_uncertainty=round(self.position_uncertainty_meters, 2),
            vertical_uncertainty=(
                round(self.altitude_uncertainty_meters, 2)
                if self.altitude_uncertainty_meters is not None
                else None
            ),
            classification=target.classification,
            source_class=SensorSourceClass.SIMULATION,
            source_type=self.modality,
            metadata={"target_id": target.target_id, "tick": tick_index, "range_m": round(dist_m, 1)},
        )
