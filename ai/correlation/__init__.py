"""Multi-track correlation, grouping, coordination index, and spatial indexing package."""

from ai.correlation.coordination import (
    MemberObservation,
    compute_coordination_index,
)
from ai.correlation.grouping import (
    GroupingConfig,
    PairwiseCorrelation,
    TrackObservation,
    correlate_tracks,
    evaluate_pairwise_correlation,
    to_track_observation,
)
from ai.correlation.spatial_grid import (
    DEFAULT_CELL_SIZE_METERS,
    SpatialGridConfig,
    SpatialHashGrid,
    normalize_latitude,
    normalize_longitude,
)

__all__ = [
    "TrackObservation",
    "PairwiseCorrelation",
    "GroupingConfig",
    "correlate_tracks",
    "evaluate_pairwise_correlation",
    "to_track_observation",
    "MemberObservation",
    "compute_coordination_index",
    "SpatialHashGrid",
    "SpatialGridConfig",
    "DEFAULT_CELL_SIZE_METERS",
    "normalize_latitude",
    "normalize_longitude",
]
