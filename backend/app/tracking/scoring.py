"""Association scoring and weight renormalization."""

from dataclasses import dataclass

from app.models.detection import Detection
from app.models.track import Track, TrackState
from app.tracking.association import angular_difference
from app.tracking.gating import GateResult, GatingConfig


@dataclass(frozen=True)
class ScoringConfig:
    weight_spatial: float = 0.50
    weight_temporal: float = 0.20
    weight_velocity: float = 0.15
    weight_heading: float = 0.10
    weight_confidence: float = 0.05
    min_association_score: float = 0.60
    max_velocity_delta: float = 50.0
    max_heading_delta: float = 90.0


@dataclass(frozen=True)
class ScoreResult:
    score: float
    passed: bool
    spatial_score: float
    temporal_score: float
    velocity_score: float | None
    heading_score: float | None
    confidence_score: float | None


class AssociationScorer:
    def __init__(
        self,
        scoring_config: ScoringConfig | None = None,
        gating_config: GatingConfig | None = None,
    ):
        self.scoring_config = scoring_config or ScoringConfig()
        self.gating_config = gating_config or GatingConfig()

    def score(
        self, detection: Detection, track: Track, gate_result: GateResult
    ) -> ScoreResult:
        multiplier = (
            self.gating_config.stale_spatial_multiplier
            if track.state == TrackState.STALE
            else 1.0
        )
        max_dist = self.gating_config.maximum_horizontal_distance * multiplier
        max_time = self.gating_config.maximum_time_delta

        dist_score = max(0.0, 1.0 - (gate_result.horizontal_distance / max_dist))
        time_score = max(0.0, 1.0 - (abs(gate_result.time_delta) / max_time))

        weighted_components: list[tuple[float, float]] = [
            (self.scoring_config.weight_spatial, dist_score),
            (self.scoring_config.weight_temporal, time_score),
        ]

        vel_score: float | None = None
        if detection.velocity is not None and track.velocity is not None:
            vel_diff = abs(detection.velocity - track.velocity)
            vel_score = max(0.0, 1.0 - (vel_diff / self.scoring_config.max_velocity_delta))
            weighted_components.append((self.scoring_config.weight_velocity, vel_score))

        head_score: float | None = None
        if detection.heading is not None and track.heading is not None:
            head_diff = angular_difference(detection.heading, track.heading)
            head_score = max(0.0, 1.0 - (head_diff / self.scoring_config.max_heading_delta))
            weighted_components.append((self.scoring_config.weight_heading, head_score))

        conf_score: float | None = None
        if detection.confidence is not None and track.confidence is not None:
            conf_diff = abs(detection.confidence - track.confidence)
            conf_score = max(0.0, 1.0 - conf_diff)
            weighted_components.append((self.scoring_config.weight_confidence, conf_score))

        total_weight = sum(w for w, _ in weighted_components)
        calculated_score = sum(w * s for w, s in weighted_components) / total_weight
        final_score = round(max(0.0, min(1.0, calculated_score)), 6)

        return ScoreResult(
            score=final_score,
            passed=final_score >= self.scoring_config.min_association_score,
            spatial_score=dist_score,
            temporal_score=time_score,
            velocity_score=vel_score,
            heading_score=head_score,
            confidence_score=conf_score,
        )
