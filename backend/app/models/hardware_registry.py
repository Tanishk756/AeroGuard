"""Stage S4 Hardware Registry & Vehicle Database Models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Float, Integer, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.database.base import Base


class PersistentHardwareComponent(Base):
    """Persistent Hardware Component entity representing real hardware registry entries."""

    __tablename__ = "hardware_components"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    manufacturer = Column(String(100), nullable=False, index=True)
    model = Column(String(100), nullable=False, index=True)
    category = Column(String(50), nullable=False, index=True)
    part_number = Column(String(100), nullable=True)
    datasheet_url = Column(String(500), nullable=True)
    mass_g = Column(Float, nullable=False, default=0.0)
    dimensions_mm = Column(JSON, nullable=True)
    electrical_specs = Column(JSON, nullable=True)
    interfaces = Column(JSON, nullable=True)
    supported_simulation_models = Column(JSON, nullable=True)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)


class PersistentVehicle(Base):
    """Persistent Vehicle Configuration entity representing user-assembled digital twins."""

    __tablename__ = "vehicles"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(100), nullable=False, index=True, default="proj-default-01")
    name = Column(String(150), nullable=False)
    vehicle_type = Column(String(50), nullable=False, default="quadcopter")

    frame_id = Column(String(36), ForeignKey("hardware_components.id"), nullable=False)
    motor_id = Column(String(36), ForeignKey("hardware_components.id"), nullable=False)
    esc_id = Column(String(36), ForeignKey("hardware_components.id"), nullable=False)
    propeller_id = Column(String(36), ForeignKey("hardware_components.id"), nullable=False)
    battery_id = Column(String(36), ForeignKey("hardware_components.id"), nullable=False)
    flight_controller_id = Column(String(36), ForeignKey("hardware_components.id"), nullable=False)
    gps_id = Column(String(36), ForeignKey("hardware_components.id"), nullable=True)

    total_mass_g = Column(Float, nullable=False, default=0.0)
    estimated_hover_throttle = Column(Float, nullable=False, default=0.5)
    thrust_to_weight_ratio = Column(Float, nullable=False, default=2.0)

    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    # Relationships
    frame = relationship("PersistentHardwareComponent", foreign_keys=[frame_id])
    motor = relationship("PersistentHardwareComponent", foreign_keys=[motor_id])
    esc = relationship("PersistentHardwareComponent", foreign_keys=[esc_id])
    propeller = relationship("PersistentHardwareComponent", foreign_keys=[propeller_id])
    battery = relationship("PersistentHardwareComponent", foreign_keys=[battery_id])
    flight_controller = relationship("PersistentHardwareComponent", foreign_keys=[flight_controller_id])
    gps = relationship("PersistentHardwareComponent", foreign_keys=[gps_id])
