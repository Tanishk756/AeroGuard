"""Stage S8 Sensor, Payload, Health, Telemetry, and Power Schemas."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class SensorInstanceSpec(BaseModel):
    """Vehicle-mounted sensor instance specification."""
    id: Optional[str] = None
    vehicle_id: str
    sensor_type: str  # IMU, GPS, COMPASS, BAROMETER, RANGEFINDER, LIDAR, OPTICAL_FLOW, AIRSPEED, CAMERA
    name: str
    mass_g: float = Field(default=15.0, ge=0.0)
    power_w: float = Field(default=0.5, ge=0.0)
    position: Dict[str, float] = Field(default={"x": 0.0, "y": 0.0, "z": 0.1})
    orientation: Dict[str, float] = Field(default={"roll": 0, "pitch": 0, "yaw": 0})
    update_rate_hz: float = Field(default=50.0, ge=0.1, le=1000.0)
    health_status: str = Field(default="OK")  # OK, DEGRADED, FAILED, DISCONNECTED
    config: Optional[Dict[str, Any]] = None


class PayloadInstanceSpec(BaseModel):
    """Vehicle-mounted payload attachment specification."""
    id: Optional[str] = None
    vehicle_id: str
    payload_type: str  # CAMERA_PAYLOAD, LIDAR_PAYLOAD, GENERIC_PAYLOAD
    name: str
    mass_g: float = Field(default=250.0, ge=0.0)
    power_w: float = Field(default=5.0, ge=0.0)
    position: Dict[str, float] = Field(default={"x": 0.0, "y": 0.0, "z": -0.05})
    orientation: Dict[str, float] = Field(default={"roll": 0, "pitch": 0, "yaw": 0})
    config: Optional[Dict[str, Any]] = None


class SensorHealthState(BaseModel):
    """Diagnostic health state for a sensor instance."""
    sensor_instance_id: str
    sensor_type: str
    healthy: bool
    status: str  # OK, DEGRADED, FAILED, DISCONNECTED
    error_code: Optional[str] = None


class IMUSample(BaseModel):
    """Normalized IMU sensor telemetry sample."""
    timestamp: float
    vehicle_id: str
    run_id: str
    sensor_instance_id: str
    source: str = "SIMULATOR"
    orientation: List[float]  # [roll, pitch, yaw] deg
    angular_velocity: List[float]  # [rad/s]
    linear_acceleration: List[float]  # [m/s^2]


class GPSSample(BaseModel):
    """Normalized GNSS / GPS sensor telemetry sample."""
    timestamp: float
    vehicle_id: str
    run_id: str
    sensor_instance_id: str
    source: str = "SIMULATOR"
    latitude: float
    longitude: float
    altitude_m: float
    fix_type: int = 3  # 3D Fix
    satellites_visible: int = 12


class RangefinderSample(BaseModel):
    """Normalized Rangefinder / LiDAR distance sample."""
    timestamp: float
    vehicle_id: str
    run_id: str
    sensor_instance_id: str
    source: str = "SIMULATOR"
    distance_m: float
    min_range_m: float = 0.1
    max_range_m: float = 40.0


class CameraMetadataSample(BaseModel):
    """Camera payload metadata sample."""
    timestamp: float
    vehicle_id: str
    run_id: str
    sensor_instance_id: str
    resolution: List[int] = Field(default=[1920, 1080])
    frame_rate_fps: int = 30
    fov_deg: float = 84.0


class PowerBudgetBreakdown(BaseModel):
    """Power budget breakdown including avionics, sensors, and payloads."""
    avionics_power_w: float
    sensor_power_w: float
    payload_power_w: float
    total_non_propulsion_power_w: float
    estimated_hover_power_w: float
