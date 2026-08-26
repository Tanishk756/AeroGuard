"""Threat assessment service managing evaluation, upserts, and explainable factor storage."""

from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.fusion.quality import TrackQualityScore
from app.geofencing.engine import GeofenceEvaluationResult, evaluate_geofence
from app.models.geofence import Geofence
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track
from app.threats.events import ThreatAssessed
from app.threats.scoring import ThreatFactors, ThreatScoringConfig, calculate_threat_score


@dataclass(frozen=True)
class ThreatEvaluationResult:
    assessment: ThreatAssessment
    factors: ThreatFactors
    event: ThreatAssessed
    geofence_results: list[GeofenceEvaluationResult]


class ThreatAssessmentService:
    def __init__(
        self,
        db: Session,
        scoring_config: ThreatScoringConfig | None = None,
    ):
        self.db = db
        self.scoring_config = scoring_config or ThreatScoringConfig()

    def evaluate_track(
        self,
        track: Track,
        quality: TrackQualityScore,
        now: datetime | None = None,
    ) -> ThreatEvaluationResult:
        """Evaluate operational threat priority for a track and persist/upsert the ThreatAssessment record."""
        eval_time = now or datetime.now(UTC).replace(tzinfo=None)

        # 1. Evaluate against all enabled geofences
        enabled_geofences = self.db.scalars(
            select(Geofence).where(Geofence.enabled.is_(True))
        ).all()
        geofence_results = [
            evaluate_geofence(track.latitude, track.longitude, track.altitude, g)
            for g in enabled_geofences
        ]

        # 2. Compute threat factors and score
        factors = calculate_threat_score(
            track=track,
            quality=quality,
            geofence_evaluations=geofence_results,
            config=self.scoring_config,
            now=eval_time,
        )

        # 3. Upsert into threat_assessments table
        existing = self.db.scalar(
            select(ThreatAssessment).where(ThreatAssessment.track_id == track.id)
        )

        if existing is not None:
            existing.score = factors.score
            existing.level = factors.level
            existing.factors = factors.to_dict()
            existing.updated_at = eval_time
            assessment = existing
        else:
            assessment = ThreatAssessment(
                track_id=track.id,
                score=factors.score,
                level=factors.level,
                factors=factors.to_dict(),
                created_at=eval_time,
                updated_at=eval_time,
            )
            try:
                with self.db.begin_nested():
                    self.db.add(assessment)
                    self.db.flush()
            except IntegrityError:
                # Race condition fallback
                existing_race = self.db.scalar(
                    select(ThreatAssessment).where(ThreatAssessment.track_id == track.id)
                )
                if existing_race is not None:
                    existing_race.score = factors.score
                    existing_race.level = factors.level
                    existing_race.factors = factors.to_dict()
                    existing_race.updated_at = eval_time
                    assessment = existing_race
                else:
                    raise

        event = ThreatAssessed(
            track_id=track.id,
            score=factors.score,
            level=factors.level.value,
            factors=factors.to_dict(),
            timestamp=eval_time,
        )

        return ThreatEvaluationResult(
            assessment=assessment,
            factors=factors,
            event=event,
            geofence_results=geofence_results,
        )
