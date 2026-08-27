"""Deterministic Behavioral Classification State Machine for individual airspace tracks.

PURPOSE
-------
This module classifies individual track observations into one of seven operationally
meaningful behavioral states for defensive situational-awareness purposes only:

  NORMAL        – Nominal airspace transit with no elevated indicators.
  APPROACHING   – Closing velocity toward a reference point/geofence > 5 m/s.
  DEPARTING     – Receding from a reference point/geofence with closing_vel < -5 m/s.
  LOITERING     – Circular/recurrent flight (loiter_radius > 30 m AND
                  directional_consistency < 0.4).
  RAPID_CHANGE  – Sudden kinematic manoeuvre: |turn_rate| > 45 °/s OR
                  |acceleration| > 5 m/s².
  COORDINATED   – Track is a member of a correlated group from AI2-B
                  (full coordination scoring belongs to AI2-D).
  ANOMALOUS     – AI1 instantaneous anomaly score >= 60.0 (HIGH threshold).

PRECEDENCE ORDER (deterministic, highest wins)
----------------------------------------------
1. RAPID_CHANGE   – Safety-critical kinematic signal, highest urgency.
2. ANOMALOUS      – Broad anomaly signal from AI1 scoring.
3. COORDINATED    – Group membership evidence (if available).
4. APPROACHING    – Closing-vector toward reference.
5. DEPARTING      – Receding from reference.
6. LOITERING      – Circular/holding pattern.
7. NORMAL         – Default when no higher-priority state is triggered.

HYSTERESIS
----------
To prevent threshold-boundary oscillation the classifier maintains per-track state.
A `ClassifierState` object tracks:
  - current state
  - consecutive ticks that the candidate state has been observed
  - consecutive ticks that a different state has been observed
  - state start timestamp (for duration_seconds)

Default thresholds:
  - enter_ticks = 2   (candidate must appear for 2 consecutive evaluations)
  - exit_ticks  = 3   (current state must be absent for 3 consecutive evaluations)

TEMPORAL SEMANTICS
------------------
`duration_seconds` uses the observation timestamp, not wall-clock time.
Out-of-order timestamps result in duration_seconds = 0.0 for that evaluation
(duration never goes negative).

DEFENSIVE BOUNDARY
------------------
This subsystem is strictly defensive situational-awareness classification.
It MUST NOT be used for weapon targeting, fire control, interception optimization,
jamming, countermeasure deployment, or engagement authorization.
"""

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, Sequence

from ai.schemas import BehaviorClassification, BehavioralState, TrackGroup


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class BehaviorClassifierConfig:
    """Configurable thresholds for the deterministic behavioral state machine."""

    # APPROACHING / DEPARTING
    approaching_closing_velocity_mps: float = 5.0   # closing_vel > this → APPROACHING
    departing_closing_velocity_mps: float = -5.0    # closing_vel < this → DEPARTING

    # LOITERING (both conditions must hold)
    loiter_min_radius_meters: float = 30.0
    loiter_max_directional_consistency: float = 0.4

    # RAPID_CHANGE (either condition triggers)
    rapid_change_turn_rate_dps: float = 45.0
    rapid_change_acceleration_mps2: float = 5.0

    # ANOMALOUS – reuse AI1 HIGH anomaly threshold (60.0 per AnomalyScoringConfig)
    anomalous_score_threshold: float = 60.0

    # COORDINATED – minimum group members to assert coordination
    coordinated_min_group_size: int = 2

    # Hysteresis
    enter_ticks: int = 2   # evaluations candidate must appear before state enters
    exit_ticks: int = 3    # evaluations state must be absent before it exits


# ─────────────────────────────────────────────────────────────────────────────
# Classifier Input
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClassifierInput:
    """All inputs required for a single behavioral classification evaluation.

    Fields mirror AI1 KinematicFeatures to allow direct reuse.
    Explicitly optional fields are None when unavailable; the classifier
    handles all missing-data cases without crashing or fabricating values.
    """

    track_id: str
    timestamp: datetime | None = None

    # Kinematics (from AI1 KinematicFeatures or raw observation)
    speed_mps: float = 0.0
    acceleration_mps2: float = 0.0
    turn_rate_dps: float = 0.0
    directional_consistency: float | None = None
    loiter_radius_meters: float | None = None
    heading_deg: float | None = None

    # Anomaly (from AI1 AnomalyAssessment – instantaneous score only)
    anomaly_score: float | None = None

    # Reference proximity (from GeofenceIngressEstimate or explicit point)
    # closing_velocity_mps: positive = closing in, negative = receding.
    # None if no spatial reference is available for this evaluation.
    closing_velocity_mps: float | None = None
    reference_id: str | None = None    # geofence_id or spatial reference label

    # Group membership (from AI2-B TrackGroup; None if ungrouped)
    group_id: str | None = None
    group_member_count: int | None = None


def classifier_input_from_ai1(
    track_id: str,
    features: Any,
    anomaly_assessment: Any | None = None,
    ingress_estimates: Sequence[Any] | None = None,
    group: TrackGroup | None = None,
    timestamp: datetime | None = None,
) -> ClassifierInput:
    """Build a ClassifierInput from AI1 KinematicFeatures, AnomalyAssessment, and optional group."""
    # Derive closest approaching reference (lowest positive TTB or first APPROACHING status)
    closing_vel: float | None = None
    reference_id: str | None = None
    if ingress_estimates:
        approaching = [
            e for e in ingress_estimates
            if getattr(e, "status", None) in ("APPROACHING", "INSIDE")
        ]
        if approaching:
            first = approaching[0]
            ttb = getattr(first, "estimated_time_to_breach_seconds", None)
            speed = getattr(features, "speed_mps", 0.0)
            if ttb is not None and ttb > 0.0 and speed is not None:
                closing_vel = float(speed)
            reference_id = getattr(first, "geofence_id", None)

        if closing_vel is None:
            departing = [
                e for e in ingress_estimates
                if getattr(e, "status", None) == "DIVERGING"
            ]
            if departing:
                speed = getattr(features, "speed_mps", 0.0)
                if speed is not None:
                    closing_vel = -float(speed)
                reference_id = getattr(departing[0], "geofence_id", None)

    return ClassifierInput(
        track_id=track_id,
        timestamp=timestamp,
        speed_mps=float(getattr(features, "speed_mps", 0.0)),
        acceleration_mps2=float(getattr(features, "acceleration_mps2", 0.0)),
        turn_rate_dps=float(getattr(features, "turn_rate_dps", 0.0)),
        directional_consistency=float(getattr(features, "directional_consistency", 1.0))
            if getattr(features, "directional_consistency", None) is not None else None,
        loiter_radius_meters=float(getattr(features, "loiter_radius_meters", None))
            if getattr(features, "loiter_radius_meters", None) is not None else None,
        heading_deg=float(getattr(features, "heading_deg", None))
            if getattr(features, "heading_deg", None) is not None else None,
        anomaly_score=float(getattr(anomaly_assessment, "anomaly_score", None))
            if anomaly_assessment is not None else None,
        closing_velocity_mps=closing_vel,
        reference_id=reference_id,
        group_id=group.group_id if group is not None else None,
        group_member_count=group.member_count if group is not None else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Persistent State Machine State
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ClassifierState:
    """Persistent per-track hysteresis state for the behavioral state machine.

    Must be created once per track and passed across evaluations to enable
    hysteresis-based state transitions and accurate duration_seconds tracking.
    """

    track_id: str
    current_state: BehavioralState = BehavioralState.NORMAL
    state_start_ts: datetime | None = None

    # Hysteresis counters
    candidate_state: BehavioralState | None = None
    candidate_ticks: int = 0
    exit_candidate: BehavioralState | None = None
    exit_ticks_count: int = 0

    previous_state: BehavioralState | None = None
    last_transition_ts: datetime | None = None


# ─────────────────────────────────────────────────────────────────────────────
# Candidate state evaluation
# ─────────────────────────────────────────────────────────────────────────────

def _evaluate_candidate_state(
    inp: ClassifierInput,
    cfg: BehaviorClassifierConfig,
) -> tuple[BehavioralState, float, str, list[str]]:
    """Return (candidate_state, confidence, reason, contributing_factors).

    Evaluates each state in precedence order and returns the first that fires,
    together with its confidence and explainability metadata.
    """
    factors: list[str] = []
    confidence: float = 1.0

    # ── 1. RAPID_CHANGE ──────────────────────────────────────────────────────
    turn_abs = abs(inp.turn_rate_dps)
    accel_abs = abs(inp.acceleration_mps2)

    rapid_turn = turn_abs > cfg.rapid_change_turn_rate_dps
    rapid_accel = accel_abs > cfg.rapid_change_acceleration_mps2

    if rapid_turn or rapid_accel:
        if rapid_turn:
            factors.append(f"turn_rate_dps={inp.turn_rate_dps:.2f}")
        if rapid_accel:
            factors.append(f"acceleration_mps2={inp.acceleration_mps2:.2f}")
        # Confidence scales with how far above threshold
        excess_turn = max(0.0, (turn_abs - cfg.rapid_change_turn_rate_dps) / cfg.rapid_change_turn_rate_dps)
        excess_accel = max(0.0, (accel_abs - cfg.rapid_change_acceleration_mps2) / cfg.rapid_change_acceleration_mps2)
        confidence = min(1.0, 0.7 + 0.3 * max(excess_turn, excess_accel))
        reason = (
            f"Rapid kinematic change detected: "
            f"turn_rate={inp.turn_rate_dps:.1f} °/s, "
            f"acceleration={inp.acceleration_mps2:.1f} m/s²"
        )
        return BehavioralState.RAPID_CHANGE, round(confidence, 3), reason, factors

    # ── 2. ANOMALOUS ─────────────────────────────────────────────────────────
    if inp.anomaly_score is not None:
        if inp.anomaly_score >= cfg.anomalous_score_threshold:
            factors.append(f"anomaly_score={inp.anomaly_score:.1f}")
            confidence = min(1.0, inp.anomaly_score / 100.0)
            reason = (
                f"AI1 instantaneous anomaly score {inp.anomaly_score:.1f} "
                f">= threshold {cfg.anomalous_score_threshold:.1f}"
            )
            return BehavioralState.ANOMALOUS, round(confidence, 3), reason, factors
    # Missing anomaly score: skip without asserting NORMAL

    # ── 3. COORDINATED ───────────────────────────────────────────────────────
    if (
        inp.group_id is not None
        and inp.group_member_count is not None
        and inp.group_member_count >= cfg.coordinated_min_group_size
    ):
        factors.append(f"group_id={inp.group_id}")
        factors.append(f"group_member_count={inp.group_member_count}")
        confidence = min(1.0, 0.5 + 0.1 * inp.group_member_count)
        reason = (
            f"Track is member of correlated group {inp.group_id} "
            f"({inp.group_member_count} members) from AI2-B spatial grouping. "
            f"Full coordination scoring deferred to AI2-D."
        )
        return BehavioralState.COORDINATED, round(confidence, 3), reason, factors

    # ── 4. APPROACHING ───────────────────────────────────────────────────────
    if inp.closing_velocity_mps is not None:
        if inp.closing_velocity_mps > cfg.approaching_closing_velocity_mps:
            factors.append(f"closing_velocity_mps={inp.closing_velocity_mps:.2f}")
            if inp.reference_id:
                factors.append(f"reference_id={inp.reference_id}")
            excess = (inp.closing_velocity_mps - cfg.approaching_closing_velocity_mps)
            confidence = min(1.0, 0.6 + 0.04 * excess)
            reason = (
                f"Closing velocity {inp.closing_velocity_mps:.1f} m/s "
                f"> threshold {cfg.approaching_closing_velocity_mps:.1f} m/s"
                + (f" toward {inp.reference_id}" if inp.reference_id else "")
            )
            return BehavioralState.APPROACHING, round(confidence, 3), reason, factors

    # ── 5. DEPARTING ─────────────────────────────────────────────────────────
    if inp.closing_velocity_mps is not None:
        if inp.closing_velocity_mps < cfg.departing_closing_velocity_mps:
            factors.append(f"closing_velocity_mps={inp.closing_velocity_mps:.2f}")
            if inp.reference_id:
                factors.append(f"reference_id={inp.reference_id}")
            excess = abs(inp.closing_velocity_mps) - abs(cfg.departing_closing_velocity_mps)
            confidence = min(1.0, 0.6 + 0.04 * excess)
            reason = (
                f"Receding velocity {inp.closing_velocity_mps:.1f} m/s "
                f"< threshold {cfg.departing_closing_velocity_mps:.1f} m/s"
                + (f" from {inp.reference_id}" if inp.reference_id else "")
            )
            return BehavioralState.DEPARTING, round(confidence, 3), reason, factors

    # When no reference is available, neither APPROACHING nor DEPARTING can be
    # determined.  The classifier does not fabricate a closing vector.

    # ── 6. LOITERING ─────────────────────────────────────────────────────────
    if (
        inp.loiter_radius_meters is not None
        and inp.directional_consistency is not None
        and inp.loiter_radius_meters > cfg.loiter_min_radius_meters
        and inp.directional_consistency < cfg.loiter_max_directional_consistency
    ):
        factors.append(f"loiter_radius_m={inp.loiter_radius_meters:.1f}")
        factors.append(f"directional_consistency={inp.directional_consistency:.3f}")
        radius_excess = (inp.loiter_radius_meters - cfg.loiter_min_radius_meters) / cfg.loiter_min_radius_meters
        consistency_deficit = cfg.loiter_max_directional_consistency - inp.directional_consistency
        confidence = min(1.0, 0.6 + 0.2 * min(1.0, radius_excess) + 0.2 * min(1.0, consistency_deficit / 0.4))
        reason = (
            f"Loitering pattern: radius {inp.loiter_radius_meters:.1f} m "
            f"> {cfg.loiter_min_radius_meters:.1f} m, "
            f"directional_consistency {inp.directional_consistency:.3f} "
            f"< {cfg.loiter_max_directional_consistency:.1f}"
        )
        return BehavioralState.LOITERING, round(confidence, 3), reason, factors

    # ── 7. NORMAL ────────────────────────────────────────────────────────────
    # Report relative evidence strength for NORMAL confidence.
    has_kinematics = inp.directional_consistency is not None
    has_anomaly = inp.anomaly_score is not None
    evidence_count = sum([True, has_kinematics, has_anomaly])
    confidence = round(evidence_count / 3.0, 3)
    factors.append(f"speed_mps={inp.speed_mps:.2f}")
    if inp.directional_consistency is not None:
        factors.append(f"directional_consistency={inp.directional_consistency:.3f}")
    reason = "No elevated behavioral indicators detected; nominal airspace transit."
    return BehavioralState.NORMAL, confidence, reason, factors


# ─────────────────────────────────────────────────────────────────────────────
# Public classification API
# ─────────────────────────────────────────────────────────────────────────────

def classify_track_behavior(
    inp: ClassifierInput,
    state: ClassifierState | None = None,
    config: BehaviorClassifierConfig | None = None,
) -> tuple[BehaviorClassification, ClassifierState]:
    """Classify a track's behavioral state with hysteresis and duration tracking.

    Parameters
    ----------
    inp:    Current observation inputs.
    state:  Persistent per-track state from the previous evaluation, or None
            for the first evaluation (a fresh ClassifierState is created).
    config: Configuration overrides, or None to use defaults.

    Returns
    -------
    (BehaviorClassification, updated ClassifierState)
    """
    cfg = config or BehaviorClassifierConfig()
    if state is None:
        state = ClassifierState(track_id=inp.track_id)

    eval_ts = inp.timestamp or datetime.now(UTC)

    candidate, candidate_conf, candidate_reason, candidate_factors = _evaluate_candidate_state(inp, cfg)

    # ── Hysteresis state machine ──────────────────────────────────────────────
    # A candidate state must be observed for `enter_ticks` consecutive evaluations
    # before it becomes the current state.
    # enter_ticks=1  → immediate (any single observation suffices)
    # enter_ticks=2  → one prior observation of the same candidate required
    #
    # Algorithm:
    #   1. Determine how many consecutive ticks this candidate has been seen.
    #   2. If ticks >= enter_ticks → enter the new state.
    #   3. Otherwise → accumulate and report current stable state.

    new_state = state.current_state

    if candidate == state.current_state:
        # Already in this state; reset pending-candidate counters
        pending_candidate = None
        candidate_ticks = 0
        exit_candidate = None
        exit_ticks_count = 0
    else:
        # Candidate differs; accumulate ticks
        if candidate == state.candidate_state:
            accumulated_ticks = state.candidate_ticks + 1
        else:
            accumulated_ticks = 1  # fresh candidate

        if accumulated_ticks >= cfg.enter_ticks:
            # Threshold reached → transition to new state
            new_state = candidate
            pending_candidate = None
            candidate_ticks = 0
            exit_candidate = None
            exit_ticks_count = 0
        else:
            # Still accumulating
            pending_candidate = candidate
            candidate_ticks = accumulated_ticks
            # Track exit for current stable state
            if state.exit_candidate == state.current_state:
                exit_ticks_count = state.exit_ticks_count + 1
                exit_candidate = state.exit_candidate
            else:
                exit_candidate = state.current_state
                exit_ticks_count = 1

    # If we are transitioning to a new state, update start timestamp
    if new_state != state.current_state:
        state_start_ts = eval_ts
        previous_state = state.current_state
    else:
        state_start_ts = state.state_start_ts or eval_ts
        previous_state = state.previous_state

    # Duration: non-negative, based on observation timestamps
    if state_start_ts is not None and eval_ts >= state_start_ts:
        duration_seconds = (eval_ts - state_start_ts).total_seconds()
    else:
        duration_seconds = 0.0

    updated_state = ClassifierState(
        track_id=inp.track_id,
        current_state=new_state,
        state_start_ts=state_start_ts,
        candidate_state=pending_candidate if new_state == state.current_state else None,
        candidate_ticks=candidate_ticks if new_state == state.current_state else 0,
        exit_candidate=exit_candidate if new_state == state.current_state else None,
        exit_ticks_count=exit_ticks_count if new_state == state.current_state else 0,
        previous_state=previous_state,
        last_transition_ts=eval_ts if new_state != state.current_state else state.last_transition_ts,
    )

    # When waiting in hysteresis (haven't entered new state yet), report the
    # *current* stable state with its existing evidence so operators see continuity.
    reported_state = new_state
    if reported_state == state.current_state and pending_candidate is not None:
        # Currently in hysteresis accumulation — surface current stable state
        # with candidate reason as a hint in contributing_factors
        classification_reason = (
            f"{candidate_reason} [hysteresis: {candidate_ticks}/{cfg.enter_ticks} ticks toward {candidate.value}]"
        )
        classification_factors = candidate_factors + [f"pending_state={candidate.value}"]
        classification_confidence = round(candidate_conf * 0.8, 3)  # lower confidence during transition
    else:
        classification_reason = candidate_reason if reported_state == candidate else (
            f"State {reported_state.value} maintained (candidate {candidate.value} pending hysteresis)"
        )
        classification_factors = candidate_factors
        classification_confidence = candidate_conf

    result = BehaviorClassification(
        track_id=inp.track_id,
        state=reported_state,
        confidence=max(0.0, min(1.0, classification_confidence)),
        duration_seconds=round(duration_seconds, 2),
        reason=classification_reason[:500],
        contributing_factors=classification_factors,
        evaluated_at=eval_ts,
    )

    return result, updated_state
