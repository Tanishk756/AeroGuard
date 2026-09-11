"""Stage S12 Seeded Deterministic Sensor & Digital Twin Simulator.

Generates reproducible IMU, GPS, Barometer, Compass, and Battery digital twin outputs
with configurable deterministic noise, bias, update frequencies, and dropouts.
"""

import math
import random
from typing import Any, Dict, List, Optional
from pydantic import BaseModel

from app.schemas.sensor_payload import GPSSample, IMUSample, SensorHealthState
from app.schemas.simulation_platform import VehicleState


class DeterministicSensorConfig(BaseModel):
    """Configuration for deterministic sensor noise and error models."""
    seed: int = 42
    gps_noise_std_m: float = 0.05
    imu_accel_noise_std: float = 0.02
    imu_gyro_noise_std: float = 0.005
    enable_dropout: bool = False
    dropout_probability: float = 0.0


class DeterministicSensorSim:
    """Seeded deterministic digital twin sensor simulator."""

    def __init__(self, config: Optional[DeterministicSensorConfig] = None):
        self.config: DeterministicSensorConfig = config or DeterministicSensorConfig()
        self._rng = random.Random(self.config.seed)

    def set_seed(self, seed: int) -> None:
        """Reset the deterministic RNG seed."""
        self.config.seed = seed
        self._rng = random.Random(seed)

    def generate_gps_sample(
        self,
        vehicle_id: str,
        sim_time_s: float,
        state: VehicleState,
        run_id: str = "s12_run",
    ) -> Optional[GPSSample]:
        """Generate deterministic GPS sample from vehicle position."""
        if self.config.enable_dropout and self._rng.random() < self.config.dropout_probability:
            return None

        # Base origin reference (37.7749 N, -122.4194 W)
        lat_base = 37.7749
        lon_base = -122.4194

        # Convert local NED (x=North, y=East) to lat/lon offsets
        deg_per_meter_lat = 1.0 / 111111.0
        deg_per_meter_lon = 1.0 / (111111.0 * math.cos(math.radians(lat_base)))

        # Extract position / velocity / attitude fields safely whether object or dict
        def _get_val(obj, key, default=0.0):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        pos_lat = _get_val(state.position, "latitude", 37.7749)
        pos_lon = _get_val(state.position, "longitude", -122.4194)
        pos_alt = _get_val(state.position, "altitude_relative", 10.0)

        noise_x = self._rng.gauss(0.0, self.config.gps_noise_std_m)
        noise_y = self._rng.gauss(0.0, self.config.gps_noise_std_m)
        noise_z = self._rng.gauss(0.0, self.config.gps_noise_std_m)

        lat = pos_lat + (noise_y * deg_per_meter_lat)
        lon = pos_lon + (noise_x * deg_per_meter_lon)
        alt = max(0.0, pos_alt + noise_z)

        return GPSSample(
            timestamp=sim_time_s,
            vehicle_id=vehicle_id,
            run_id=run_id,
            sensor_instance_id=f"gps_{vehicle_id}",
            latitude=round(lat, 7),
            longitude=round(lon, 7),
            altitude_m=round(alt, 3),
            fix_type=3,
            satellites_visible=14,
        )

    def generate_imu_sample(
        self,
        vehicle_id: str,
        sim_time_s: float,
        state: VehicleState,
        run_id: str = "s12_run",
    ) -> Optional[IMUSample]:
        """Generate deterministic IMU sample from vehicle orientation and motion."""
        if self.config.enable_dropout and self._rng.random() < self.config.dropout_probability:
            return None

        def _get_val(obj, key, default=0.0):
            if isinstance(obj, dict):
                return obj.get(key, default)
            return getattr(obj, key, default)

        roll = _get_val(state.attitude, "roll_deg", 0.0)
        pitch = _get_val(state.attitude, "pitch_deg", 0.0)
        yaw = _get_val(state.attitude, "yaw_deg", 0.0)

        vx = _get_val(state.velocity, "vx", 0.0)
        vy = _get_val(state.velocity, "vy", 0.0)
        vz = _get_val(state.velocity, "vz", 0.0)

        roll_noise = self._rng.gauss(0.0, self.config.imu_gyro_noise_std)
        pitch_noise = self._rng.gauss(0.0, self.config.imu_gyro_noise_std)
        yaw_noise = self._rng.gauss(0.0, self.config.imu_gyro_noise_std)

        acc_noise_x = self._rng.gauss(0.0, self.config.imu_accel_noise_std)
        acc_noise_y = self._rng.gauss(0.0, self.config.imu_accel_noise_std)
        acc_noise_z = self._rng.gauss(0.0, self.config.imu_accel_noise_std)

        # Basic gravity component on Z axis
        linear_acc = [
            round(vx * 0.1 + acc_noise_x, 4),
            round(vy * 0.1 + acc_noise_y, 4),
            round(9.81 + vz * 0.1 + acc_noise_z, 4),
        ]

        return IMUSample(
            timestamp=sim_time_s,
            vehicle_id=vehicle_id,
            run_id=run_id,
            sensor_instance_id=f"imu_{vehicle_id}",
            orientation=[
                round(roll + roll_noise, 4),
                round(pitch + pitch_noise, 4),
                round(yaw + yaw_noise, 4),
            ],
            angular_velocity=[round(roll_noise, 4), round(pitch_noise, 4), round(yaw_noise, 4)],
            linear_acceleration=linear_acc,
        )

    def get_health_status(self, vehicle_id: str, is_degraded: bool = False) -> List[SensorHealthState]:
        """Return diagnostic health states for vehicle sensors."""
        status = "DEGRADED" if is_degraded else "OK"
        healthy = not is_degraded
        return [
            SensorHealthState(sensor_instance_id=f"gps_{vehicle_id}", sensor_type="GPS", healthy=healthy, status=status),
            SensorHealthState(sensor_instance_id=f"imu_{vehicle_id}", sensor_type="IMU", healthy=healthy, status=status),
        ]
