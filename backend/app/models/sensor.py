"""Operational sensor registration model."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class SensorSourceClass(StrEnum):
    REAL = "REAL"
    SIMULATION = "SIMULATION"
    REPLAY = "REPLAY"


class SensorStatus(StrEnum):
    REGISTERED = "REGISTERED"
    ACTIVE = "ACTIVE"
    DEGRADED = "DEGRADED"
    OFFLINE = "OFFLINE"
    DISABLED = "DISABLED"


class Sensor(Base):
    __tablename__ = "sensors"
    __table_args__ = (
        CheckConstraint("length(name) between 1 and 200", name="ck_sensors_name_length"),
        CheckConstraint("length(source_type) between 1 and 64", name="ck_sensors_source_type_length"),
        Index("ix_sensors_status", "status"),
        Index("ix_sensors_source_type", "source_type"),
        Index("ix_sensors_updated_at", "updated_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    source_class: Mapped[SensorSourceClass] = mapped_column(Enum(SensorSourceClass, native_enum=False, create_constraint=True), nullable=False)
    status: Mapped[SensorStatus] = mapped_column(Enum(SensorStatus, native_enum=False, create_constraint=True), nullable=False, default=SensorStatus.REGISTERED)
    configuration_version: Mapped[int] = mapped_column(nullable=False, default=1)
    configuration_metadata: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))

    detections = relationship("Detection", back_populates="sensor")
    alerts = relationship("Alert", back_populates="sensor")