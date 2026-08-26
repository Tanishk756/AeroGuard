"""Multi-sensor observation fusion, track quality, and classification reconciliation package."""

from app.fusion.classification import (
    ClassificationReconciliation,
    reconcile_classification,
)
from app.fusion.consensus import FusedKinematics, fuse_kinematics
from app.fusion.quality import (
    QualityConfig,
    TrackQualityScore,
    calculate_source_diversity,
    compute_track_quality,
    decay_coasting_confidence,
)

__all__ = [
    "ClassificationReconciliation",
    "FusedKinematics",
    "QualityConfig",
    "TrackQualityScore",
    "calculate_source_diversity",
    "compute_track_quality",
    "decay_coasting_confidence",
    "fuse_kinematics",
    "reconcile_classification",
]
