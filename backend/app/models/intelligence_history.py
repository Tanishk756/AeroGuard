"""Historical defensive intelligence models for append-only replay and analytical time-series."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class IntelligenceSnapshot(Base):
    """Periodic or event-triggered full defensive multi-track intelligence snapshot."""

    __tablename__ = "intelligence_snapshots"
    __table_args__ = (
        CheckConstraint("active_track_count >= 0", name="ck_intelligence_snapshots_active_tracks"),
        CheckConstraint("group_count >= 0", name="ck_intelligence_snapshots_groups"),
        CheckConstraint("formation_count >= 0", name="ck_intelligence_snapshots_formations"),
        CheckConstraint("peak_threat_score >= 0 and peak_threat_score <= 100", name="ck_intelligence_snapshots_peak_score"),
        Index("ix_intelligence_snapshots_timestamp", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    active_track_count: Mapped[int] = mapped_column(nullable=False, default=0)
    group_count: Mapped[int] = mapped_column(nullable=False, default=0)
    formation_count: Mapped[int] = mapped_column(nullable=False, default=0)
    peak_threat_score: Mapped[float] = mapped_column(nullable=False, default=0.0)
    summary_json: Mapped[dict] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )


class TrackGroupHistory(Base):
    """Historical record of multi-track correlation group lifecycle states and centroids."""

    __tablename__ = "track_group_history"
    __table_args__ = (
        CheckConstraint("member_count >= 0", name="ck_track_group_history_member_count"),
        CheckConstraint("centroid_lat between -90 and 90", name="ck_track_group_history_centroid_lat"),
        CheckConstraint("centroid_lon between -180 and 180", name="ck_track_group_history_centroid_lon"),
        CheckConstraint("radius_meters >= 0", name="ck_track_group_history_radius"),
        Index("ix_track_group_history_timestamp_group", "timestamp", "group_id"),
        Index("ix_track_group_history_group_id", "group_id"),
        Index("ix_track_group_history_timestamp", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    member_track_ids: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    member_count: Mapped[int] = mapped_column(nullable=False, default=0)
    centroid_lat: Mapped[float] = mapped_column(nullable=False)
    centroid_lon: Mapped[float] = mapped_column(nullable=False)
    radius_meters: Mapped[float] = mapped_column(nullable=False, default=0.0)
    behavioral_state: Mapped[str] = mapped_column(String(32), nullable=False)
    coordination_index: Mapped[float | None] = mapped_column(nullable=True)
    formation_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )


class BehaviorEventHistory(Base):
    """Historical log of track behavioral classification state transitions."""

    __tablename__ = "behavior_event_history"
    __table_args__ = (
        CheckConstraint("duration_seconds >= 0", name="ck_behavior_event_history_duration"),
        CheckConstraint("confidence between 0 and 1", name="ck_behavior_event_history_confidence"),
        Index("ix_behavior_event_history_timestamp_track", "timestamp", "track_id"),
        Index("ix_behavior_event_history_track_id", "track_id"),
        Index("ix_behavior_event_history_timestamp", "timestamp"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    track_id: Mapped[str] = mapped_column(String(36), nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    previous_state: Mapped[str | None] = mapped_column(String(32), nullable=True)
    new_state: Mapped[str] = mapped_column(String(32), nullable=False)
    duration_seconds: Mapped[float] = mapped_column(nullable=False, default=0.0)
    confidence: Mapped[float] = mapped_column(nullable=False, default=1.0)
    reasons: Mapped[list] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        default=lambda: datetime.now(UTC).replace(tzinfo=None),
    )
