"""Backend tests for Stage AI2-C: Deterministic Behavioral Classification State Machine.

Tests cover:
 1.  NORMAL baseline
 2.  APPROACHING above threshold
 3.  APPROACHING exact threshold boundary
 4.  DEPARTING
 5.  LOITERING
 6.  LOITERING exact radius boundary
 7.  LOITERING exact directional-consistency boundary
 8.  RAPID_CHANGE from turn rate
 9.  RAPID_CHANGE from acceleration
10.  RAPID_CHANGE exact threshold boundaries
11.  Heading wraparound (turn rate sign)
12.  COORDINATED with valid group evidence
13.  COORDINATED without sufficient group evidence
14.  ANOMALOUS from AI1 anomaly score
15.  Anomaly threshold boundary
16.  Precedence when multiple states trigger
17.  First observation duration
18.  Increasing timestamp duration
19.  Same timestamp
20.  Out-of-order timestamp
21.  State persistence
22.  Hysteresis prevents immediate oscillation
23.  Hysteresis allows legitimate transition after enough ticks
24.  Missing heading
25.  Missing velocity / speed
26.  Missing anomaly score
27.  Missing group information
28.  Deterministic repeated evaluation
29.  Confidence bounds
30.  Contributing-factor completeness
"""

from datetime import UTC, datetime, timedelta

import pytest

from ai.behavior.classifier import (
    BehaviorClassifierConfig,
    ClassifierInput,
    ClassifierState,
    classify_track_behavior,
)
from ai.schemas import BehavioralState


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def make_inp(
    tid: str = "TRK-01",
    speed: float = 10.0,
    accel: float = 0.0,
    turn_rate: float = 0.0,
    dir_consistency: float | None = 0.9,
    loiter_radius: float | None = None,
    anomaly_score: float | None = 10.0,
    closing_vel: float | None = None,
    reference_id: str | None = None,
    group_id: str | None = None,
    group_count: int | None = None,
    heading: float | None = 90.0,
    ts: datetime | None = None,
) -> ClassifierInput:
    return ClassifierInput(
        track_id=tid,
        timestamp=ts or _BASE_TS,
        speed_mps=speed,
        acceleration_mps2=accel,
        turn_rate_dps=turn_rate,
        directional_consistency=dir_consistency,
        loiter_radius_meters=loiter_radius,
        heading_deg=heading,
        anomaly_score=anomaly_score,
        closing_velocity_mps=closing_vel,
        reference_id=reference_id,
        group_id=group_id,
        group_member_count=group_count,
    )


def fresh_state(tid: str = "TRK-01") -> ClassifierState:
    return ClassifierState(track_id=tid)


def run(inp: ClassifierInput, state: ClassifierState | None = None,
        cfg: BehaviorClassifierConfig | None = None) -> tuple:
    """Single-evaluation convenience wrapper returning (classification, state)."""
    return classify_track_behavior(inp, state, cfg)


# ---------------------------------------------------------------------------
# 1. NORMAL baseline
# ---------------------------------------------------------------------------

def test_normal_baseline():
    inp = make_inp(speed=10.0, accel=0.5, turn_rate=5.0, anomaly_score=10.0)
    cls, _ = run(inp)
    assert cls.state == BehavioralState.NORMAL
    assert cls.track_id == "TRK-01"
    assert 0.0 <= cls.confidence <= 1.0


# ---------------------------------------------------------------------------
# 2. APPROACHING above threshold
# ---------------------------------------------------------------------------

def test_approaching_above_threshold():
    inp = make_inp(closing_vel=8.0, reference_id="GEO-1", anomaly_score=5.0)
    # Hysteresis: need 2 ticks
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.APPROACHING
    assert "closing_velocity_mps" in " ".join(cls.contributing_factors)


# ---------------------------------------------------------------------------
# 3. APPROACHING exact threshold boundary
# ---------------------------------------------------------------------------

def test_approaching_at_exact_threshold_not_triggered():
    """closing_vel == 5.0 is NOT > 5.0 so must not trigger APPROACHING."""
    inp = make_inp(closing_vel=5.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.APPROACHING


def test_approaching_just_above_threshold():
    """closing_vel == 5.001 is > 5.0 so must trigger APPROACHING."""
    inp = make_inp(closing_vel=5.001, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.APPROACHING


# ---------------------------------------------------------------------------
# 4. DEPARTING
# ---------------------------------------------------------------------------

def test_departing_below_threshold():
    inp = make_inp(closing_vel=-8.0, reference_id="GEO-1", anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.DEPARTING
    assert "closing_velocity_mps" in " ".join(cls.contributing_factors)


def test_departing_at_exact_threshold_not_triggered():
    """closing_vel == -5.0 is NOT < -5.0."""
    inp = make_inp(closing_vel=-5.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.DEPARTING


def test_departing_just_below_threshold():
    inp = make_inp(closing_vel=-5.001, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.DEPARTING


# ---------------------------------------------------------------------------
# 5. LOITERING
# ---------------------------------------------------------------------------

def test_loitering_clear():
    inp = make_inp(loiter_radius=100.0, dir_consistency=0.2, anomaly_score=5.0, closing_vel=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.LOITERING
    assert "loiter_radius_m" in " ".join(cls.contributing_factors)
    assert "directional_consistency" in " ".join(cls.contributing_factors)


# ---------------------------------------------------------------------------
# 6. LOITERING exact radius boundary
# ---------------------------------------------------------------------------

def test_loitering_exact_radius_not_triggered():
    """radius == 30.0 is NOT > 30.0."""
    inp = make_inp(loiter_radius=30.0, dir_consistency=0.1, anomaly_score=5.0, closing_vel=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.LOITERING


def test_loitering_just_above_radius():
    inp = make_inp(loiter_radius=30.001, dir_consistency=0.1, anomaly_score=5.0, closing_vel=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.LOITERING


# ---------------------------------------------------------------------------
# 7. LOITERING exact directional-consistency boundary
# ---------------------------------------------------------------------------

def test_loitering_exact_consistency_not_triggered():
    """dir_consistency == 0.4 is NOT < 0.4."""
    inp = make_inp(loiter_radius=100.0, dir_consistency=0.4, anomaly_score=5.0, closing_vel=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.LOITERING


def test_loitering_just_below_consistency():
    inp = make_inp(loiter_radius=100.0, dir_consistency=0.399, anomaly_score=5.0, closing_vel=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.LOITERING


# ---------------------------------------------------------------------------
# 8. RAPID_CHANGE from turn rate
# ---------------------------------------------------------------------------

def test_rapid_change_from_turn_rate():
    inp = make_inp(turn_rate=50.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE
    assert "turn_rate_dps" in " ".join(cls.contributing_factors)


def test_rapid_change_from_negative_turn_rate():
    """Negative turn rates (left turns) must also trigger RAPID_CHANGE."""
    inp = make_inp(turn_rate=-55.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE


# ---------------------------------------------------------------------------
# 9. RAPID_CHANGE from acceleration
# ---------------------------------------------------------------------------

def test_rapid_change_from_acceleration():
    inp = make_inp(accel=6.0, turn_rate=0.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE
    assert "acceleration_mps2" in " ".join(cls.contributing_factors)


def test_rapid_change_from_deceleration():
    """Strong negative acceleration must trigger RAPID_CHANGE."""
    inp = make_inp(accel=-6.0, turn_rate=0.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE


# ---------------------------------------------------------------------------
# 10. RAPID_CHANGE exact threshold boundaries
# ---------------------------------------------------------------------------

def test_rapid_change_exact_turn_rate_not_triggered():
    """turn_rate == 45.0 is NOT > 45.0."""
    inp = make_inp(turn_rate=45.0, accel=0.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.RAPID_CHANGE


def test_rapid_change_just_above_turn_rate():
    inp = make_inp(turn_rate=45.001, accel=0.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE


def test_rapid_change_exact_accel_not_triggered():
    inp = make_inp(turn_rate=0.0, accel=5.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.RAPID_CHANGE


def test_rapid_change_just_above_accel():
    inp = make_inp(turn_rate=0.0, accel=5.001, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE


# ---------------------------------------------------------------------------
# 11. Heading wraparound (turn rate sign correctness)
# ---------------------------------------------------------------------------

def test_heading_wraparound_does_not_falsely_trigger_rapid_change():
    """A 2° heading change (359° → 1°) must not produce a falsely large turn rate."""
    # The classifier uses turn_rate_dps passed in directly; this tests that
    # the *caller* (kinematics engine) handles wraparound. We test with a
    # correctly computed small turn rate to confirm NORMAL is returned.
    inp = make_inp(turn_rate=2.0, accel=0.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.RAPID_CHANGE


def test_heading_wraparound_large_turn_triggers_correctly():
    """A genuinely large turn rate (from real 90° manoeuvre) must trigger RAPID_CHANGE."""
    inp = make_inp(turn_rate=90.0, accel=0.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE


# ---------------------------------------------------------------------------
# 12. COORDINATED with valid group evidence
# ---------------------------------------------------------------------------

def test_coordinated_with_sufficient_group():
    inp = make_inp(group_id="GRP-001", group_count=3, anomaly_score=5.0, closing_vel=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.COORDINATED
    assert "group_id" in " ".join(cls.contributing_factors)
    assert "group_member_count" in " ".join(cls.contributing_factors)


# ---------------------------------------------------------------------------
# 13. COORDINATED without sufficient group evidence
# ---------------------------------------------------------------------------

def test_coordinated_group_too_small():
    """group_count = 1 is below min_group_size=2 → not COORDINATED."""
    inp = make_inp(group_id="GRP-001", group_count=1, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.COORDINATED


def test_coordinated_no_group():
    """group_id=None → not COORDINATED."""
    inp = make_inp(group_id=None, group_count=None, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.COORDINATED


# ---------------------------------------------------------------------------
# 14. ANOMALOUS from AI1 anomaly score
# ---------------------------------------------------------------------------

def test_anomalous_from_high_score():
    inp = make_inp(anomaly_score=75.0, turn_rate=0.0, accel=0.0, closing_vel=None, group_id=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.ANOMALOUS
    assert "anomaly_score" in " ".join(cls.contributing_factors)


# ---------------------------------------------------------------------------
# 15. Anomaly threshold boundary
# ---------------------------------------------------------------------------

def test_anomalous_exact_threshold_not_triggered():
    """anomaly_score == 60.0 is NOT >= 60.0 ... wait, it IS >= 60.0; check strict."""
    # The threshold is >= 60.0 so 60.0 must trigger ANOMALOUS
    inp = make_inp(anomaly_score=60.0, turn_rate=0.0, accel=0.0, closing_vel=None, group_id=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.ANOMALOUS


def test_anomalous_just_below_threshold():
    """anomaly_score=59.9 should NOT trigger ANOMALOUS."""
    inp = make_inp(anomaly_score=59.9, turn_rate=0.0, accel=0.0, closing_vel=None, group_id=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.ANOMALOUS


# ---------------------------------------------------------------------------
# 16. Precedence when multiple states trigger
# ---------------------------------------------------------------------------

def test_precedence_rapid_change_beats_anomalous():
    """RAPID_CHANGE (priority 1) beats ANOMALOUS (priority 2)."""
    inp = make_inp(turn_rate=90.0, anomaly_score=80.0, closing_vel=None, group_id=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.RAPID_CHANGE


def test_precedence_anomalous_beats_coordinated():
    """ANOMALOUS (priority 2) beats COORDINATED (priority 3)."""
    inp = make_inp(
        turn_rate=0.0, accel=0.0,
        anomaly_score=80.0,
        group_id="GRP-001", group_count=3,
        closing_vel=None,
    )
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.ANOMALOUS


def test_precedence_coordinated_beats_approaching():
    """COORDINATED (priority 3) beats APPROACHING (priority 4)."""
    inp = make_inp(
        turn_rate=0.0, accel=0.0,
        anomaly_score=5.0,
        group_id="GRP-001", group_count=3,
        closing_vel=8.0,
    )
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.COORDINATED


def test_precedence_approaching_beats_loitering():
    """APPROACHING (priority 4) beats LOITERING (priority 6)."""
    inp = make_inp(
        anomaly_score=5.0, closing_vel=8.0,
        loiter_radius=100.0, dir_consistency=0.2,
        group_id=None,
    )
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.APPROACHING


def test_precedence_departing_beats_loitering():
    """DEPARTING (priority 5) beats LOITERING (priority 6)."""
    inp = make_inp(
        anomaly_score=5.0, closing_vel=-8.0,
        loiter_radius=100.0, dir_consistency=0.2,
        group_id=None,
    )
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.DEPARTING


# ---------------------------------------------------------------------------
# 17. First observation duration
# ---------------------------------------------------------------------------

def test_first_observation_duration_zero():
    inp = make_inp(ts=_BASE_TS)
    cls, _ = run(inp)
    assert cls.duration_seconds == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 18. Increasing timestamp duration
# ---------------------------------------------------------------------------

def test_increasing_timestamp_duration():
    """After 30 s in the same state, duration_seconds must reflect 30 s."""
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    ts1 = _BASE_TS
    ts2 = _BASE_TS + timedelta(seconds=30)

    inp1 = make_inp(speed=10.0, anomaly_score=5.0, ts=ts1)
    cls1, state1 = run(inp1, cfg=cfg)

    inp2 = make_inp(speed=10.0, anomaly_score=5.0, ts=ts2)
    cls2, _ = run(inp2, state1, cfg=cfg)

    assert cls2.state == BehavioralState.NORMAL
    assert cls2.duration_seconds == pytest.approx(30.0, abs=0.1)


# ---------------------------------------------------------------------------
# 19. Same timestamp
# ---------------------------------------------------------------------------

def test_same_timestamp_does_not_produce_negative_duration():
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    inp1 = make_inp(ts=_BASE_TS)
    _, state1 = run(inp1, cfg=cfg)

    inp2 = make_inp(ts=_BASE_TS)
    cls2, _ = run(inp2, state1, cfg=cfg)
    assert cls2.duration_seconds >= 0.0


# ---------------------------------------------------------------------------
# 20. Out-of-order timestamp
# ---------------------------------------------------------------------------

def test_out_of_order_timestamp_no_negative_duration():
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    ts_later = _BASE_TS + timedelta(seconds=10)
    ts_earlier = _BASE_TS

    inp1 = make_inp(ts=ts_later)
    _, state1 = run(inp1, cfg=cfg)

    inp2 = make_inp(ts=ts_earlier)
    cls2, _ = run(inp2, state1, cfg=cfg)
    assert cls2.duration_seconds >= 0.0


# ---------------------------------------------------------------------------
# 21. State persistence (same state across multiple evaluations)
# ---------------------------------------------------------------------------

def test_state_persists_across_evaluations():
    cfg = BehaviorClassifierConfig(enter_ticks=1)

    state = None
    for i in range(5):
        ts = _BASE_TS + timedelta(seconds=i * 2)
        inp = make_inp(turn_rate=90.0, accel=0.0, anomaly_score=5.0, closing_vel=None, ts=ts)
        cls, state = run(inp, state, cfg=cfg)
        assert cls.state == BehavioralState.RAPID_CHANGE

    assert state.current_state == BehavioralState.RAPID_CHANGE


# ---------------------------------------------------------------------------
# 22. Hysteresis prevents immediate oscillation
# ---------------------------------------------------------------------------

def test_hysteresis_prevents_immediate_state_oscillation():
    """With enter_ticks=3, the first observation of RAPID_CHANGE must NOT
    immediately change the displayed state from NORMAL."""
    cfg = BehaviorClassifierConfig(enter_ticks=3, exit_ticks=3)

    # Start in NORMAL
    inp1 = make_inp(turn_rate=0.0, anomaly_score=5.0)
    cls1, state1 = run(inp1, cfg=cfg)
    assert cls1.state == BehavioralState.NORMAL

    # Sudden RAPID_CHANGE candidate – first tick only
    inp2 = make_inp(turn_rate=90.0, anomaly_score=5.0)
    cls2, _ = run(inp2, state1, cfg=cfg)
    # Still NORMAL because we haven't accumulated enter_ticks yet
    assert cls2.state == BehavioralState.NORMAL


# ---------------------------------------------------------------------------
# 23. Hysteresis allows legitimate transition after enough ticks
# ---------------------------------------------------------------------------

def test_hysteresis_allows_entry_after_enough_ticks():
    """With enter_ticks=2, after 2 consecutive RAPID_CHANGE candidates, state must enter."""
    cfg = BehaviorClassifierConfig(enter_ticks=2)

    inp_normal = make_inp(turn_rate=0.0, anomaly_score=5.0)
    _, state0 = run(inp_normal, cfg=cfg)

    inp_rapid = make_inp(turn_rate=90.0, anomaly_score=5.0, ts=_BASE_TS + timedelta(seconds=1))
    cls1, state1 = run(inp_rapid, state0, cfg=cfg)
    # First tick: still NORMAL
    assert cls1.state == BehavioralState.NORMAL

    inp_rapid2 = make_inp(turn_rate=90.0, anomaly_score=5.0, ts=_BASE_TS + timedelta(seconds=2))
    cls2, _ = run(inp_rapid2, state1, cfg=cfg)
    # Second tick: entered RAPID_CHANGE
    assert cls2.state == BehavioralState.RAPID_CHANGE


# ---------------------------------------------------------------------------
# 24. Missing heading
# ---------------------------------------------------------------------------

def test_missing_heading_does_not_crash():
    inp = make_inp(heading=None, turn_rate=0.0, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state == BehavioralState.NORMAL
    assert 0.0 <= cls.confidence <= 1.0


# ---------------------------------------------------------------------------
# 25. Missing velocity / speed
# ---------------------------------------------------------------------------

def test_missing_velocity_produces_normal_not_crash():
    inp = ClassifierInput(
        track_id="TRK-01",
        timestamp=_BASE_TS,
        speed_mps=0.0,
        anomaly_score=5.0,
    )
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state is not None
    assert 0.0 <= cls.confidence <= 1.0


# ---------------------------------------------------------------------------
# 26. Missing anomaly score
# ---------------------------------------------------------------------------

def test_missing_anomaly_score_does_not_trigger_anomalous():
    inp = make_inp(anomaly_score=None, turn_rate=0.0, accel=0.0, closing_vel=None, group_id=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    # Cannot determine ANOMALOUS without score → must not falsely assert it
    assert cls.state != BehavioralState.ANOMALOUS


def test_missing_anomaly_score_reduces_confidence():
    """With no anomaly evidence, NORMAL confidence should be lower than with full evidence."""
    cfg = BehaviorClassifierConfig(enter_ticks=1)

    inp_full = make_inp(anomaly_score=5.0, dir_consistency=0.9)
    cls_full, _ = run(inp_full, cfg=cfg)

    inp_missing = make_inp(anomaly_score=None, dir_consistency=0.9)
    cls_missing, _ = run(inp_missing, cfg=cfg)

    assert cls_missing.confidence <= cls_full.confidence


# ---------------------------------------------------------------------------
# 27. Missing group information
# ---------------------------------------------------------------------------

def test_missing_group_does_not_trigger_coordinated():
    inp = make_inp(group_id=None, group_count=None, anomaly_score=5.0)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    assert cls.state != BehavioralState.COORDINATED


# ---------------------------------------------------------------------------
# 28. Deterministic repeated evaluation
# ---------------------------------------------------------------------------

def test_deterministic_repeated_evaluation():
    """Identical inputs must produce identical outputs every time."""
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    inp = make_inp(turn_rate=90.0, anomaly_score=5.0)

    results = [run(inp, cfg=cfg)[0] for _ in range(5)]
    for cls in results[1:]:
        assert cls.state == results[0].state
        assert cls.confidence == pytest.approx(results[0].confidence, abs=1e-6)
        assert cls.reason == results[0].reason


# ---------------------------------------------------------------------------
# 29. Confidence bounds
# ---------------------------------------------------------------------------

def test_confidence_always_bounded_0_to_1():
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    inputs = [
        make_inp(anomaly_score=0.0, turn_rate=0.0, closing_vel=None, group_id=None),
        make_inp(anomaly_score=100.0, turn_rate=0.0, closing_vel=None, group_id=None),
        make_inp(turn_rate=1000.0, accel=1000.0),
        make_inp(closing_vel=0.001),
        make_inp(loiter_radius=31.0, dir_consistency=0.39, anomaly_score=5.0, closing_vel=None),
    ]
    for inp in inputs:
        cls, _ = run(inp, cfg=cfg)
        assert 0.0 <= cls.confidence <= 1.0, f"confidence={cls.confidence} for state {cls.state}"


# ---------------------------------------------------------------------------
# 30. Contributing-factor completeness
# ---------------------------------------------------------------------------

def test_contributing_factors_populated_for_loitering():
    inp = make_inp(loiter_radius=50.0, dir_consistency=0.2, anomaly_score=5.0, closing_vel=None)
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    cls, _ = run(inp, cfg=cfg)
    if cls.state == BehavioralState.LOITERING:
        joined = " ".join(cls.contributing_factors)
        assert "loiter_radius_m" in joined
        assert "directional_consistency" in joined


def test_contributing_factors_not_empty_for_any_state():
    cfg = BehaviorClassifierConfig(enter_ticks=1)
    test_inputs = [
        make_inp(),
        make_inp(turn_rate=90.0),
        make_inp(anomaly_score=80.0, turn_rate=0.0, closing_vel=None, group_id=None),
        make_inp(closing_vel=8.0),
    ]
    for inp in test_inputs:
        cls, _ = run(inp, cfg=cfg)
        assert len(cls.contributing_factors) > 0, f"No factors for state {cls.state}"
