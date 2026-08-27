"""Defensive intelligence orchestration service."""

from datetime import UTC, datetime
import logging
from typing import Any, Sequence
from sqlalchemy import desc, select
from sqlalchemy.orm import Session

from ai.anomaly.scoring import evaluate_anomaly
from ai.behavior.classifier import (
    ClassifierInput,
    classify_track_behavior,
    classifier_input_from_ai1,
)
from ai.confidence.sensor import compute_sensor_confidence
from ai.correlation.coordination import compute_coordination_index
from ai.correlation.grouping import correlate_tracks, to_track_observation
from ai.features.kinematics import extract_kinematic_features
from ai.priority.scoring import evaluate_threat_priority
from ai.schemas import (
    BehaviorClassification,
    CoordinatedFormation,
    DefensiveIntelligenceSummary,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    TrackGroup,
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
    behavioral classification, and threat prioritization for operational tracks.
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

            # 7. Evaluate Behavioral State
            classifier_inp = classifier_input_from_ai1(
                track_id=track.id,
                features=features,
                anomaly_assessment=anomaly,
                ingress_estimates=ingress_estimates,
                timestamp=current_time,
            )
            behavior_classification, _ = classify_track_behavior(classifier_inp)

            # 8. Evaluate Defensive Threat Priority (AI2-E)
            priority = evaluate_threat_priority(
                track_id=track.id,
                group_id=getattr(track, "group_id", None),
                ingress_estimates=ingress_estimates,
                behavior=behavior_classification,
                persistent_anomaly=anomaly.anomaly_score,
                coordination=None,
                kinematics=features,
                sensor_confidence=sensor_conf,
                evaluated_at=datetime.now(UTC),
            )

            summary = DefensiveIntelligenceSummary(
                track_id=track.id,
                features=features,
                anomaly=anomaly,
                trajectory=trajectory,
                ingress_estimates=ingress_estimates,
                priority=priority,
                evaluated_at=datetime.now(UTC),
            )

            # 9. Publish realtime events if requested
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

    @staticmethod
    def evaluate_multi_track_intelligence(
        tracks: Sequence[Any],
        geofences: list[Any] | None = None,
        now: datetime | None = None,
    ) -> MultiTrackIntelligenceSummary:
        """Evaluate multi-track correlation, behavioral state, coordination, and priorities across all active tracks."""
        eval_ts = now or datetime.now(UTC)

        # Normalize all track inputs (handles dicts, ORM models, domain objects)
        normalized_tracks = [to_track_observation(t) for t in tracks]

        # 1. AI2-B Grouping
        groups = correlate_tracks(normalized_tracks, now=eval_ts)

        # Map track_id to its group if any
        track_to_group: dict[str, TrackGroup] = {}
        for g in groups:
            for mid in g.member_track_ids:
                track_to_group[mid] = g

        # 2. AI2-D Formations & Coordination
        formations: list[CoordinatedFormation] = []
        track_to_formation: dict[str, CoordinatedFormation] = {}
        for g in groups:
            member_objs = [
                t for t in normalized_tracks
                if t.id in g.member_track_ids
            ]
            formation = compute_coordination_index(g, member_objs, evaluated_at=eval_ts)
            if formation is not None:
                formations.append(formation)
                for mid in formation.member_track_ids:
                    track_to_formation[mid] = formation

        # 3. AI2-C Behaviors and AI2-E Priorities per track
        behaviors: list[BehaviorClassification] = []
        priorities: list[ThreatPriorityAssessment] = []

        for t in normalized_tracks:
            tid = t.id
            grp = track_to_group.get(tid)
            fmt = track_to_formation.get(tid)

            spd = float(t.velocity or 0.0)
            hdg = float(t.heading) if t.heading is not None else None

            clf_inp = ClassifierInput(
                track_id=tid,
                speed_mps=spd,
                heading_deg=hdg,
                group_id=grp.group_id if grp else None,
                group_member_count=grp.member_count if grp else None,
                timestamp=eval_ts,
            )
            b_class, _ = classify_track_behavior(clf_inp)
            behaviors.append(b_class)

            conf = float(t.confidence)

            # Priority evaluation combining all signals
            p_assess = evaluate_threat_priority(
                track_id=tid,
                group_id=grp.group_id if grp else None,
                behavior=b_class,
                coordination=fmt,
                kinematics=spd,
                sensor_confidence=conf,
                evaluated_at=eval_ts,
            )
            priorities.append(p_assess)

        return MultiTrackIntelligenceSummary(
            groups=groups,
            behaviors=behaviors,
            formations=formations,
            priorities=priorities,
            evaluated_at=eval_ts,
        )
