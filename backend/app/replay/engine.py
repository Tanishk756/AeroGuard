"""Deterministic read-only historical replay engine."""

from datetime import UTC, datetime, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.history.queries import (
    get_track_state_at,
    normalize_timestamp,
    query_historical_alerts,
    query_historical_detections,
    query_historical_threats,
)
from app.models.alert import Alert, AlertStatus
from app.models.detection import Detection
from app.models.threat import ThreatAssessment
from app.models.track import Track, TrackHistory, TrackState
from app.replay.models import ReplayConfig
from app.schemas.history import (
    HistoricalAlertItem,
    HistoricalDetectionItem,
    HistoricalThreatItem,
)
from app.schemas.replay import (
    ReplayFilter,
    ReplaySnapshot,
    ReplayTrackState,
)


class ReplayEngine:
    """Stateless/step-based historical state reconstructor."""

    def __init__(self, db: Session, config: ReplayConfig):
        self.db = db
        self.config = config
        self.start_time = normalize_timestamp(config.start_time)
        self.end_time = normalize_timestamp(config.end_time)
        self.dt = timedelta(seconds=config.step_interval_seconds)
        self.filters = config.filters

        self.step_index = 0
        self.current_time = self.start_time

    def reset(self) -> None:
        self.step_index = 0
        self.current_time = self.start_time

    def step(self, steps: int = 1) -> ReplaySnapshot:
        """Advance replay clock by N steps and generate snapshot."""
        if steps < 1:
            raise ValueError("steps must be at least 1")

        self.step_index += steps
        self.current_time = self.start_time + (self.step_index * self.dt)
        if self.current_time > self.end_time:
            self.current_time = self.end_time

        return self.get_snapshot_at(self.current_time, self.step_index)

    def get_snapshot_at(self, as_of_time: datetime, step_idx: int = 0) -> ReplaySnapshot:
        """Reconstruct operational snapshot at specific virtual timestamp."""
        norm_time = normalize_timestamp(as_of_time)
        is_complete = norm_time >= self.end_time

        # 1. Active Tracks reconstruction
        active_tracks: list[ReplayTrackState] = []
        track_stmt = select(Track).where(Track.first_seen_at <= norm_time)
        if self.filters.track_ids:
            track_stmt = track_stmt.where(Track.id.in_(self.filters.track_ids))
        if self.filters.classifications:
            track_stmt = track_stmt.where(Track.classification.in_(self.filters.classifications))

        candidate_tracks = self.db.scalars(track_stmt).all()
        for track in candidate_tracks:
            latest_point = get_track_state_at(self.db, track.id, norm_time)
            if latest_point is None:
                continue

            # If the track was archived before or at this time, check if it is still considered active
            if latest_point.state in (TrackState.ARCHIVED, TrackState.LOST):
                # Don't show inactive tracks in active_tracks list
                continue

            active_tracks.append(
                ReplayTrackState(
                    track_id=track.id,
                    state=latest_point.state,
                    latitude=latest_point.latitude,
                    longitude=latest_point.longitude,
                    altitude=latest_point.altitude,
                    velocity=latest_point.velocity,
                    heading=latest_point.heading,
                    confidence=latest_point.confidence,
                    classification=track.classification,
                    source_count=track.source_count,
                )
            )

        # Deterministic sorting for active tracks
        active_tracks.sort(key=lambda t: t.track_id)

        # 2. Recent Detections (in window [as_of_time - dt, as_of_time])
        window_start = norm_time - self.dt
        dets, _ = query_historical_detections(
            self.db,
            start_time=window_start,
            end_time=norm_time,
            limit=100,
        )
        recent_detections = []
        for d in dets:
            if self.filters.sensor_ids and d.sensor_id not in self.filters.sensor_ids:
                continue
            if self.filters.track_ids and d.track_id not in self.filters.track_ids:
                continue
            recent_detections.append(
                HistoricalDetectionItem(
                    id=d.id,
                    sensor_id=d.sensor_id,
                    source_detection_id=d.source_detection_id,
                    timestamp=d.timestamp.replace(tzinfo=UTC),
                    latitude=d.latitude,
                    longitude=d.longitude,
                    altitude=d.altitude,
                    velocity=d.velocity,
                    heading=d.heading,
                    confidence=d.confidence,
                    horizontal_uncertainty=d.horizontal_uncertainty,
                    vertical_uncertainty=d.vertical_uncertainty,
                    classification=d.classification,
                    source_class=d.source_class,
                    source_type=d.source_type,
                    track_id=d.track_id,
                )
            )

        # 3. Active Alerts at as_of_time
        alert_stmt = select(Alert).where(
            Alert.created_at <= norm_time,
            (Alert.resolved_at.is_(None)) | (Alert.resolved_at > norm_time),
        )
        if self.filters.track_ids:
            alert_stmt = alert_stmt.where(Alert.track_id.in_(self.filters.track_ids))
        if self.filters.sensor_ids:
            alert_stmt = alert_stmt.where(Alert.sensor_id.in_(self.filters.sensor_ids))

        active_alerts_orm = self.db.scalars(alert_stmt.order_by(Alert.created_at.asc(), Alert.id.asc())).all()
        active_alerts = [
            HistoricalAlertItem(
                id=a.id,
                type=a.type,
                severity=a.severity,
                status=a.status,
                track_id=a.track_id,
                sensor_id=a.sensor_id,
                reason=a.reason,
                metadata_json=a.metadata_json,
                created_at=a.created_at.replace(tzinfo=UTC),
                updated_at=a.updated_at.replace(tzinfo=UTC),
                resolved_at=a.resolved_at.replace(tzinfo=UTC) if a.resolved_at else None,
            )
            for a in active_alerts_orm
        ]

        # 4. Current Threat Assessments for active tracks
        active_threats: list[HistoricalThreatItem] = []
        if active_tracks:
            active_track_ids = [t.track_id for t in active_tracks]
            threat_stmt = select(ThreatAssessment).where(
                ThreatAssessment.track_id.in_(active_track_ids),
                ThreatAssessment.updated_at <= norm_time,
            )
            threats_orm = self.db.scalars(
                threat_stmt.order_by(ThreatAssessment.updated_at.asc(), ThreatAssessment.id.asc())
            ).all()
            active_threats = [
                HistoricalThreatItem(
                    id=th.id,
                    track_id=th.track_id,
                    score=th.score,
                    level=th.level,
                    factors=th.factors,
                    created_at=th.created_at.replace(tzinfo=UTC),
                    updated_at=th.updated_at.replace(tzinfo=UTC),
                )
                for th in threats_orm
            ]

        metrics = {
            "active_tracks_count": len(active_tracks),
            "recent_detections_count": len(recent_detections),
            "active_alerts_count": len(active_alerts),
            "active_threats_count": len(active_threats),
        }

        return ReplaySnapshot(
            replay_time=norm_time.replace(tzinfo=UTC),
            step_index=step_idx,
            is_complete=is_complete,
            active_tracks=active_tracks,
            recent_detections=recent_detections,
            active_alerts=active_alerts,
            active_threats=active_threats,
            metrics=metrics,
        )
