"""Track association, gating, scoring, lifecycle, and management package."""

from app.tracking.association import (
    AssociationDecision,
    angular_difference,
    calculate_distance_3d,
    generate_track_id,
    haversine_distance,
)
from app.tracking.events import DetectionAssociated
from app.tracking.gating import AssociationGate, GateResult, GatingConfig
from app.tracking.lifecycle import LifecycleConfig, TrackLifecycleService, TrackStateTransition
from app.tracking.scoring import AssociationScorer, ScoreResult, ScoringConfig
from app.tracking.service import DetectionCandidateProvider, TrackingResult, TrackingService

__all__ = [
    "AssociationDecision",
    "AssociationGate",
    "AssociationScorer",
    "DetectionAssociated",
    "DetectionCandidateProvider",
    "GateResult",
    "GatingConfig",
    "LifecycleConfig",
    "ScoreResult",
    "ScoringConfig",
    "TrackLifecycleService",
    "TrackStateTransition",
    "TrackingResult",
    "TrackingService",
    "angular_difference",
    "calculate_distance_3d",
    "generate_track_id",
    "haversine_distance",
]
