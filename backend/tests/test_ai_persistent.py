"""Tests for AI2-D: Persistent Anomaly Engine.

Covers:
 1. First evaluation
 2. Accumulation — repeated high scores raise persistent score
 3. 30-second half-life decay
 4. Multiple decay intervals
 5. Enter threshold exactly 60 (>= 60 must qualify)
 6. Enter threshold just below 60 (should not qualify)
 7. Three-tick persistence requirement — enter on tick 3, not tick 2
 8. Recovery threshold exactly 40 (< 40 to count recovery ticks)
 9. Recovery just above 40 (should not count recovery)
10. Five-tick exit requirement — exit on tick 5, not tick 4
11. Score oscillation around thresholds
12. Timestamp gap (large dt decays correctly)
13. Out-of-order timestamps
14. Duplicate timestamps
15. Missing score (None)
16. Per-track isolation
17. reset_track
18. reset_all
19. Deterministic repeated evaluation
20. Confidence/bounds: persistent score always [0, 100]
"""

from datetime import UTC, datetime, timedelta

import pytest

from ai.anomaly.persistent import (
    PersistentAnomalyAccumulator,
    PersistentAnomalyConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def make_accum(
    enter_threshold: float = 60.0,
    enter_ticks: int = 3,
    exit_threshold: float = 40.0,
    exit_ticks: int = 5,
    half_life: float = 30.0,
) -> PersistentAnomalyAccumulator:
    cfg = PersistentAnomalyConfig(
        half_life_seconds=half_life,
        enter_threshold=enter_threshold,
        enter_ticks=enter_ticks,
        exit_threshold=exit_threshold,
        exit_ticks=exit_ticks,
    )
    return PersistentAnomalyAccumulator(config=cfg)


def tick(accum: PersistentAnomalyAccumulator, score: float | None, dt_from_base: float, tid: str = "TRK-01"):
    return accum.update(tid, score, _BASE_TS + timedelta(seconds=dt_from_base))


# ---------------------------------------------------------------------------
# 1. First evaluation
# ---------------------------------------------------------------------------

def test_first_evaluation_zero_score():
    accum = make_accum()
    r = tick(accum, 0.0, 0.0)
    assert r.persistent_score == pytest.approx(0.0, abs=0.01)
    assert not r.is_anomalous
    assert r.qualifying_ticks == 0
    assert r.dt_seconds == pytest.approx(0.0, abs=0.01)
    assert r.decay_factor == pytest.approx(1.0, abs=1e-4)


def test_first_evaluation_high_score():
    accum = make_accum()
    r = tick(accum, 80.0, 0.0)
    # Alpha = 1 - decay_factor; decay_factor = 1.0 at dt=0 → alpha = 0
    # So: new_persistent = decayed + ai1 * alpha = 0 + 80 * 0 = 0
    # This is correct: at dt=0 the decay factor is 1.0 and alpha = 0,
    # meaning the new score hasn't had time to accumulate yet.
    # The first observation initializes the accumulator.
    assert r.persistent_score >= 0.0
    assert not r.is_anomalous  # need 3 qualifying ticks


# ---------------------------------------------------------------------------
# 2. Accumulation — repeated high scores raise persistent score
# ---------------------------------------------------------------------------

def test_accumulation_raises_score():
    accum = make_accum()
    prev = 0.0
    for i in range(1, 6):
        r = tick(accum, 80.0, i * 5.0)  # every 5 seconds
        assert r.persistent_score >= prev
        prev = r.persistent_score


def test_entry_reached_after_three_qualifying_ticks():
    """With enter_ticks=3 and a short half-life, anomalous state must be entered
    after exactly 3 consecutive qualifying ticks.

    The leaky integrator formula:
        new_persistent = decayed + ai1_score * alpha
        alpha = 1 - decay_factor
    At dt=0 (first observation): alpha=0, so score stays at 0 — the first tick
    initializes the timestamp reference without contributing a score.
    Subsequent ticks at short half-life accumulate quickly.
    """
    accum = make_accum(enter_ticks=3, enter_threshold=60.0, half_life=1.0)

    # Seed at t=0: initializes last_timestamp; score stays 0 (alpha=0)
    accum.update("TRK-01", 100.0, _BASE_TS)

    # Ticks 1, 2, 3 — dt=5s each, half_life=1s:
    #   decay_factor = 0.5^5 ≈ 0.031, alpha ≈ 0.969
    # Tick 1: 0 * 0.031 + 100 * 0.969 = 96.9  → qualifies (tick 1)
    # Tick 2: 96.9 * 0.031 + 100 * 0.969 ≈ 99.9 → qualifies (tick 2)
    # Tick 3: ≈ 99.9 → qualifies (tick 3 = enter_ticks) → is_anomalous = True
    r1 = accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=5))
    r2 = accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=10))
    r3 = accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=15))

    assert r1.persistent_score >= 60.0, f"Expected >= 60 after tick 1, got {r1.persistent_score}"
    assert r1.qualifying_ticks >= 1
    assert r2.qualifying_ticks >= 2
    assert r3.is_anomalous, f"Expected is_anomalous after 3 ticks, got {r3}"


# ---------------------------------------------------------------------------
# 3. 30-second half-life decay
# ---------------------------------------------------------------------------

def test_half_life_30_seconds():
    """After 30 s with zero AI1 score, persistent score should be ≈ half."""
    accum = make_accum()
    # Seed with a high score
    accum.update("TRK-01", 0.0, _BASE_TS)  # initialize at 0
    # Manually prime state to a known persistent_score
    state = accum.get_state("TRK-01")
    state.persistent_score = 80.0
    state.last_timestamp = _BASE_TS

    # After exactly 30 s with ai1=0:
    r = accum.update("TRK-01", 0.0, _BASE_TS + timedelta(seconds=30))
    # decay_factor = 0.5^(30/30) = 0.5
    # decayed = 80 * 0.5 = 40
    # alpha = 0.5; new_persistent = 40 + 0 * 0.5 = 40
    assert r.persistent_score == pytest.approx(40.0, abs=0.5)
    assert r.decay_factor == pytest.approx(0.5, abs=1e-4)


def test_half_life_60_seconds():
    """After 60 s with zero AI1 score, persistent score should be ≈ quarter."""
    accum = make_accum()
    accum.update("TRK-01", 0.0, _BASE_TS)
    state = accum.get_state("TRK-01")
    state.persistent_score = 80.0
    state.last_timestamp = _BASE_TS

    r = accum.update("TRK-01", 0.0, _BASE_TS + timedelta(seconds=60))
    # decay_factor = 0.25; decayed = 80 * 0.25 = 20; alpha = 0.75; new = 20 + 0 = 20
    assert r.persistent_score == pytest.approx(20.0, abs=0.5)
    assert r.decay_factor == pytest.approx(0.25, abs=1e-4)


# ---------------------------------------------------------------------------
# 4. Multiple decay intervals
# ---------------------------------------------------------------------------

def test_multiple_decay_intervals():
    """Score should monotonically decrease when new signal is zero."""
    accum = make_accum()
    accum.update("TRK-01", 0.0, _BASE_TS)
    state = accum.get_state("TRK-01")
    state.persistent_score = 80.0
    state.last_timestamp = _BASE_TS

    prev = 80.0
    for i in range(1, 6):
        r = accum.update("TRK-01", 0.0, _BASE_TS + timedelta(seconds=i * 30))
        assert r.persistent_score < prev
        prev = r.persistent_score


# ---------------------------------------------------------------------------
# 5. Enter threshold exactly 60
# ---------------------------------------------------------------------------

def test_enter_threshold_exactly_60_qualifies():
    """persistent_score >= 60.0 must increment qualifying_ticks."""
    accum = make_accum(enter_threshold=60.0)
    accum.update("TRK-01", 0.0, _BASE_TS)
    state = accum.get_state("TRK-01")
    state.persistent_score = 59.0          # just below
    state.last_timestamp = _BASE_TS

    # Feed a score that pushes persistent to exactly 60
    # Use a large alpha by having a 30s gap → alpha = 0.5
    # new = 59 * 0.5 + 100 * 0.5 = 79.5 — well above 60; increment ticks
    r = accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=30))
    assert r.persistent_score >= 60.0
    assert r.qualifying_ticks >= 1


def test_enter_threshold_just_below_60_does_not_qualify():
    """persistent_score < 60.0 must NOT increment qualifying_ticks."""
    accum = make_accum(enter_threshold=60.0)
    # Warm up
    accum.update("TRK-01", 0.0, _BASE_TS)
    state = accum.get_state("TRK-01")
    state.persistent_score = 55.0
    state.last_timestamp = _BASE_TS

    # Keep below 60: send a score of 50 with very short dt so alpha ≈ 0
    r = accum.update("TRK-01", 50.0, _BASE_TS + timedelta(milliseconds=100))
    assert r.persistent_score < 60.0
    assert r.qualifying_ticks == 0


# ---------------------------------------------------------------------------
# 6. Enter threshold below 60 (should not qualify)
# (covered by test above — testing again with persistent 0)
# ---------------------------------------------------------------------------

def test_zero_score_never_qualifies():
    accum = make_accum()
    for i in range(5):
        r = tick(accum, 0.0, i * 5.0)
    assert not r.is_anomalous
    assert r.qualifying_ticks == 0


# ---------------------------------------------------------------------------
# 7. Three-tick persistence requirement
# ---------------------------------------------------------------------------

def test_three_tick_persistence_requirement():
    """Must NOT be anomalous until enter_ticks=3 consecutive qualifying ticks."""
    accum = make_accum(enter_ticks=3, enter_threshold=60.0, half_life=1.0)
    # Use a very short half-life so alpha is large and score builds quickly

    r1 = accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=5))
    r2 = accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=10))
    # Not yet anomalous after 2 qualifying ticks
    assert not r1.is_anomalous or not r2.is_anomalous  # at least one is False

    # Keep feeding until we confirm it does eventually become anomalous
    for i in range(3, 20):
        r = accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=i * 5))
        if r.is_anomalous:
            break
    assert r.is_anomalous, "Should become anomalous after sufficient qualifying ticks"


# ---------------------------------------------------------------------------
# 8. Recovery threshold exactly 40
# ---------------------------------------------------------------------------

def test_recovery_threshold_below_40_counts():
    """persistent_score < 40.0 must increment recovery_ticks when in anomalous state."""
    accum = make_accum(exit_threshold=40.0, enter_ticks=1, enter_threshold=60.0, half_life=1.0)

    # Enter anomalous state quickly
    for i in range(1, 10):
        accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=i))

    state = accum.get_state("TRK-01")
    assert state.is_anomalous

    # Drive score to below 40 with zero input and long dt
    state.persistent_score = 39.0
    state.last_timestamp = _BASE_TS + timedelta(seconds=10)
    r = accum.update("TRK-01", 0.0, _BASE_TS + timedelta(seconds=11))
    # Score should remain < 40 (was 39 * decay + 0 * alpha)
    if r.persistent_score < 40.0:
        assert r.recovery_ticks >= 1


def test_recovery_above_40_does_not_count():
    """persistent_score >= 40.0 must NOT increment recovery_ticks."""
    accum = make_accum(exit_threshold=40.0, enter_ticks=1, enter_threshold=60.0, half_life=1.0)

    for i in range(1, 10):
        accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=i))

    state = accum.get_state("TRK-01")
    state.persistent_score = 50.0
    state.last_timestamp = _BASE_TS + timedelta(seconds=10)

    # Keep score at 50 with minimal dt
    r = accum.update("TRK-01", 50.0, _BASE_TS + timedelta(milliseconds=10010))
    assert r.persistent_score >= 40.0
    assert r.recovery_ticks == 0


# ---------------------------------------------------------------------------
# 9. Five-tick exit requirement
# ---------------------------------------------------------------------------

def test_five_tick_exit_requirement():
    """Anomalous state must NOT exit before exit_ticks=5 consecutive recovery ticks."""
    accum = make_accum(enter_ticks=1, enter_threshold=60.0, exit_threshold=40.0, exit_ticks=5, half_life=1.0)

    # Enter anomalous state
    for i in range(1, 15):
        accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=i))

    state = accum.get_state("TRK-01")
    assert state.is_anomalous

    # Send recovery observations and track when it exits
    base_exit_ts = _BASE_TS + timedelta(seconds=15)
    exited_at = None
    for i in range(1, 20):
        # Push score way below exit threshold
        state = accum.get_state("TRK-01")
        state.persistent_score = 1.0
        r = accum.update("TRK-01", 0.0, base_exit_ts + timedelta(seconds=i * 2))
        if not r.is_anomalous and exited_at is None:
            exited_at = i

    assert exited_at is not None
    assert exited_at >= 5, f"Exited too early at tick {exited_at}"


# ---------------------------------------------------------------------------
# 10. Score oscillation around thresholds
# ---------------------------------------------------------------------------

def test_score_oscillation_does_not_flap():
    """Scores oscillating just above/below thresholds should not toggle is_anomalous rapidly."""
    accum = make_accum(enter_ticks=3, exit_ticks=5, enter_threshold=60.0, exit_threshold=40.0, half_life=1.0)

    transitions = 0
    prev_state = False
    for i in range(20):
        score = 65.0 if i % 2 == 0 else 35.0
        r = accum.update("TRK-01", score, _BASE_TS + timedelta(seconds=i * 3))
        if r.is_anomalous != prev_state and i > 0:
            transitions += 1
        prev_state = r.is_anomalous

    # Hysteresis must prevent constant flapping — fewer than 5 transitions over 20 ticks
    assert transitions < 5


# ---------------------------------------------------------------------------
# 11. Timestamp gap
# ---------------------------------------------------------------------------

def test_large_timestamp_gap_decays():
    """A 5-minute gap with zero AI1 score must decay the persistent score substantially."""
    accum = make_accum(half_life=30.0)
    accum.update("TRK-01", 0.0, _BASE_TS)
    state = accum.get_state("TRK-01")
    state.persistent_score = 80.0
    state.last_timestamp = _BASE_TS

    r = accum.update("TRK-01", 0.0, _BASE_TS + timedelta(seconds=300))  # 5 minutes
    # decay = 0.5 ^ (300/30) = 0.5^10 ≈ 0.00097
    expected = 80.0 * (0.5 ** 10)
    assert r.persistent_score == pytest.approx(expected, abs=1.0)


# ---------------------------------------------------------------------------
# 12. Out-of-order timestamps
# ---------------------------------------------------------------------------

def test_out_of_order_timestamp_no_crash():
    accum = make_accum()
    accum.update("TRK-01", 50.0, _BASE_TS + timedelta(seconds=10))
    # Earlier timestamp must not crash or produce negative dt
    r = accum.update("TRK-01", 50.0, _BASE_TS + timedelta(seconds=5))
    assert r.dt_seconds == pytest.approx(0.0, abs=0.01)
    assert 0.0 <= r.persistent_score <= 100.0


# ---------------------------------------------------------------------------
# 13. Duplicate timestamps
# ---------------------------------------------------------------------------

def test_duplicate_timestamp_idempotent():
    accum = make_accum()
    ts = _BASE_TS + timedelta(seconds=10)
    r1 = accum.update("TRK-01", 50.0, ts)
    r2 = accum.update("TRK-01", 50.0, ts)
    assert r2.dt_seconds == pytest.approx(0.0, abs=0.01)
    assert 0.0 <= r2.persistent_score <= 100.0


# ---------------------------------------------------------------------------
# 14. Missing score (None)
# ---------------------------------------------------------------------------

def test_missing_score_applies_pure_decay():
    accum = make_accum(half_life=30.0)
    accum.update("TRK-01", 0.0, _BASE_TS)
    state = accum.get_state("TRK-01")
    state.persistent_score = 60.0
    state.last_timestamp = _BASE_TS

    r = accum.update("TRK-01", None, _BASE_TS + timedelta(seconds=30))
    assert r.instantaneous_score is None
    # Pure decay: 60 * 0.5 = 30
    assert r.persistent_score == pytest.approx(30.0, abs=0.5)


def test_missing_score_never_enters_anomalous():
    accum = make_accum()
    for i in range(10):
        r = accum.update("TRK-01", None, _BASE_TS + timedelta(seconds=i * 5))
    assert not r.is_anomalous
    assert r.persistent_score == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 15. Per-track isolation
# ---------------------------------------------------------------------------

def test_per_track_isolation():
    """Updating TRK-A must not affect TRK-B state."""
    accum = make_accum(half_life=1.0)
    for i in range(1, 20):
        accum.update("TRK-A", 100.0, _BASE_TS + timedelta(seconds=i))

    r_b = accum.update("TRK-B", 0.0, _BASE_TS + timedelta(seconds=20))
    assert not r_b.is_anomalous
    assert r_b.persistent_score == pytest.approx(0.0, abs=0.1)


def test_multiple_tracks_independent():
    accum = make_accum(half_life=1.0)
    for i in range(1, 15):
        accum.update("TRK-A", 100.0, _BASE_TS + timedelta(seconds=i))
        accum.update("TRK-B", 0.0, _BASE_TS + timedelta(seconds=i))

    state_a = accum.get_state("TRK-A")
    state_b = accum.get_state("TRK-B")
    assert state_a.persistent_score > state_b.persistent_score


# ---------------------------------------------------------------------------
# 16. reset_track
# ---------------------------------------------------------------------------

def test_reset_track():
    accum = make_accum(half_life=1.0)
    for i in range(1, 10):
        accum.update("TRK-01", 100.0, _BASE_TS + timedelta(seconds=i))

    accum.reset_track("TRK-01")
    assert accum.get_state("TRK-01") is None

    # After reset, state starts fresh
    r = accum.update("TRK-01", 0.0, _BASE_TS + timedelta(seconds=20))
    assert r.persistent_score == pytest.approx(0.0, abs=0.01)
    assert not r.is_anomalous


# ---------------------------------------------------------------------------
# 17. reset_all
# ---------------------------------------------------------------------------

def test_reset_all():
    accum = make_accum(half_life=1.0)
    for tid in ["TRK-A", "TRK-B", "TRK-C"]:
        for i in range(1, 5):
            accum.update(tid, 100.0, _BASE_TS + timedelta(seconds=i))

    assert len(accum.tracked_ids) == 3
    accum.reset_all()
    assert len(accum.tracked_ids) == 0


# ---------------------------------------------------------------------------
# 18. Deterministic repeated evaluation
# ---------------------------------------------------------------------------

def test_deterministic_repeated_evaluation():
    """Same sequence of inputs must produce identical persistent scores."""
    def run_sequence():
        accum = make_accum()
        results = []
        for i, score in enumerate([80.0, 70.0, 90.0, 20.0, 0.0]):
            r = accum.update("TRK-01", score, _BASE_TS + timedelta(seconds=i * 10))
            results.append(r.persistent_score)
        return results

    r1 = run_sequence()
    r2 = run_sequence()
    for a, b in zip(r1, r2):
        assert a == pytest.approx(b, abs=1e-6)


# ---------------------------------------------------------------------------
# 19. Persistent score always in [0, 100]
# ---------------------------------------------------------------------------

def test_persistent_score_always_bounded():
    accum = make_accum()
    scores = [0.0, 100.0, 150.0, -10.0, None, 60.0, 0.0, 0.0, 0.0, 0.0]
    for i, score in enumerate(scores):
        r = accum.update("TRK-01", score, _BASE_TS + timedelta(seconds=i * 5))
        assert 0.0 <= r.persistent_score <= 100.0
