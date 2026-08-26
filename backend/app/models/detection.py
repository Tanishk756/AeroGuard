"""Validated operational detection model."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, JSON, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.sensor import SensorSourceClass


class Detection(Base):
    __tablename__ = "detections"
    __table_args__ = (
        UniqueConstraint("sensor_id", "source_detection_id", name="uq_detections_sensor_source_id"),
        CheckConstraint("latitude between -90 and 90", name="ck_detections_latitude"),
        CheckConstraint("longitude between -180 and 180", name="ck_detections_longitude"),
        CheckConstraint("heading is null or heading >= 0 and heading < 360", name="ck_detections_heading"),
        CheckConstraint("velocity is null or velocity >= 0", name="ck_detections_velocity"),
        CheckConstraint("confidence between 0 and 1", name="ck_detections_confidence"),
        CheckConstraint("horizontal_uncertainty is null or horizontal_uncertainty >= 0", name="ck_detections_horizontal_uncertainty"),
        CheckConstraint("vertical_uncertainty is null or vertical_uncertainty >= 0", name="ck_detections_vertical_uncertainty"),
        Index("ix_detections_timestamp", "timestamp"),
        Index("ix_detections_sensor_timestamp", "sensor_id", "timestamp"),
        Index("ix_detections_track_id", "track_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False)
    source_detection_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    altitude: Mapped[float | None] = mapped_column(nullable=True)
    velocity: Mapped[float | None] = mapped_column(nullable=True)
    heading: Mapped[float | None] = mapped_column(nullable=True)
    horizontal_uncertainty: Mapped[float | None] = mapped_column(nullable=True)
    vertical_uncertainty: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False)
    classification: Mapped[str | None] = mapped_column(String(64), nullable=True)
    quality: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_class: Mapped[SensorSourceClass] = mapped_column(Enum(SensorSourceClass, native_enum=False, create_constraint=True), nullable=False)
    source_type: Mapped[str] = mapped_column(String(64), nullable=False)
    track_id: Mapped[str | None] = mapped_column(ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    sensor = relationship("Sensor", back_populates="detections")
    track = relationship("Track", back_populates="detections")


def _get_metadata(detection: Detection) -> dict:
    return detection.metadata_json


def _set_metadata(detection: Detection, value: dict) -> None:
    detection.metadata_json = value


Detection.metadata = property(_get_metadata, _set_metadata)


@event.listens_for(Detection, "before_update")
@event.listens_for(Detection, "before_delete")
def reject_detection_mutation(mapper, connection, target: Detection) -> None:
    raise ValueError("Detections are immutable")