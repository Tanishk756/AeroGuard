"""Multi-track correlation, grouping, and coordination index package."""

from ai.correlation.grouping import (
    TrackObservation,
    PairwiseCorrelation,
    GroupingConfig,
    correlate_tracks,
    evaluate_pairwise_correlation,
)
from ai.correlation.coordination import (
    MemberObservation,
    compute_coordination_index,
)

__all__ = [
    "TrackObservation",
    "PairwiseCorrelation",
    "GroupingConfig",
    "correlate_tracks",
    "evaluate_pairwise_correlation",
    "MemberObservation",
    "compute_coordination_index",
]
