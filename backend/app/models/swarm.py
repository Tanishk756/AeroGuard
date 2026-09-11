"""Stage S10 Multi-Vehicle Swarm & Formation ORM Models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class PersistentSwarm(Base):
    """Multi-vehicle swarm configuration and operational entity."""

    __tablename__ = "swarms"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(128), nullable=False)
    description = Column(String(256), nullable=True)
    leader_vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=True)
    formation_type = Column(String(32), nullable=False, default="LINE")  # LINE, COLUMN, V_FORMATION, GRID, CIRCLE
    formation_spacing_m = Column(Float, nullable=False, default=10.0)
    min_separation_m = Column(Float, nullable=False, default=5.0)
    status = Column(String(32), nullable=False, default="IDLE")  # IDLE, ACTIVE, DEGRADED, CRITICAL, DISCONNECTED
    config_json = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    members = relationship(
        "PersistentSwarmMember",
        back_populates="swarm",
        cascade="all, delete-orphan",
        order_by="PersistentSwarmMember.slot_index",
    )


class PersistentSwarmMember(Base):
    """Membership mapping vehicle into a swarm slot."""

    __tablename__ = "swarm_members"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    swarm_id = Column(String(36), ForeignKey("swarms.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id", ondelete="CASCADE"), nullable=False, index=True)
    role = Column(String(32), nullable=False, default="FOLLOWER")  # LEADER, FOLLOWER
    slot_index = Column(Integer, nullable=False, default=0)
    offset_x = Column(Float, nullable=False, default=0.0)
    offset_y = Column(Float, nullable=False, default=0.0)
    offset_z = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    swarm = relationship("PersistentSwarm", back_populates="members")
