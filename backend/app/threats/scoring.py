"""Deterministic operational threat priority scoring algorithms and factor modeling."""

from dataclasses import dataclass, field
from datetime import UTC, datetime

from app.fusion.quality import TrackQualityScore
from app.geofencing.engine import GeofenceEvaluationResult
from app.models.threat import ThreatLevel
from app.models.track import Track


@dataclass(frozen=True)
class ThreatScoringConfig:
    weight_geofence: float = 0.50
    weight_kinematic: float = 0.30
    weight_classification: float = 0.20
    max_proximity_warning_distance: float = 5000.0
    max_speed_reference: float = 50.0  # m/s
    threshold_critical: float = 80.0
    threshold_high: float = 55.0
    threshold_medium: float = 25.0
    classification_weights: dict[str, float] = field(
        default_factory=lambda: {
            "UAV": 0.85,
            "DRONE": 0.85,
            "HELICOPTER": 0.60,
            "PLANE": 0.40,
            "UNKNOWN": 0.50,
            "BIRD": 0.05,
        }
    )


@dataclass(frozen=True)
class ThreatFactors:
    score: float
    level: ThreatLevel
    geofence_factor: float
    kinematic_factor: float
    classification_factor: float
    track_quality: float
    source_diversity: float
    breached_geofences: list[str]
    nearest_geofence_distance_meters: float | None
    reason: str
    evaluation_timestamp: datetime

    def to_dict(self) -> dict:
        return {
            "score": self.score,
            "level": self.level.value,
            "geofence_factor": self.geofence_factor,
            "kinematic_factor": self.kinematic_factor,
            "classification_factor": self.classification_factor,
            "track_quality": self.track_quality,
            "source_diversity": self.source_diversity,
            "breached_geofences": self.breached_geofences,
            "nearest_geofence_distance_meters": self.nearest_geofence_distance_meters,
            "reason": self.reason,
            "evaluation_timestamp": self.evaluation_timestamp.isoformat(),
        }


def calculate_threat_score(
    track: Track,
    quality: TrackQualityScore,
    geofence_evaluations: list[GeofenceEvaluationResult],
    config: ThreatScoringConfig | None = None,
    now: datetime | None = None,
) -> ThreatFactors:
    """Calculate deterministic operational threat priority score and factor breakdown.

    All scores represent relative operational urgency and prioritization for defensive review,
    not probabilistic attack likelihood.
    """
    cfg = config or ThreatScoringConfig()
    eval_time = now or datetime.now(UTC).replace(tzinfo=None)

    # 1. Geofence Factor
    breached = [g.geofence_id for g in geofence_evaluations if g.inside]
    distances = [g.distance_to_boundary_meters for g in geofence_evaluations if g.distance_to_boundary_meters < 999999.0]
    nearest_dist = min(distances) if distances else None

    if breached:
        geofence_factor = 1.00
    elif nearest_dist is not None:
        geofence_factor = max(0.0, min(1.0, 1.0 - (nearest_dist / cfg.max_proximity_warning_distance)))
    else:
        geofence_factor = 0.00

    # 2. Kinematic Factor (speed relative to reference baseline)
    if track.velocity is not None:
        kinematic_factor = max(0.0, min(1.0, track.velocity / cfg.max_speed_reference))
    else:
        kinematic_factor = 0.20

    # 3. Classification Factor
    cls_key = (track.classification or "UNKNOWN").strip().upper()
    classification_factor = cfg.classification_weights.get(cls_key, 0.50)

    # 4. Composite Threat Priority Calculation
    raw_score = 100.0 * (
        cfg.weight_geofence * geofence_factor
        + cfg.weight_kinematic * kinematic_factor
        + cfg.weight_classification * classification_factor
    ) * quality.quality

    final_score = round(max(0.0, min(100.0, raw_score)), 2)

    # 5. Threat Level Assignment
    if final_score >= cfg.threshold_critical or (breached and cls_key in ("UAV", "DRONE") and quality.quality >= 0.40):
        level = ThreatLevel.CRITICAL
    elif final_score >= cfg.threshold_high:
        level = ThreatLevel.HIGH
    elif final_score >= cfg.threshold_medium:
        level = ThreatLevel.MEDIUM
    else:
        level = ThreatLevel.LOW

    # 6. Reason Generation
    if breached:
        reason = f"Operational priority {level.value}: track breached {len(breached)} active geofence(s) [{', '.join(breached[:2])}]"
    elif nearest_dist is not None and nearest_dist < 1000.0:
        reason = f"Operational priority {level.value}: track proximity {nearest_dist:.0f}m from protected perimeter"
    else:
        reason = f"Operational priority {level.value}: score={final_score:.1f}, class={cls_key}, quality={quality.quality:.2f}"

    return ThreatFactors(
        score=final_score,
        level=level,
        geofence_factor=round(geofence_factor, 4),
        kinematic_factor=round(kinematic_factor, 4),
        classification_factor=round(classification_factor, 4),
        track_quality=quality.quality,
        source_diversity=quality.diversity_component,
        breached_geofences=breached,
        nearest_geofence_distance_meters=nearest_dist,
        reason=reason,
        evaluation_timestamp=eval_time,
    )
