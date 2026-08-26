"""Scenario metadata model; execution is intentionally deferred."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.sensor import SensorSourceClass


class ScenarioStatus(StrEnum):
    DRAFT = "DRAFT"
    READY = "READY"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class Scenario(Base):
    __tablename__ = "scenarios"
    __table_args__ = (
        Index("ix_scenarios_status", "status"),
        Index("ix_scenarios_created_by_user_id", "created_by_user_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str] = mapped_column(String(1000), nullable=False)
    status: Mapped[ScenarioStatus] = mapped_column(Enum(ScenarioStatus, native_enum=False, create_constraint=True), nullable=False, default=ScenarioStatus.DRAFT)
    created_by_user_id: Mapped[str] = mapped_column(ForeignKey("users.id", ondelete="RESTRICT"), nullable=False)
    source_class: Mapped[SensorSourceClass] = mapped_column(Enum(SensorSourceClass, native_enum=False, create_constraint=True), nullable=False, default=SensorSourceClass.SIMULATION)
    configuration_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))

    created_by = relationship("User")