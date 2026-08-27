"""Deterministic, explainable kinematic anomaly scoring algorithms."""

from datetime import UTC, datetime
from ai.anomaly.models import AnomalyScoringConfig
from ai.schemas import (
    AnomalyAssessment,
    AnomalyCategory,
    AnomalyFactor,
    KinematicFeatures,
)


def _classify_severity(score: float, config: AnomalyScoringConfig) -> str:
    if score >= config.threshold_critical:
        return "CRITICAL"
    if score >= config.threshold_high:
        return "HIGH"
    if score >= config.threshold_medium:
        return "MEDIUM"
    return "LOW"


def evaluate_anomaly(
    track_id: str,
    features: KinematicFeatures,
    sensor_confidence: float = 1.0,
    config: AnomalyScoringConfig | None = None,
) -> AnomalyAssessment:
    """Compute deterministic, explainable anomaly score and contributing factors for a track."""
    cfg = config or AnomalyScoringConfig()
    factors: list[AnomalyFactor] = []

    # 1. Turn Rate / Erratic Heading Factor
    turn_rate = abs(features.turn_rate_dps)
    if turn_rate <= cfg.normal_turn_rate_max_dps:
        turn_score = (turn_rate / cfg.normal_turn_rate_max_dps) * 20.0
    else:
        excess = min(1.0, (turn_rate - cfg.normal_turn_rate_max_dps) / (cfg.extreme_turn_rate_dps - cfg.normal_turn_rate_max_dps))
        turn_score = 20.0 + (excess * 80.0)
    turn_score = round(min(100.0, max(0.0, turn_score)), 1)
    turn_contrib = round(turn_score * cfg.weight_turn_rate, 2)
    turn_desc = f"Turn rate {turn_rate:.1f}°/s (baseline: ≤{cfg.normal_turn_rate_max_dps:.0f}°/s)"
    factors.append(
        AnomalyFactor(
            name="Turn Rate & Heading Stability",
            score=turn_score,
            weight=cfg.weight_turn_rate,
            contribution=turn_contrib,
            severity=_classify_severity(turn_score, cfg),
            description=turn_desc,
        )
    )

    # 2. Vertical Rate / Climb & Dive Factor
    vert_speed = abs(features.vertical_speed_mps)
    if vert_speed <= cfg.normal_climb_rate_max_mps:
        vert_score = (vert_speed / cfg.normal_climb_rate_max_mps) * 15.0
    else:
        excess = min(1.0, (vert_speed - cfg.normal_climb_rate_max_mps) / (cfg.extreme_climb_rate_mps - cfg.normal_climb_rate_max_mps))
        vert_score = 15.0 + (excess * 85.0)
    vert_score = round(min(100.0, max(0.0, vert_score)), 1)
    vert_contrib = round(vert_score * cfg.weight_vertical_rate, 2)
    direction_str = "climb" if features.vertical_speed_mps >= 0 else "descent"
    vert_desc = f"Vertical {direction_str} {vert_speed:.1f} m/s (baseline: ≤{cfg.normal_climb_rate_max_mps:.0f} m/s)"
    factors.append(
        AnomalyFactor(
            name="Vertical Speed & Altitude Rate",
            score=vert_score,
            weight=cfg.weight_vertical_rate,
            contribution=vert_contrib,
            severity=_classify_severity(vert_score, cfg),
            description=vert_desc,
        )
    )

    # 3. Horizontal Acceleration Factor
    accel = abs(features.acceleration_mps2)
    if accel <= cfg.normal_acceleration_max_mps2:
        acc_score = (accel / cfg.normal_acceleration_max_mps2) * 15.0
    else:
        excess = min(1.0, (accel - cfg.normal_acceleration_max_mps2) / (cfg.extreme_acceleration_mps2 - cfg.normal_acceleration_max_mps2))
        acc_score = 15.0 + (excess * 85.0)
    acc_score = round(min(100.0, max(0.0, acc_score)), 1)
    acc_contrib = round(acc_score * cfg.weight_acceleration, 2)
    acc_desc = f"Acceleration {accel:.1f} m/s² (baseline: ≤{cfg.normal_acceleration_max_mps2:.0f} m/s²)"
    factors.append(
        AnomalyFactor(
            name="Kinematic Acceleration Rate",
            score=acc_score,
            weight=cfg.weight_acceleration,
            contribution=acc_contrib,
            severity=_classify_severity(acc_score, cfg),
            description=acc_desc,
        )
    )

    # 4. Loitering Pattern Factor
    if features.loiter_radius_meters is not None:
        loiter_score = 50.0 + min(50.0, (1.0 - features.directional_consistency) * 50.0)
        loiter_desc = f"Circular loitering detected (radius ~{features.loiter_radius_meters:.0f}m, consistency {features.directional_consistency:.2f})"
    elif features.directional_consistency < 0.5:
        loiter_score = (1.0 - features.directional_consistency) * 60.0
        loiter_desc = f"Low directional consistency ({features.directional_consistency:.2f})"
    else:
        loiter_score = 0.0
        loiter_desc = f"High directional consistency ({features.directional_consistency:.2f})"
    loiter_score = round(min(100.0, max(0.0, loiter_score)), 1)
    loiter_contrib = round(loiter_score * cfg.weight_loitering, 2)
    factors.append(
        AnomalyFactor(
            name="Loitering & Pattern Recurrence",
            score=loiter_score,
            weight=cfg.weight_loitering,
            contribution=loiter_contrib,
            severity=_classify_severity(loiter_score, cfg),
            description=loiter_desc,
        )
    )

    # 5. Unusual Velocity Factor
    speed = features.speed_mps
    if speed <= cfg.normal_speed_max_mps:
        speed_score = 0.0
        speed_desc = f"Nominal velocity {speed:.1f} m/s"
    else:
        excess = min(1.0, (speed - cfg.normal_speed_max_mps) / (cfg.extreme_speed_mps - cfg.normal_speed_max_mps))
        speed_score = 20.0 + (excess * 80.0)
        speed_desc = f"Elevated speed {speed:.1f} m/s (baseline: ≤{cfg.normal_speed_max_mps:.0f} m/s)"
    speed_score = round(min(100.0, max(0.0, speed_score)), 1)
    speed_contrib = round(speed_score * cfg.weight_speed, 2)
    factors.append(
        AnomalyFactor(
            name="Speed & Velocity Bounds",
            score=speed_score,
            weight=cfg.weight_speed,
            contribution=speed_contrib,
            severity=_classify_severity(speed_score, cfg),
            description=speed_desc,
        )
    )

    # Calculate aggregate anomaly score: blend weighted average with peak factor
    # to capture both multi-factor degradation and acute single-dimension anomalies
    weighted_sum = sum(f.contribution for f in factors)
    max_factor_score = max((f.score for f in factors), default=0.0)
    raw_aggregate = max(weighted_sum, 0.60 * max_factor_score + 0.40 * weighted_sum)

    # Moderate by sensor confidence to prevent low-confidence noise from triggering false alarms
    confidence_moderator = 0.5 + (0.5 * max(0.0, min(1.0, sensor_confidence)))
    final_score = round(min(100.0, max(0.0, raw_aggregate * confidence_moderator)), 1)
    anomaly_level = _classify_severity(final_score, cfg)

    # Determine primary anomaly category
    if final_score < cfg.threshold_medium:
        primary_category = AnomalyCategory.NORMAL
    else:
        # Find highest contributing factor
        highest_factor = max(factors, key=lambda f: f.contribution)
        if highest_factor.name.startswith("Turn"):
            primary_category = AnomalyCategory.ERRATIC_HEADING
        elif highest_factor.name.startswith("Vertical"):
            primary_category = AnomalyCategory.RAPID_ALTITUDE_CHANGE
        elif highest_factor.name.startswith("Kinematic"):
            primary_category = AnomalyCategory.EXCESSIVE_ACCELERATION
        elif highest_factor.name.startswith("Loitering"):
            primary_category = AnomalyCategory.LOITERING_PATTERN
        else:
            primary_category = AnomalyCategory.UNUSUAL_KINEMATICS

    # Generate explainable summary
    high_factors = [f for f in factors if f.score >= cfg.threshold_medium]
    if not high_factors:
        summary = "Flight kinematics nominal and consistent with standard airspace transit."
    else:
        factor_summaries = [f"{f.name} ({f.severity}: {f.score:.0f})" for f in sorted(high_factors, key=lambda x: x.contribution, reverse=True)]
        summary = f"Anomalous flight indicators detected: {', '.join(factor_summaries)}."

    return AnomalyAssessment(
        track_id=track_id,
        anomaly_score=final_score,
        anomaly_level=anomaly_level,
        primary_category=primary_category,
        sensor_confidence=round(sensor_confidence, 3),
        factors=factors,
        summary=summary,
        evaluated_at=datetime.now(UTC),
    )
