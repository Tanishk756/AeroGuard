"""Explainable defensive threat prioritization scoring engine — Stage AI2-E.

ARCHITECTURE
------------
Computes a deterministic, explainable situational-awareness defensive priority score
for individual airspace tracks based on multi-source defensive indicators:
1. Defensive geofence proximity/ingress (weight: 0.30)
2. Behavioral classification state (weight: 0.25)
3. Persistent anomaly profile (weight: 0.20)
4. Multi-track coordination index (weight: 0.15)
5. Kinematic dynamics & velocity bounds (weight: 0.10)

FORMULATION
-----------
Base priority score:
    P_base = 0.30 × P_geofence + 0.25 × P_behavior + 0.20 × P_anomaly + 0.15 × P_coordination + 0.10 × P_kinematic

Confidence scaling:
    P_scaled = clamp(P_base, 0, 100) × (0.30 + 0.70 × C_s)

Final priority score:
    P_final = clamp(P_scaled, 0, 100)

Where every component P_* is normalized to [0, 100] and C_s ∈ [0, 1].

SAFETY BOUNDARY
---------------
This module computes an informational operational situational-awareness prioritization metric
("Which track deserves greater operator attention?").
It must NOT:
- identify targets for engagement
- recommend weapons
- recommend interception
- control aircraft
- control countermeasures
- provide fire-control logic
- produce hostile-intent probabilities
- generate destructive actions
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Sequence

from ai.anomaly.models import AnomalyScoringConfig
from ai.anomaly.persistent import PersistentAnomalyResult
from ai.schemas import (
    AnomalyAssessment,
    BehaviorClassification,
    BehavioralState,
    CoordinatedFormation,
    GeofenceIngressEstimate,
    KinematicFeatures,
    ThreatPriorityAssessment,
    ThreatPriorityFactor,
)


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PriorityScoringConfig:
    """Configurable weights and thresholds for defensive threat prioritization."""

    # Component weights (must sum exactly to 1.0)
    weight_geofence: float = 0.30
    weight_behavior: float = 0.25
    weight_anomaly: float = 0.20
    weight_coordination: float = 0.15
    weight_kinematic: float = 0.10

    # Confidence scaling: P_scaled = clamp(P_base, 0, 100) * (confidence_base + confidence_scale * C_s)
    confidence_base: float = 0.30
    confidence_scale: float = 0.70

    # Priority level classification thresholds
    threshold_critical: float = 80.0
    threshold_high: float = 60.0
    threshold_medium: float = 30.0

    # Range clamping bounds
    score_min: float = 0.0
    score_max: float = 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Behavioral State Score Mapping (Deterministic)
# ─────────────────────────────────────────────────────────────────────────────

BEHAVIOR_PRIORITY_MAP: dict[BehavioralState, float] = {
    BehavioralState.NORMAL: 10.0,
    BehavioralState.DEPARTING: 20.0,
    BehavioralState.LOITERING: 50.0,
    BehavioralState.APPROACHING: 70.0,
    BehavioralState.COORDINATED: 80.0,
    BehavioralState.RAPID_CHANGE: 85.0,
    BehavioralState.ANOMALOUS: 90.0,
}


# ─────────────────────────────────────────────────────────────────────────────
# Component Normalization Functions
# ─────────────────────────────────────────────────────────────────────────────

def normalize_geofence_component(
    ingress_estimates: Sequence[Any] | None = None,
    raw_score: float | None = None,
) -> tuple[float, str]:
    """Normalize defensive geofence ingress estimates into [0.0, 100.0].

    Rules:
    - INSIDE: 100.0 (inside defensive boundary)
    - APPROACHING: 30.0 to 100.0 based on estimated time to breach (TTB <= 60s)
    - DIVERGING: 15.0 (receding from perimeter)
    - NO_INTERSECTION: 0.0 (no breach forecast)
    - Missing / None: 0.0 (neutral fallback)
    """
    if raw_score is not None:
        score = round(max(0.0, min(100.0, float(raw_score))), 1)
        return score, f"Direct geofence score input: {score:.1f}"

    if not ingress_estimates:
        return 0.0, "No active geofence ingress or breach detected (neutral fallback)"

    # 1. Check for INSIDE status
    inside_estimates = [
        e for e in ingress_estimates
        if getattr(e, "status", None) == "INSIDE"
    ]
    if inside_estimates:
        gname = getattr(inside_estimates[0], "geofence_name", getattr(inside_estimates[0], "geofence_id", "perimeter"))
        return 100.0, f"Track is INSIDE defensive geofence boundary ({gname})"

    # 2. Check for APPROACHING status
    approaching = [
        e for e in ingress_estimates
        if getattr(e, "status", None) == "APPROACHING"
    ]
    if approaching:
        # Find closest breach forecast (lowest positive TTB)
        valid_ttbs = [
            (getattr(e, "estimated_time_to_breach_seconds", None), e)
            for e in approaching
        ]
        ttb_entries = [(ttb, e) for ttb, e in valid_ttbs if ttb is not None]

        if ttb_entries:
            min_ttb, best_est = min(ttb_entries, key=lambda x: x[0])
            gname = getattr(best_est, "geofence_name", getattr(best_est, "geofence_id", "perimeter"))
            if min_ttb <= 0.0:
                score = 100.0
                desc = f"Track approaching defensive geofence {gname} (imminent breach)"
            elif min_ttb <= 60.0:
                # Linear scaling from 100.0 (at ttb=0) down to 30.0 (at ttb=60.0)
                score = round(max(30.0, min(100.0, 100.0 - (min_ttb / 60.0) * 70.0)), 1)
                desc = f"Track approaching defensive geofence {gname} (est. breach in {min_ttb:.1f}s)"
            else:
                score = 30.0
                desc = f"Track approaching defensive geofence {gname} (est. breach in {min_ttb:.1f}s > 60s horizon)"
            return score, desc
        else:
            return 80.0, "Track approaching defensive geofence (unspecified breach time)"

    # 3. Check for DIVERGING status
    diverging = [
        e for e in ingress_estimates
        if getattr(e, "status", None) == "DIVERGING"
    ]
    if diverging:
        return 15.0, "Track trajectory is diverging from defensive geofence"

    # 4. Default NO_INTERSECTION / other
    return 0.0, "Track trajectory has no projected geofence intersection"


def normalize_behavior_component(
    behavior: Any | None = None,
    raw_score: float | None = None,
) -> tuple[float, str]:
    """Normalize behavioral classification into [0.0, 100.0].

    Deterministic mapping:
    - NORMAL: 10.0
    - DEPARTING: 20.0
    - LOITERING: 50.0
    - APPROACHING: 70.0
    - COORDINATED: 80.0
    - RAPID_CHANGE: 85.0
    - ANOMALOUS: 90.0
    - Missing / None: 10.0 (NORMAL baseline fallback)
    """
    if raw_score is not None:
        score = round(max(0.0, min(100.0, float(raw_score))), 1)
        return score, f"Direct behavior score input: {score:.1f}"

    if behavior is None:
        return 10.0, "No behavioral classification evidence; default to NORMAL baseline"

    if isinstance(behavior, BehaviorClassification):
        state = behavior.state
        score = BEHAVIOR_PRIORITY_MAP.get(state, 10.0)
        return score, f"Behavioral state: {state.value} (confidence {behavior.confidence:.2f}): {behavior.reason}"

    if isinstance(behavior, BehavioralState):
        score = BEHAVIOR_PRIORITY_MAP.get(behavior, 10.0)
        return score, f"Behavioral state: {behavior.value}"

    if isinstance(behavior, str):
        try:
            enum_val = BehavioralState(behavior.upper())
            score = BEHAVIOR_PRIORITY_MAP.get(enum_val, 10.0)
            return score, f"Behavioral state: {enum_val.value}"
        except ValueError:
            return 10.0, f"Unrecognized behavioral state '{behavior}'; default to NORMAL baseline"

    return 10.0, "No valid behavioral classification evidence; default to NORMAL baseline"


def normalize_anomaly_component(
    persistent_anomaly: Any | None = None,
    raw_score: float | None = None,
) -> tuple[float, str]:
    """Normalize persistent anomaly accumulation into [0.0, 100.0].

    Consumes AI2-D PersistentAnomalyResult or raw persistent anomaly score.
    Missing / None: 0.0 (neutral fallback).
    """
    if raw_score is not None:
        score = round(max(0.0, min(100.0, float(raw_score))), 1)
        return score, f"Direct anomaly score input: {score:.1f}"

    if persistent_anomaly is None:
        return 0.0, "No persistent anomaly history available (neutral fallback)"

    if isinstance(persistent_anomaly, PersistentAnomalyResult):
        score = round(max(0.0, min(100.0, persistent_anomaly.persistent_score)), 1)
        if persistent_anomaly.is_anomalous:
            desc = f"Persistent anomaly active (score: {score:.1f}, {persistent_anomaly.qualifying_ticks} qualifying ticks)"
        else:
            desc = f"Persistent anomaly accumulated score: {score:.1f}"
        return score, desc

    if isinstance(persistent_anomaly, (int, float)):
        score = round(max(0.0, min(100.0, float(persistent_anomaly))), 1)
        return score, f"Persistent anomaly score: {score:.1f}"

    return 0.0, "No valid persistent anomaly data available (neutral fallback)"


def normalize_coordination_component(
    coordination: Any | None = None,
    raw_score: float | None = None,
) -> tuple[float, str]:
    """Normalize multi-track coordination into [0.0, 100.0].

    Consumes AI2-D CoordinatedFormation (synchronization_index * 100.0) or float sync index.
    Missing / None: 0.0 (neutral fallback).
    """
    if raw_score is not None:
        score = round(max(0.0, min(100.0, float(raw_score))), 1)
        return score, f"Direct coordination score input: {score:.1f}"

    if coordination is None:
        return 0.0, "Track is not part of a coordinated formation (neutral fallback)"

    if isinstance(coordination, CoordinatedFormation):
        score = round(max(0.0, min(100.0, coordination.synchronization_index * 100.0)), 1)
        desc = (
            f"Coordinated formation {coordination.formation_id} "
            f"(sync index: {coordination.synchronization_index:.2f}, members: {len(coordination.member_track_ids)})"
        )
        return score, desc

    if isinstance(coordination, (int, float)):
        val = float(coordination)
        if 0.0 <= val <= 1.0:
            score = round(val * 100.0, 1)
        else:
            score = round(max(0.0, min(100.0, val)), 1)
        return score, f"Coordination index contribution: {score:.1f}"

    return 0.0, "No valid coordination data available (neutral fallback)"


def normalize_kinematic_component(
    kinematics: Any | None = None,
    raw_score: float | None = None,
) -> tuple[float, str]:
    """Normalize kinematic dynamics / instantaneous anomaly into [0.0, 100.0].

    Consumes AI1 KinematicFeatures, AnomalyAssessment, or raw numeric score.
    Missing / None: 0.0 (neutral fallback).
    """
    if raw_score is not None:
        score = round(max(0.0, min(100.0, float(raw_score))), 1)
        return score, f"Direct kinematic score input: {score:.1f}"

    if kinematics is None:
        return 0.0, "No kinematic dynamic features available (neutral fallback)"

    if isinstance(kinematics, KinematicFeatures):
        # Deterministic kinematic activity composite:
        # Speed: up to 50 m/s -> 40 pts
        # Acceleration: up to 10 m/s² -> 30 pts
        # Turn rate: up to 60 °/s -> 30 pts
        speed_comp = min(1.0, kinematics.speed_mps / 50.0) * 40.0
        accel_comp = min(1.0, abs(kinematics.acceleration_mps2) / 10.0) * 30.0
        turn_comp = min(1.0, abs(kinematics.turn_rate_dps) / 60.0) * 30.0
        score = round(max(0.0, min(100.0, speed_comp + accel_comp + turn_comp)), 1)
        desc = (
            f"Kinematics: speed={kinematics.speed_mps:.1f} m/s, "
            f"accel={kinematics.acceleration_mps2:.1f} m/s², "
            f"turn_rate={kinematics.turn_rate_dps:.1f} °/s"
        )
        return score, desc

    if isinstance(kinematics, AnomalyAssessment):
        score = round(max(0.0, min(100.0, kinematics.anomaly_score)), 1)
        desc = f"Kinematic instantaneous anomaly: {score:.1f} ({kinematics.primary_category.value})"
        return score, desc

    if isinstance(kinematics, (int, float)):
        score = round(max(0.0, min(100.0, float(kinematics))), 1)
        return score, f"Kinematic dynamic score: {score:.1f}"

    return 0.0, "No valid kinematic dynamic data available (neutral fallback)"


# ─────────────────────────────────────────────────────────────────────────────
# Priority Level Classification
# ─────────────────────────────────────────────────────────────────────────────

def classify_priority_level(score: float, config: PriorityScoringConfig | None = None) -> str:
    """Deterministically map final priority score to priority level string."""
    cfg = config or PriorityScoringConfig()
    if score >= cfg.threshold_critical:
        return "CRITICAL"
    if score >= cfg.threshold_high:
        return "HIGH"
    if score >= cfg.threshold_medium:
        return "MEDIUM"
    return "LOW"


# ─────────────────────────────────────────────────────────────────────────────
# Core Priority Evaluation Function
# ─────────────────────────────────────────────────────────────────────────────

def evaluate_threat_priority(
    track_id: str,
    group_id: str | None = None,
    ingress_estimates: Sequence[Any] | None = None,
    behavior: Any | None = None,
    persistent_anomaly: Any | None = None,
    coordination: Any | None = None,
    kinematics: Any | None = None,
    sensor_confidence: float = 1.0,
    # Direct component score overrides for exact mathematical / unit testing
    p_geofence_override: float | None = None,
    p_behavior_override: float | None = None,
    p_anomaly_override: float | None = None,
    p_coordination_override: float | None = None,
    p_kinematic_override: float | None = None,
    config: PriorityScoringConfig | None = None,
    evaluated_at: datetime | None = None,
) -> ThreatPriorityAssessment:
    """Compute explainable defensive threat priority assessment for a track.

    Mathematical Model:
    1. P_base = 0.30 × P_geofence + 0.25 × P_behavior + 0.20 × P_anomaly + 0.15 × P_coordination + 0.10 × P_kinematic
    2. P_scaled = clamp(P_base, 0, 100) × (0.30 + 0.70 × C_s)
    3. P_final = clamp(P_scaled, 0, 100)
    """
    cfg = config or PriorityScoringConfig()
    eval_ts = evaluated_at or datetime.now(UTC)

    # ── 1. Component Normalization ─────────────────────────────────────────
    p_geofence, desc_geofence = normalize_geofence_component(ingress_estimates, raw_score=p_geofence_override)
    p_behavior, desc_behavior = normalize_behavior_component(behavior, raw_score=p_behavior_override)
    p_anomaly, desc_anomaly = normalize_anomaly_component(persistent_anomaly, raw_score=p_anomaly_override)
    p_coordination, desc_coordination = normalize_coordination_component(coordination, raw_score=p_coordination_override)
    p_kinematic, desc_kinematic = normalize_kinematic_component(kinematics, raw_score=p_kinematic_override)

    # ── 2. Weighted Factor Breakdown & Mathematical Reconciliation ────────
    contrib_geofence = round(p_geofence * cfg.weight_geofence, 2)
    contrib_behavior = round(p_behavior * cfg.weight_behavior, 2)
    contrib_anomaly = round(p_anomaly * cfg.weight_anomaly, 2)
    contrib_coordination = round(p_coordination * cfg.weight_coordination, 2)
    contrib_kinematic = round(p_kinematic * cfg.weight_kinematic, 2)

    factors: list[ThreatPriorityFactor] = [
        ThreatPriorityFactor(
            name="Defensive Geofence Ingress & Proximity",
            score=p_geofence,
            weight=cfg.weight_geofence,
            contribution=contrib_geofence,
            description=desc_geofence[:300],
        ),
        ThreatPriorityFactor(
            name="Behavioral Classification",
            score=p_behavior,
            weight=cfg.weight_behavior,
            contribution=contrib_behavior,
            description=desc_behavior[:300],
        ),
        ThreatPriorityFactor(
            name="Persistent Anomaly Profile",
            score=p_anomaly,
            weight=cfg.weight_anomaly,
            contribution=contrib_anomaly,
            description=desc_anomaly[:300],
        ),
        ThreatPriorityFactor(
            name="Multi-Track Coordination",
            score=p_coordination,
            weight=cfg.weight_coordination,
            contribution=contrib_coordination,
            description=desc_coordination[:300],
        ),
        ThreatPriorityFactor(
            name="Kinematic Dynamics & Velocity",
            score=p_kinematic,
            weight=cfg.weight_kinematic,
            contribution=contrib_kinematic,
            description=desc_kinematic[:300],
        ),
    ]

    # Base score: exact weighted sum
    p_base = (
        cfg.weight_geofence * p_geofence
        + cfg.weight_behavior * p_behavior
        + cfg.weight_anomaly * p_anomaly
        + cfg.weight_coordination * p_coordination
        + cfg.weight_kinematic * p_kinematic
    )
    p_base_clamped = max(cfg.score_min, min(cfg.score_max, p_base))

    # ── 3. Confidence Scaling ──────────────────────────────────────────────
    c_s = max(0.0, min(1.0, float(sensor_confidence if sensor_confidence is not None else 1.0)))
    conf_scale = cfg.confidence_base + (cfg.confidence_scale * c_s)
    p_scaled = p_base_clamped * conf_scale
    final_score = round(max(cfg.score_min, min(cfg.score_max, p_scaled)), 1)

    # ── 4. Priority Level Assignment ───────────────────────────────────────
    priority_level = classify_priority_level(final_score, cfg)

    # ── 5. Explainable Reason Generation ───────────────────────────────────
    top_factors = sorted(factors, key=lambda f: f.contribution, reverse=True)
    active_factors = [f for f in top_factors if f.score > 0.0]

    if active_factors:
        lead = active_factors[0]
        reason_parts = [f"{lead.name} (+{lead.contribution:.1f} pts)"]
        if len(active_factors) > 1 and active_factors[1].contribution > 0.0:
            second = active_factors[1]
            reason_parts.append(f"{second.name} (+{second.contribution:.1f} pts)")
        reason = (
            f"Defensive priority {priority_level} (score: {final_score:.1f}/100, "
            f"base: {p_base:.1f}, conf_scale: {conf_scale:.2f}): "
            f"primary indicators: {', '.join(reason_parts)}."
        )
    else:
        reason = (
            f"Defensive priority {priority_level} (score: {final_score:.1f}/100): "
            f"nominal baseline across all defensive indicators."
        )

    return ThreatPriorityAssessment(
        track_id=track_id,
        group_id=group_id,
        priority_score=final_score,
        priority_level=priority_level,
        confidence=round(c_s, 3),
        factors=factors,
        reason=reason[:500],
        evaluated_at=eval_ts,
    )
