"""Stage S8 Sensor & Payload Digital Twin ORM Models.

Provides entities for vehicle-mounted sensor instances and payload attachments.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class PersistentSensorInstance(Base):
    """Vehicle-mounted sensor instance entity with spatial placement and update rates."""

    __tablename__ = "sensor_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    sensor_type = Column(String(32), nullable=False)  # IMU, GPS, COMPASS, BAROMETER, RANGEFINDER, LIDAR, OPTICAL_FLOW, AIRSPEED, CAMERA
    name = Column(String(128), nullable=False)
    mass_g = Column(Float, nullable=False, default=15.0)
    power_w = Column(Float, nullable=False, default=0.5)
    position_json = Column(JSON, nullable=False)     # {"x": 0.0, "y": 0.0, "z": 0.1}
    orientation_json = Column(JSON, nullable=False)  # {"roll": 0, "pitch": 0, "yaw": 0}
    update_rate_hz = Column(Float, nullable=False, default=50.0)
    health_status = Column(String(32), nullable=False, default="OK")  # OK, DEGRADED, FAILED, DISCONNECTED
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    vehicle = relationship("PersistentVehicle")


class PersistentPayloadInstance(Base):
    """Vehicle-mounted payload attachment (cameras, gimbals, LiDAR scanners)."""

    __tablename__ = "payload_instances"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False, index=True)
    payload_type = Column(String(32), nullable=False)  # CAMERA_PAYLOAD, LIDAR_PAYLOAD, GENERIC_PAYLOAD
    name = Column(String(128), nullable=False)
    mass_g = Column(Float, nullable=False, default=250.0)
    power_w = Column(Float, nullable=False, default=5.0)
    position_json = Column(JSON, nullable=False)     # {"x": 0.0, "y": 0.0, "z": -0.05}
    orientation_json = Column(JSON, nullable=False)  # {"roll": 0, "pitch": 0, "yaw": 0}
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    vehicle = relationship("PersistentVehicle")
