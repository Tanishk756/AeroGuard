"""Defensive intelligence orchestration service."""

from datetime import UTC, datetime
import logging
from typing import Any
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ai.anomaly.scoring import evaluate_anomaly
from ai.confidence.sensor import compute_sensor_confidence
from ai.features.kinematics import extract_kinematic_features
from ai.schemas import (
    DefensiveIntelligenceSummary,
    TrackPoint,
)
from ai.trajectory.predictor import estimate_geofence_ingress, predict_trajectory
from app.core.events import get_event_bus
from app.models.geofence import Geofence
from app.models.track import Track, TrackHistory
from app.schemas.events import RealtimeChannel, RealtimeEventType

logger = logging.getLogger(__name__)


class DefensiveIntelligenceService:
    """Orchestrates kinematic feature extraction, anomaly evaluation, trajectory prediction,

    and perimeter ingress estimation for operational tracks.
    """

    @staticmethod
    def evaluate_track(
        db: Session,
        track: Track,
        geofences: list[Any] | None = None,
        publish_events: bool = True,
    ) -> DefensiveIntelligenceSummary | None:
        """Evaluate defensive intelligence for an active track and optionally publish realtime events."""
        try:
            # 1. Fetch recent history points (up to 30 points ordered chronologically)
            history_stmt = (
                select(TrackHistory)
                .where(TrackHistory.track_id == track.id)
                .order_by(desc(TrackHistory.sequence))
                .limit(30)
            )
            history_rows = list(db.scalars(history_stmt).all())
            history_rows.reverse()

            points: list[TrackPoint] = []
            for h in history_rows:
                points.append(
                    TrackPoint(
                        timestamp=h.timestamp if h.timestamp.tzinfo else h.timestamp.replace(tzinfo=UTC),
                        latitude=h.latitude,
                        longitude=h.longitude,
                        altitude=h.altitude,
                        velocity=h.velocity,
                        heading=h.heading,
                        confidence=h.confidence,
                    )
                )

            # Ensure latest track point is included
            current_time = track.last_seen_at if track.last_seen_at.tzinfo else track.last_seen_at.replace(tzinfo=UTC)
            if not points or points[-1].timestamp < current_time:
                points.append(
                    TrackPoint(
                        timestamp=current_time,
                        latitude=track.latitude,
                        longitude=track.longitude,
                        altitude=track.altitude,
                        velocity=track.velocity,
                        heading=track.heading,
                        confidence=track.confidence,
                    )
                )

            # 2. Extract kinematic features
            features = extract_kinematic_features(points)

            # 3. Compute sensor confidence
            sensor_prov = history_rows[-1].provenance.value if (history_rows and hasattr(history_rows[-1], 'provenance') and history_rows[-1].provenance) else None
            sensor_conf = compute_sensor_confidence(
                provenance=sensor_prov,
                source_count=track.source_count,
                last_seen_at=track.last_seen_at,
                now=current_time,
                track_confidence=track.confidence,
                sample_count=len(points),
                speed_variance=features.speed_variance,
            )

            # 4. Evaluate anomaly
            anomaly = evaluate_anomaly(
                track_id=track.id,
                features=features,
                sensor_confidence=sensor_conf,
            )

            # 5. Predict trajectory (60s horizon)
            trajectory = predict_trajectory(
                track_id=track.id,
                current_lat=track.latitude,
                current_lon=track.longitude,
                current_alt=track.altitude,
                speed_mps=features.speed_mps,
                heading_deg=features.heading_deg,
                acceleration_mps2=features.acceleration_mps2,
                vertical_speed_mps=features.vertical_speed_mps,
                turn_rate_dps=features.turn_rate_dps,
                horizon_seconds=60.0,
                step_interval_seconds=5.0,
                start_time=current_time,
            )

            # 6. Estimate geofence ingress
            if geofences is None:
                geofence_stmt = select(Geofence).where(Geofence.enabled == True)
                geofences = list(db.scalars(geofence_stmt).all())

            ingress_estimates = estimate_geofence_ingress(
                track_id=track.id,
                trajectory=trajectory,
                geofences=geofences,
                current_lat=track.latitude,
                current_lon=track.longitude,
                current_alt=track.altitude,
            )

            summary = DefensiveIntelligenceSummary(
                track_id=track.id,
                features=features,
                anomaly=anomaly,
                trajectory=trajectory,
                ingress_estimates=ingress_estimates,
                evaluated_at=datetime.now(UTC),
            )

            # 7. Publish realtime events if requested
            if publish_events:
                has_breach_risk = any(e.status in ("APPROACHING", "INSIDE") for e in ingress_estimates)
                if anomaly.anomaly_score >= 30.0 or has_breach_risk or len(points) <= 2:
                    get_event_bus().publish(
                        event_type=RealtimeEventType.AI_SUMMARY,
                        channel=RealtimeChannel.OPERATIONAL,
                        payload=summary.model_dump(mode="json"),
                        resource_type="track_intelligence",
                        resource_id=track.id,
                    )

            return summary
        except Exception as err:
            logger.warning(
                f"[DefensiveAI] Failed to evaluate intelligence for track {getattr(track, 'id', 'unknown')}: {err}"
            )
            return None
