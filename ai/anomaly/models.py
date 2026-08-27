"""Configuration and threshold definitions for deterministic anomaly scoring."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class AnomalyScoringConfig:
    """Configurable weights and thresholds for deterministic anomaly assessment."""

    weight_turn_rate: float = 0.25
    weight_vertical_rate: float = 0.25
    weight_acceleration: float = 0.20
    weight_loitering: float = 0.15
    weight_speed: float = 0.15

    # Threshold baselines for scoring normalization
    normal_turn_rate_max_dps: float = 15.0  # Turn rate above this scales up anomaly
    extreme_turn_rate_dps: float = 60.0

    normal_climb_rate_max_mps: float = 5.0  # Vertical speed above this scales up anomaly
    extreme_climb_rate_mps: float = 25.0

    normal_acceleration_max_mps2: float = 4.0
    extreme_acceleration_mps2: float = 15.0

    normal_speed_max_mps: float = 35.0  # Standard commercial UAV max speed
    extreme_speed_mps: float = 75.0

    # Severity level score cutoffs
    threshold_critical: float = 80.0
    threshold_high: float = 60.0
    threshold_medium: float = 30.0
