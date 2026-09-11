"""Stage S11 Swarm Telemetry & Safety-Action Engine ORM Models."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, Integer, Float, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class PersistentSwarmSafetyPolicy(Base):
    """Configurable swarm spatial safety policy entity."""

    __tablename__ = "swarm_safety_policies"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    swarm_id = Column(String(36), ForeignKey("swarms.id", ondelete="CASCADE"), nullable=True, index=True)
    name = Column(String(128), nullable=False)
    min_separation_m = Column(Float, nullable=False, default=5.0)
    warning_separation_m = Column(Float, nullable=False, default=8.0)
    critical_separation_m = Column(Float, nullable=False, default=3.0)
    telemetry_timeout_s = Column(Float, nullable=False, default=5.0)
    link_quality_threshold_percent = Column(Float, nullable=False, default=50.0)
    formation_deviation_threshold_m = Column(Float, nullable=False, default=4.0)
    leader_timeout_s = Column(Float, nullable=False, default=5.0)
    cooldown_s = Column(Float, nullable=False, default=10.0)
    action_escalation = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    updated_at = Column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class PersistentSwarmSafetyEvent(Base):
    """Auditable log of executed safety actions and safety conditions."""

    __tablename__ = "swarm_safety_events"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    swarm_id = Column(String(36), ForeignKey("swarms.id", ondelete="CASCADE"), nullable=False, index=True)
    vehicle_id = Column(String(36), nullable=True)
    target_vehicle_id = Column(String(36), nullable=True)
    event_type = Column(String(64), nullable=False, index=True)
    severity = Column(String(32), nullable=False, default="WARNING", index=True)
    measured_value = Column(Float, nullable=True)
    threshold_value = Column(Float, nullable=True)
    executed_action = Column(String(64), nullable=True)
    policy_version = Column(Integer, nullable=False, default=1)
    details_json = Column(JSON, nullable=True)
    timestamp = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False, index=True)
