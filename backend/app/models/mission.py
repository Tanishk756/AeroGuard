"""Stage S7 Mission Planner ORM Models.

Provides entities for versioned missions, deterministic mission items, and immutable mission run snapshots.
"""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class PersistentMission(Base):
    """First-class versioned flight mission entity."""

    __tablename__ = "missions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    project_id = Column(String(64), nullable=False, index=True, default="proj-default-01")
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False)
    scenario_id = Column(String(36), ForeignKey("scenario_entities.id"), nullable=False)
    name = Column(String(128), nullable=False)
    description = Column(String(256), nullable=True)
    version = Column(Integer, nullable=False, default=1)
    status = Column(String(32), nullable=False, default="CREATED")  # CREATED, VALIDATED, UPLOADED, RUNNING, COMPLETED, ABORTED
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    items = relationship("PersistentMissionItem", back_populates="mission", cascade="all, delete-orphan", order_by="PersistentMissionItem.sequence")


class PersistentMissionItem(Base):
    """Deterministic ordered item within a flight mission."""

    __tablename__ = "mission_items"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    mission_id = Column(String(36), ForeignKey("missions.id"), nullable=False, index=True)
    sequence = Column(Integer, nullable=False)
    command_type = Column(String(32), nullable=False)  # TAKEOFF, WAYPOINT, LOITER, LAND, RETURN_TO_HOME
    latitude = Column(Float, nullable=True)
    longitude = Column(Float, nullable=True)
    altitude_m = Column(Float, nullable=False, default=10.0)
    acceptance_radius_m = Column(Float, nullable=False, default=2.0)
    loiter_duration_s = Column(Float, nullable=False, default=0.0)
    params_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    mission = relationship("PersistentMission", back_populates="items")


class PersistentMissionRunSnapshot(Base):
    """Immutable snapshot recording complete vehicle, scenario, world, and mission hashes for a run."""

    __tablename__ = "mission_run_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(64), nullable=False, index=True, unique=True)
    mission_id = Column(String(36), ForeignKey("missions.id"), nullable=False)
    mission_hash = Column(String(64), nullable=False)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False)
    vehicle_hash = Column(String(64), nullable=False)
    scenario_id = Column(String(36), ForeignKey("scenario_entities.id"), nullable=False)
    scenario_hash = Column(String(64), nullable=False)
    world_hash = Column(String(64), nullable=False)
    snapshot_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
