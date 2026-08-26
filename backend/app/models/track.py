"""Operational track and append-only history models."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, Index, JSON, String, UniqueConstraint, event
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.sensor import SensorSourceClass


class TrackState(StrEnum):
    NEW = "NEW"
    ACTIVE = "ACTIVE"
    STALE = "STALE"
    LOST = "LOST"
    ARCHIVED = "ARCHIVED"


class Track(Base):
    __tablename__ = "tracks"
    __table_args__ = (
        CheckConstraint("latitude between -90 and 90", name="ck_tracks_latitude"),
        CheckConstraint("longitude between -180 and 180", name="ck_tracks_longitude"),
        CheckConstraint("heading is null or heading >= 0 and heading < 360", name="ck_tracks_heading"),
        CheckConstraint("velocity is null or velocity >= 0", name="ck_tracks_velocity"),
        CheckConstraint("confidence between 0 and 1", name="ck_tracks_confidence"),
        Index("ix_tracks_state", "state"),
        Index("ix_tracks_last_seen_at", "last_seen_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    state: Mapped[TrackState] = mapped_column(Enum(TrackState, native_enum=False, create_constraint=True), nullable=False, default=TrackState.NEW)
    first_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    altitude: Mapped[float | None] = mapped_column(nullable=True)
    velocity: Mapped[float | None] = mapped_column(nullable=True)
    heading: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False)
    classification: Mapped[str | None] = mapped_column(String(64), nullable=True)
    source_count: Mapped[int] = mapped_column(nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))

    detections = relationship("Detection", back_populates="track")
    history = relationship("TrackHistory", back_populates="track", cascade="all, delete-orphan")
    associations = relationship("TrackAssociation", back_populates="track", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="track")
    threat_assessments = relationship("ThreatAssessment", back_populates="track", cascade="all, delete-orphan")


class TrackHistory(Base):
    __tablename__ = "track_history"
    __table_args__ = (
        UniqueConstraint("track_id", "sequence", name="uq_track_history_track_sequence"),
        CheckConstraint("latitude between -90 and 90", name="ck_track_history_latitude"),
        CheckConstraint("longitude between -180 and 180", name="ck_track_history_longitude"),
        CheckConstraint("sequence >= 0", name="ck_track_history_sequence"),
        CheckConstraint("heading is null or heading >= 0 and heading < 360", name="ck_track_history_heading"),
        CheckConstraint("velocity is null or velocity >= 0", name="ck_track_history_velocity"),
        CheckConstraint("confidence between 0 and 1", name="ck_track_history_confidence"),
        Index("ix_track_history_track_timestamp", "track_id", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    latitude: Mapped[float] = mapped_column(nullable=False)
    longitude: Mapped[float] = mapped_column(nullable=False)
    altitude: Mapped[float | None] = mapped_column(nullable=True)
    velocity: Mapped[float | None] = mapped_column(nullable=True)
    heading: Mapped[float | None] = mapped_column(nullable=True)
    confidence: Mapped[float] = mapped_column(nullable=False)
    state: Mapped[TrackState] = mapped_column(Enum(TrackState, native_enum=False, create_constraint=True), nullable=False)
    provenance: Mapped[SensorSourceClass] = mapped_column(Enum(SensorSourceClass, native_enum=False, create_constraint=True), nullable=False)
    source_detection_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))

    track = relationship("Track", back_populates="history")


@event.listens_for(TrackHistory, "before_update")
@event.listens_for(TrackHistory, "before_delete")
def reject_history_mutation(mapper, connection, target: TrackHistory) -> None:
    raise ValueError("Track history is immutable")