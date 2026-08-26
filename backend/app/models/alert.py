"""Operational alert model."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class AlertType(StrEnum):
    TRACK_DETECTED = "TRACK_DETECTED"
    TRACK_LOST = "TRACK_LOST"
    UNKNOWN_TRACK = "UNKNOWN_TRACK"
    GEOFENCE_BREACH = "GEOFENCE_BREACH"
    SENSOR_OFFLINE = "SENSOR_OFFLINE"
    SENSOR_DEGRADED = "SENSOR_DEGRADED"
    DATA_QUALITY_LOW = "DATA_QUALITY_LOW"


class AlertSeverity(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class AlertStatus(StrEnum):
    OPEN = "OPEN"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    RESOLVED = "RESOLVED"


class Alert(Base):
    __tablename__ = "alerts"
    __table_args__ = (
        Index("ix_alerts_status_created_at", "status", "created_at"),
        Index("ix_alerts_track_id", "track_id"),
        Index("ix_alerts_sensor_id", "sensor_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    type: Mapped[AlertType] = mapped_column(Enum(AlertType, native_enum=False, create_constraint=True), nullable=False)
    severity: Mapped[AlertSeverity] = mapped_column(Enum(AlertSeverity, native_enum=False, create_constraint=True), nullable=False)
    status: Mapped[AlertStatus] = mapped_column(Enum(AlertStatus, native_enum=False, create_constraint=True), nullable=False, default=AlertStatus.OPEN)
    track_id: Mapped[str | None] = mapped_column(ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True)
    sensor_id: Mapped[str | None] = mapped_column(ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    track = relationship("Track", back_populates="alerts")
    sensor = relationship("Sensor", back_populates="alerts")


def _get_metadata(alert: Alert) -> dict:
    return alert.metadata_json


def _set_metadata(alert: Alert, value: dict) -> None:
    alert.metadata_json = value


Alert.metadata = property(_get_metadata, _set_metadata)