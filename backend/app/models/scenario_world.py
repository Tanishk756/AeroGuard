"""Stage S6 Scenario & World Management ORM Models.

Provides first-class entities for versioned scenarios, simulator-neutral worlds, and world objects.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, Boolean, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class PersistentSimulationWorld(Base):
    """Simulator-neutral environment world entity."""

    __tablename__ = "simulation_worlds"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), nullable=False, index=True, default="proj-default-01")
    name = Column(String(128), nullable=False)
    world_type = Column(String(32), nullable=False, default="FLAT_GROUND")
    description = Column(String(256), nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    objects = relationship("PersistentWorldObject", back_populates="world", cascade="all, delete-orphan")


class PersistentWorldObject(Base):
    """Generic static or dynamic physical entity placed within a SimulationWorld."""

    __tablename__ = "world_objects"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    world_id = Column(String(36), ForeignKey("simulation_worlds.id"), nullable=False, index=True)
    object_type = Column(String(64), nullable=False)  # STATIC_BOX, STATIC_CYLINDER, LANDING_PAD
    position_json = Column(JSON, nullable=False)     # {"x": 0.0, "y": 0.0, "z": 0.0}
    orientation_json = Column(JSON, nullable=False)  # {"roll": 0.0, "pitch": 0.0, "yaw": 0.0}
    scale_json = Column(JSON, nullable=False)        # {"x": 1.0, "y": 1.0, "z": 1.0}
    collision_enabled = Column(Boolean, default=True, nullable=False)
    visual_enabled = Column(Boolean, default=True, nullable=False)
    metadata_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    world = relationship("PersistentSimulationWorld", back_populates="objects")


class PersistentScenarioEntity(Base):
    """First-class versioned simulation scenario configuration entity."""

    __tablename__ = "scenario_entities"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), nullable=False, index=True, default="proj-default-01")
    name = Column(String(128), nullable=False)
    description = Column(String(256), nullable=True)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False)
    simulator = Column(String(32), nullable=False, default="GAZEBO")
    autopilot = Column(String(32), nullable=False, default="ARDUPILOT")
    world_id = Column(String(36), ForeignKey("simulation_worlds.id"), nullable=False)
    environment_config_json = Column(JSON, nullable=False)
    physics_config_json = Column(JSON, nullable=False)
    weather_config_json = Column(JSON, nullable=False)
    spawn_config_json = Column(JSON, nullable=False)
    random_seed = Column(Integer, nullable=False, default=42)
    configuration_version = Column(Integer, nullable=False, default=1)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    vehicle = relationship("PersistentVehicle")
    world = relationship("PersistentSimulationWorld")
