"""Tracking service orchestrating candidate generation, gating, scoring, assignment, and persistence."""

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import Sequence

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.alerts.rules import (
    evaluate_data_quality_alert,
    evaluate_detection_alert,
    evaluate_geofence_breach_alerts,
)
from app.alerts.service import AlertService
from app.fusion.classification import reconcile_classification
from app.fusion.consensus import fuse_kinematics
from app.fusion.quality import compute_track_quality
from app.models.association import TrackAssociation, TrackAssociationDecision
from app.models.detection import Detection
from app.models.track import Track, TrackHistory, TrackState
from app.threats.service import ThreatAssessmentService
from app.tracking.association import (
    AssociationDecision,
    generate_track_id,
)
from app.tracking.events import DetectionAssociated
from app.tracking.gating import AssociationGate, GateResult, GatingConfig
from app.tracking.lifecycle import LifecycleConfig
from app.tracking.scoring import AssociationScorer, ScoreResult, ScoringConfig


@dataclass(frozen=True)
class TrackingResult:
    decision: AssociationDecision
    event: DetectionAssociated
    track: Track


class DetectionCandidateProvider:
    def __init__(self, db: Session, window_seconds: float = 300.0):
        self.db = db
        self.window_seconds = window_seconds

    def get_candidates(self, detection: Detection) -> list[Track]:
        """Query candidate tracks in NEW, ACTIVE, or STALE states within temporal window."""
        window = timedelta(seconds=self.window_seconds)
        statement = (
            select(Track)
            .where(
                Track.state.in_([TrackState.NEW, TrackState.ACTIVE, TrackState.STALE]),
                Track.last_seen_at >= detection.timestamp - window,
                Track.last_seen_at <= detection.timestamp + window,
            )
            .order_by(Track.last_seen_at.desc(), Track.id.asc())
        )
        return list(self.db.scalars(statement).all())


class TrackingService:
    def __init__(
        self,
        db: Session,
        gating_config: GatingConfig | None = None,
        scoring_config: ScoringConfig | None = None,
        lifecycle_config: LifecycleConfig | None = None,
        candidate_provider: DetectionCandidateProvider | None = None,
    ):
        self.db = db
        self.gating_config = gating_config or GatingConfig()
        self.scoring_config = scoring_config or ScoringConfig()
        self.lifecycle_config = lifecycle_config or LifecycleConfig()
        self.gate = AssociationGate(self.gating_config)
        self.scorer = AssociationScorer(self.scoring_config, self.gating_config)
        self.candidate_provider = candidate_provider or DetectionCandidateProvider(
            db, window_seconds=self.lifecycle_config.late_detection_window_seconds
        )
        self.threat_service = ThreatAssessmentService(db)
        self.alert_service = AlertService(db)

    def process_detection(self, detection: Detection) -> TrackingResult:
        """Process a single persisted detection through gating, scoring, assignment, and persistence."""
        # 1. Idempotency check for existing association
        existing_assoc = self.db.scalar(
            select(TrackAssociation).where(
                TrackAssociation.detection_id == detection.id
            )
        )
        if existing_assoc is not None:
            track = self.db.get(Track, existing_assoc.track_id)
            decision = AssociationDecision(
                detection_id=detection.id,
                track_id=existing_assoc.track_id,
                decision=TrackAssociationDecision.DUPLICATE,
                gate_result=existing_assoc.gate_result,
                horizontal_distance=existing_assoc.distance_meters,
                vertical_distance=existing_assoc.vertical_distance_meters,
                time_delta=existing_assoc.time_delta_seconds,
                score=existing_assoc.score,
                reason="Detection already associated",
                candidate_count=0,
            )
            event = DetectionAssociated(
                detection_id=detection.id,
                track_id=existing_assoc.track_id,
                timestamp=existing_assoc.timestamp,
                score=existing_assoc.score,
                decision=TrackAssociationDecision.DUPLICATE.value,
            )
            return TrackingResult(decision=decision, event=event, track=track)

        now = datetime.now(UTC).replace(tzinfo=None)

        # 2. Acquire candidates
        candidates = self.candidate_provider.get_candidates(detection)
        candidate_count = len(candidates)

        # 3. Evaluate candidates with gating and scoring
        evaluated_candidates: list[tuple[Track, GateResult, ScoreResult]] = []
        gate_rejection_reasons: list[str] = []

        for cand in candidates:
            gate_res = self.gate.evaluate(detection, cand)
            if not gate_res.passed:
                gate_rejection_reasons.append(f"Track {cand.id}: {gate_res.reason}")
                continue

            score_res = self.scorer.score(detection, cand, gate_res)
            if not score_res.passed:
                gate_rejection_reasons.append(
                    f"Track {cand.id}: Score {score_res.score:.2f} below threshold {self.scoring_config.min_association_score:.2f}"
                )
                continue

            evaluated_candidates.append((cand, gate_res, score_res))

        # 4. Deterministic Tie Breaking
        if evaluated_candidates:
            evaluated_candidates.sort(
                key=lambda item: (
                    -item[2].score,
                    item[1].horizontal_distance,
                    abs(item[1].time_delta),
                    item[0].first_seen_at,
                    item[0].id,
                )
            )
            winning_track, winning_gate, winning_score = evaluated_candidates[0]
            return self._associate_to_track(
                detection, winning_track, winning_gate, winning_score, candidate_count, now
            )

        # 5. No qualifying candidate -> Create NEW track
        reason = (
            "New track created: no candidates within temporal/spatial gates"
            if candidate_count == 0
            else f"New track created: candidates rejected ({'; '.join(gate_rejection_reasons[:3])})"
        )
        return self._create_new_track(detection, candidate_count, reason, now)

    def _create_new_track(
        self, detection: Detection, candidate_count: int, reason: str, now: datetime
    ) -> TrackingResult:
        track_id = generate_track_id(detection.id)
        track = Track(
            id=track_id,
            state=TrackState.NEW,
            first_seen_at=detection.timestamp,
            last_seen_at=detection.timestamp,
            latitude=detection.latitude,
            longitude=detection.longitude,
            altitude=detection.altitude,
            velocity=detection.velocity,
            heading=detection.heading,
            confidence=detection.confidence,
            classification=detection.classification,
            source_count=1,
            created_at=now,
            updated_at=now,
        )

        history_entry = TrackHistory(
            track_id=track_id,
            sequence=1,
            timestamp=detection.timestamp,
            latitude=detection.latitude,
            longitude=detection.longitude,
            altitude=detection.altitude,
            velocity=detection.velocity,
            heading=detection.heading,
            confidence=detection.confidence,
            state=TrackState.NEW,
            provenance=detection.source_class,
            source_detection_ids=[detection.id],
            created_at=now,
        )

        association_entry = TrackAssociation(
            detection_id=detection.id,
            track_id=track_id,
            sensor_id=detection.sensor_id,
            timestamp=detection.timestamp,
            distance_meters=0.0,
            vertical_distance_meters=0.0 if detection.altitude is not None else None,
            time_delta_seconds=0.0,
            score=1.0,
            decision=TrackAssociationDecision.NEW_TRACK,
            reason=reason[:512],
            gate_result="PASSED",
            created_at=now,
        )

        try:
            with self.db.begin_nested():
                self.db.add(track)
                self.db.add(history_entry)
                self.db.add(association_entry)
                self.db.flush()

                # Stage F4: Compute initial track quality & threat assessment
                quality = compute_track_quality(self.db, track, now=now)
                threat_eval = self.threat_service.evaluate_track(track, quality, now=now)
                breach_alerts = evaluate_geofence_breach_alerts(
                    track, threat_eval.geofence_results, threat_factors=threat_eval.factors
                )
                if breach_alerts:
                    self.alert_service.process_candidates(breach_alerts, now=now)
                self.db.flush()
        except IntegrityError:
            existing_assoc = self.db.scalar(
                select(TrackAssociation).where(
                    TrackAssociation.detection_id == detection.id
                )
            )
            if existing_assoc is not None:
                track = self.db.get(Track, existing_assoc.track_id)
                decision = AssociationDecision(
                    detection_id=detection.id,
                    track_id=existing_assoc.track_id,
                    decision=TrackAssociationDecision.DUPLICATE,
                    gate_result=existing_assoc.gate_result,
                    horizontal_distance=existing_assoc.distance_meters,
                    vertical_distance=existing_assoc.vertical_distance_meters,
                    time_delta=existing_assoc.time_delta_seconds,
                    score=existing_assoc.score,
                    reason="Detection already associated",
                    candidate_count=candidate_count,
                )
                event = DetectionAssociated(
                    detection_id=detection.id,
                    track_id=existing_assoc.track_id,
                    timestamp=existing_assoc.timestamp,
                    score=existing_assoc.score,
                    decision=TrackAssociationDecision.DUPLICATE.value,
                )
                return TrackingResult(decision=decision, event=event, track=track)
            self.db.rollback()
            raise

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        decision = AssociationDecision(
            detection_id=detection.id,
            track_id=track_id,
            decision=TrackAssociationDecision.NEW_TRACK,
            gate_result="PASSED",
            horizontal_distance=0.0,
            vertical_distance=0.0 if detection.altitude is not None else None,
            time_delta=0.0,
            score=1.0,
            reason=reason,
            candidate_count=candidate_count,
        )
        event = DetectionAssociated(
            detection_id=detection.id,
            track_id=track_id,
            timestamp=detection.timestamp,
            score=1.0,
            decision=TrackAssociationDecision.NEW_TRACK.value,
        )
        return TrackingResult(decision=decision, event=event, track=track)

    def _associate_to_track(
        self,
        detection: Detection,
        track: Track,
        gate_res: GateResult,
        score_res: ScoreResult,
        candidate_count: int,
        now: datetime,
    ) -> TrackingResult:
        prev_state = track.state

        # Check if sensor is contributing for the first time
        existing_sensor_assoc = self.db.scalar(
            select(TrackAssociation.id).where(
                TrackAssociation.track_id == track.id,
                TrackAssociation.sensor_id == detection.sensor_id,
            ).limit(1)
        )
        if existing_sensor_assoc is None:
            track.source_count += 1

        # Stage F4: Multi-sensor kinematic consensus
        fused = fuse_kinematics(track, detection)
        if detection.timestamp >= track.last_seen_at:
            track.latitude = fused.latitude
            track.longitude = fused.longitude
            if fused.altitude is not None:
                track.altitude = fused.altitude
            if fused.velocity is not None:
                track.velocity = fused.velocity
            if fused.heading is not None:
                track.heading = fused.heading
            track.last_seen_at = detection.timestamp

        # Deterministic confidence smoothing
        track.confidence = round(0.7 * track.confidence + 0.3 * detection.confidence, 6)

        # Stage F4: Multi-source classification reconciliation
        reconciliation = reconcile_classification(self.db, track, latest_detection=detection)
        if reconciliation.reconciled_classification is not None:
            track.classification = reconciliation.reconciled_classification

        # Lifecycle state updates
        if track.state == TrackState.NEW:
            window_end = track.first_seen_at + timedelta(
                seconds=self.lifecycle_config.confirmation_window_seconds
            )
            assoc_count = (
                self.db.scalar(
                    select(func.count(TrackAssociation.id)).where(
                        TrackAssociation.track_id == track.id,
                        TrackAssociation.timestamp >= track.first_seen_at,
                        TrackAssociation.timestamp <= window_end,
                    )
                )
                or 0
            )
            total_qualifying = assoc_count + 1
            if (
                total_qualifying >= self.lifecycle_config.confirmation_count
                and detection.timestamp <= window_end
            ):
                track.state = TrackState.ACTIVE
        elif track.state == TrackState.STALE:
            track.state = TrackState.ACTIVE

        track.updated_at = now

        seq = (
            self.db.scalar(
                select(func.max(TrackHistory.sequence)).where(
                    TrackHistory.track_id == track.id
                )
            )
            or 0
        ) + 1

        history_entry = TrackHistory(
            track_id=track.id,
            sequence=seq,
            timestamp=detection.timestamp,
            latitude=track.latitude,
            longitude=track.longitude,
            altitude=track.altitude,
            velocity=track.velocity,
            heading=track.heading,
            confidence=track.confidence,
            state=track.state,
            provenance=detection.source_class,
            source_detection_ids=[detection.id],
            created_at=now,
        )

        association_entry = TrackAssociation(
            detection_id=detection.id,
            track_id=track.id,
            sensor_id=detection.sensor_id,
            timestamp=detection.timestamp,
            distance_meters=round(gate_res.horizontal_distance, 3),
            vertical_distance_meters=(
                round(gate_res.vertical_distance, 3)
                if gate_res.vertical_distance is not None
                else None
            ),
            time_delta_seconds=round(abs(gate_res.time_delta), 3),
            score=score_res.score,
            decision=TrackAssociationDecision.ASSOCIATED,
            reason=f"Associated with track {track.id} (score={score_res.score:.2f}, dist={gate_res.horizontal_distance:.1f}m)"[:512],
            gate_result="PASSED",
            created_at=now,
        )

        try:
            with self.db.begin_nested():
                self.db.add(history_entry)
                self.db.add(association_entry)
                self.db.flush()

                # Stage F4: Compute track quality, threat assessment, and operational alerts
                quality = compute_track_quality(
                    self.db, track, latest_distance_meters=gate_res.horizontal_distance, now=now
                )
                threat_eval = self.threat_service.evaluate_track(track, quality, now=now)

                alert_candidates = []
                det_alert = evaluate_detection_alert(
                    track, previous_state=prev_state, threat_factors=threat_eval.factors
                )
                if det_alert:
                    alert_candidates.append(det_alert)

                breach_alerts = evaluate_geofence_breach_alerts(
                    track, threat_eval.geofence_results, threat_factors=threat_eval.factors
                )
                alert_candidates.extend(breach_alerts)

                quality_alert = evaluate_data_quality_alert(track, quality)
                if quality_alert:
                    alert_candidates.append(quality_alert)

                if alert_candidates:
                    self.alert_service.process_candidates(alert_candidates, now=now)
                self.db.flush()
        except IntegrityError:
            existing_assoc = self.db.scalar(
                select(TrackAssociation).where(
                    TrackAssociation.detection_id == detection.id
                )
            )
            if existing_assoc is not None:
                track = self.db.get(Track, existing_assoc.track_id)
                decision = AssociationDecision(
                    detection_id=detection.id,
                    track_id=existing_assoc.track_id,
                    decision=TrackAssociationDecision.DUPLICATE,
                    gate_result=existing_assoc.gate_result,
                    horizontal_distance=existing_assoc.distance_meters,
                    vertical_distance=existing_assoc.vertical_distance_meters,
                    time_delta=existing_assoc.time_delta_seconds,
                    score=existing_assoc.score,
                    reason="Detection already associated",
                    candidate_count=candidate_count,
                )
                event = DetectionAssociated(
                    detection_id=detection.id,
                    track_id=existing_assoc.track_id,
                    timestamp=existing_assoc.timestamp,
                    score=existing_assoc.score,
                    decision=TrackAssociationDecision.DUPLICATE.value,
                )
                return TrackingResult(decision=decision, event=event, track=track)
            self.db.rollback()
            raise

        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise

        decision = AssociationDecision(
            detection_id=detection.id,
            track_id=track.id,
            decision=TrackAssociationDecision.ASSOCIATED,
            gate_result="PASSED",
            horizontal_distance=gate_res.horizontal_distance,
            vertical_distance=gate_res.vertical_distance,
            time_delta=gate_res.time_delta,
            score=score_res.score,
            reason=f"Associated with track {track.id}",
            candidate_count=candidate_count,
        )
        event = DetectionAssociated(
            detection_id=detection.id,
            track_id=track.id,
            timestamp=detection.timestamp,
            score=score_res.score,
            decision=TrackAssociationDecision.ASSOCIATED.value,
        )
        return TrackingResult(decision=decision, event=event, track=track)

    def process_batch(self, detections: Sequence[Detection]) -> list[TrackingResult]:
        """Process a sequence of detections in deterministic chronological order."""
        ordered = sorted(detections, key=lambda d: (d.timestamp, d.id))
        return [self.process_detection(d) for d in ordered]
