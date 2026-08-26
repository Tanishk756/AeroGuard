"""Track lifecycle management and state transitions."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.sensor import SensorSourceClass
from app.models.track import Track, TrackHistory, TrackState


@dataclass(frozen=True)
class LifecycleConfig:
    confirmation_count: int = 3
    confirmation_window_seconds: float = 30.0
    coast_timeout_seconds: float = 10.0
    lost_timeout_seconds: float = 60.0
    archive_delay_seconds: float = 86400.0  # 24 hours
    late_detection_window_seconds: float = 300.0  # 5 minutes


@dataclass(frozen=True)
class TrackStateTransition:
    track_id: str
    from_state: TrackState
    to_state: TrackState
    timestamp: datetime
    last_seen_at: datetime


class TrackLifecycleService:
    def __init__(self, db: Session, config: LifecycleConfig | None = None):
        self.db = db
        self.config = config or LifecycleConfig()

    def advance(self, now: datetime | None = None) -> list[TrackStateTransition]:
        if now is None:
            now = datetime.now(UTC).replace(tzinfo=None)
        elif now.tzinfo is not None:
            now = now.astimezone(UTC).replace(tzinfo=None)

        transitions: list[TrackStateTransition] = []

        # 1. ACTIVE -> STALE (coast timeout)
        stale_cutoff = now - timedelta(seconds=self.config.coast_timeout_seconds)
        active_tracks = self.db.scalars(
            select(Track)
            .where(Track.state == TrackState.ACTIVE, Track.last_seen_at < stale_cutoff)
            .order_by(Track.last_seen_at.asc(), Track.id.asc())
        ).all()

        for track in active_tracks:
            transition = self._transition_track(track, TrackState.STALE, now)
            transitions.append(transition)

        # 2. STALE -> LOST (lost timeout)
        lost_cutoff = now - timedelta(seconds=self.config.lost_timeout_seconds)
        stale_tracks = self.db.scalars(
            select(Track)
            .where(Track.state == TrackState.STALE, Track.last_seen_at < lost_cutoff)
            .order_by(Track.last_seen_at.asc(), Track.id.asc())
        ).all()

        for track in stale_tracks:
            transition = self._transition_track(track, TrackState.LOST, now)
            transitions.append(transition)

        # 3. LOST -> ARCHIVED (archive delay)
        archive_cutoff = now - timedelta(seconds=self.config.archive_delay_seconds)
        lost_tracks = self.db.scalars(
            select(Track)
            .where(Track.state == TrackState.LOST, Track.last_seen_at < archive_cutoff)
            .order_by(Track.last_seen_at.asc(), Track.id.asc())
        ).all()

        for track in lost_tracks:
            transition = self._transition_track(track, TrackState.ARCHIVED, now)
            transitions.append(transition)

        if transitions:
            try:
                self.db.commit()
            except Exception:
                self.db.rollback()
                raise

        return transitions

    def _transition_track(
        self, track: Track, new_state: TrackState, now: datetime
    ) -> TrackStateTransition:
        old_state = track.state
        track.state = new_state
        track.updated_at = now

        seq = (
            self.db.scalar(
                select(func.max(TrackHistory.sequence)).where(
                    TrackHistory.track_id == track.id
                )
            )
            or 0
        ) + 1

        last_provenance = (
            self.db.scalar(
                select(TrackHistory.provenance)
                .where(TrackHistory.track_id == track.id)
                .order_by(TrackHistory.sequence.desc())
                .limit(1)
            )
            or SensorSourceClass.REAL
        )

        history_entry = TrackHistory(
            track_id=track.id,
            sequence=seq,
            timestamp=now,
            latitude=track.latitude,
            longitude=track.longitude,
            altitude=track.altitude,
            velocity=track.velocity,
            heading=track.heading,
            confidence=track.confidence,
            state=new_state,
            provenance=last_provenance,
            source_detection_ids=[],
            created_at=now,
        )
        self.db.add(history_entry)

        return TrackStateTransition(
            track_id=track.id,
            from_state=old_state,
            to_state=new_state,
            timestamp=now,
            last_seen_at=track.last_seen_at,
        )
