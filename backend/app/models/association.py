"""Operational track association model."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class TrackAssociationDecision(StrEnum):
    ASSOCIATED = "ASSOCIATED"
    NEW_TRACK = "NEW_TRACK"
    NO_CANDIDATE = "NO_CANDIDATE"
    GATE_REJECTED = "GATE_REJECTED"
    STALE_DETECTION = "STALE_DETECTION"
    CLOSED_TRACK = "CLOSED_TRACK"
    DUPLICATE = "DUPLICATE"


class TrackAssociation(Base):
    __tablename__ = "track_associations"
    __table_args__ = (
        UniqueConstraint("detection_id", name="uq_track_associations_detection_id"),
        CheckConstraint("score is null or (score >= 0 and score <= 1)", name="ck_track_associations_score"),
        CheckConstraint("distance_meters is null or distance_meters >= 0", name="ck_track_associations_distance"),
        CheckConstraint("vertical_distance_meters is null or vertical_distance_meters >= 0", name="ck_track_associations_vertical_distance"),
        CheckConstraint("time_delta_seconds is null or time_delta_seconds >= 0", name="ck_track_associations_time_delta"),
        Index("ix_track_associations_track_timestamp", "track_id", "timestamp"),
        Index("ix_track_associations_sensor_timestamp", "sensor_id", "timestamp"),
        Index("ix_track_associations_decision_timestamp", "decision", "timestamp"),
        Index("ix_track_associations_detection_id", "detection_id"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    detection_id: Mapped[str] = mapped_column(ForeignKey("detections.id", ondelete="CASCADE"), nullable=False, unique=True)
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    sensor_id: Mapped[str] = mapped_column(ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    distance_meters: Mapped[float | None] = mapped_column(nullable=True)
    vertical_distance_meters: Mapped[float | None] = mapped_column(nullable=True)
    time_delta_seconds: Mapped[float | None] = mapped_column(nullable=True)
    score: Mapped[float | None] = mapped_column(nullable=True)
    decision: Mapped[TrackAssociationDecision] = mapped_column(
        Enum(TrackAssociationDecision, native_enum=False, create_constraint=True),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    gate_result: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )

    detection = relationship("Detection")
    track = relationship("Track", back_populates="associations")
    sensor = relationship("Sensor")


@event.listens_for(TrackAssociation, "before_update")
@event.listens_for(TrackAssociation, "before_delete")
def reject_association_mutation(mapper, connection, target: TrackAssociation) -> None:
    raise ValueError("Track associations are immutable")
