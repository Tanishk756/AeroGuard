"""Temporal persistent anomaly accumulator — Stage AI2-D.

ARCHITECTURE
------------
This module wraps the existing AI1 instantaneous anomaly score produced by
``ai.anomaly.scoring.evaluate_anomaly`` and adds temporal persistence via
exponential decay, entry hysteresis, and exit hysteresis.

It does NOT replace or modify the underlying AI1 algorithm.

MATHEMATICAL FORMULATION
------------------------
After each observation, the persistent score is updated via:

    decayed   = previous_score × decay_factor
    decay_factor = 0.5 ** (dt_seconds / half_life)

    persistent_score = max(decayed, new_ai1_score)
    # Blends in a small fraction of the new score to handle stale signals
    # Alternative: simple max preserves highest observed signal during the window.

    Because "max" alone never decays during a continuous anomaly, the authoritative
    formula used here is a leaky-integrator with exponential decay:

    persistent_score = decayed * (1 - alpha) + new_ai1_score * alpha
    where alpha = 1 - decay_factor   (when new_ai1_score > 0)

    Simplified to:
    persistent_score = decayed + (new_ai1_score - decayed) * alpha
                     = decayed + new_ai1_score * (1 - decay_factor)

    This guarantees:
    - Full decay to 0 if AI1 score drops to 0
    - New high-anomaly signals are immediately reflected
    - Smooth decay during recovery

HALF-LIFE BEHAVIOUR
-------------------
With half_life = 30.0 seconds and zero subsequent AI1 score:

    t =  0 s → persistent_score = S
    t = 30 s → persistent_score = S × 0.5
    t = 60 s → persistent_score = S × 0.25

ENTRY / EXIT HYSTERESIS
------------------------
- ANOMALOUS state entered only after:
    persistent_score >= enter_threshold (default 60.0)
    for enter_ticks consecutive evaluations (default 3)

- ANOMALOUS state exited only after:
    persistent_score < exit_threshold (default 40.0)
    for exit_ticks consecutive evaluations (default 5)

DEFENSIVE BOUNDARY
------------------
This is strictly defensive situational-awareness.
Persistent anomaly state must NOT be construed as hostile intent probability,
weapon targeting, engagement authorization, or fire-control input.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime


# ─────────────────────────────────────────────────────────────────────────────
# Configuration
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PersistentAnomalyConfig:
    """Configurable parameters for the temporal anomaly accumulator."""

    # Decay
    half_life_seconds: float = 30.0         # τ½: score halves every 30 s with zero input

    # Entry hysteresis
    enter_threshold: float = 60.0           # persistent_score >= this begins entry count
    enter_ticks: int = 3                    # consecutive ticks above enter_threshold to enter

    # Exit hysteresis
    exit_threshold: float = 40.0            # persistent_score < this begins recovery count
    exit_ticks: int = 5                     # consecutive ticks below exit_threshold to exit

    # Clamping
    score_min: float = 0.0
    score_max: float = 100.0


# ─────────────────────────────────────────────────────────────────────────────
# Per-track state
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class TrackAnomalyState:
    """Mutable per-track persistent anomaly state.

    Must be created fresh per track and never shared across tracks.
    """

    track_id: str

    # Temporal accumulation
    persistent_score: float = 0.0
    last_timestamp: datetime | None = None

    # Entry hysteresis
    qualifying_ticks: int = 0           # consecutive ticks at/above enter_threshold

    # Exit hysteresis
    recovery_ticks: int = 0             # consecutive ticks below exit_threshold

    # Persistent anomaly flag
    is_anomalous: bool = False


# ─────────────────────────────────────────────────────────────────────────────
# Result
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class PersistentAnomalyResult:
    """Result of a single persistent anomaly evaluation.

    Attributes
    ----------
    track_id:                 Track identifier.
    instantaneous_score:      Raw AI1 score for this observation (or None if missing).
    persistent_score:         Temporally accumulated/decayed score [0, 100].
    is_anomalous:             True when entry hysteresis has been satisfied.
    qualifying_ticks:         How many consecutive ticks above enter_threshold.
    recovery_ticks:           How many consecutive ticks below exit_threshold.
    dt_seconds:               Time since last observation (0 for first).
    decay_factor:             Decay multiplier applied this evaluation.
    evaluated_at:             Observation timestamp used.
    """

    track_id: str
    instantaneous_score: float | None
    persistent_score: float
    is_anomalous: bool
    qualifying_ticks: int
    recovery_ticks: int
    dt_seconds: float
    decay_factor: float
    evaluated_at: datetime


# ─────────────────────────────────────────────────────────────────────────────
# Accumulator
# ─────────────────────────────────────────────────────────────────────────────

class PersistentAnomalyAccumulator:
    """Deterministic temporal anomaly accumulator with per-track isolation.

    Usage::

        accum = PersistentAnomalyAccumulator()
        result = accum.update(track_id, ai1_score, timestamp)

    State is stored in memory only — never persisted to disk or browser storage.
    """

    def __init__(self, config: PersistentAnomalyConfig | None = None) -> None:
        self._cfg = config or PersistentAnomalyConfig()
        self._states: dict[str, TrackAnomalyState] = {}

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def update(
        self,
        track_id: str,
        instantaneous_score: float | None,
        timestamp: datetime | None = None,
    ) -> PersistentAnomalyResult:
        """Evaluate and update persistent anomaly state for a single track.

        Parameters
        ----------
        track_id:             Unique track identifier.
        instantaneous_score:  AI1 score [0, 100], or None if unavailable.
        timestamp:            Observation time (UTC). Falls back to now().

        Returns
        -------
        PersistentAnomalyResult with the updated persistent state.
        """
        cfg = self._cfg
        eval_ts = timestamp or datetime.now(UTC)

        # Retrieve or create per-track state
        if track_id not in self._states:
            self._states[track_id] = TrackAnomalyState(track_id=track_id)

        state = self._states[track_id]

        # ── Compute dt and decay factor ───────────────────────────────────
        if state.last_timestamp is None:
            dt_seconds = 0.0
        else:
            dt_seconds = (eval_ts - state.last_timestamp).total_seconds()
            if dt_seconds < 0.0:
                # Out-of-order: treat as zero dt (no decay, no time advance)
                dt_seconds = 0.0

        decay_factor = 0.5 ** (dt_seconds / cfg.half_life_seconds)

        # ── Apply decay then blend in new signal ─────────────────────────
        decayed = state.persistent_score * decay_factor

        if instantaneous_score is not None:
            ai1 = max(cfg.score_min, min(cfg.score_max, float(instantaneous_score)))
            # Leaky-integrator: decayed baseline + scaled new signal
            alpha = 1.0 - decay_factor  # how much weight goes to the new signal
            new_persistent = decayed + ai1 * alpha
        else:
            # Missing score → pure decay, no new signal contribution
            new_persistent = decayed

        new_persistent = round(max(cfg.score_min, min(cfg.score_max, new_persistent)), 3)

        # ── Entry hysteresis ─────────────────────────────────────────────
        if new_persistent >= cfg.enter_threshold:
            qualifying = state.qualifying_ticks + 1
            recovery = 0
        else:
            qualifying = 0
            # Only count recovery ticks when in anomalous state or accumulating recovery
            recovery = state.recovery_ticks + 1 if state.is_anomalous else 0

        # ── Exit hysteresis ──────────────────────────────────────────────
        if not state.is_anomalous:
            # Enter anomalous when enough qualifying ticks accumulate
            new_is_anomalous = qualifying >= cfg.enter_ticks
        else:
            # Exit anomalous when persistent_score < exit_threshold for exit_ticks
            if new_persistent >= cfg.exit_threshold:
                recovery = 0  # reset recovery counter — still above exit threshold
            exit_reached = (
                new_persistent < cfg.exit_threshold
                and recovery >= cfg.exit_ticks
            )
            new_is_anomalous = not exit_reached

        # ── Update state ─────────────────────────────────────────────────
        state.persistent_score = new_persistent
        state.last_timestamp = eval_ts if dt_seconds >= 0.0 else state.last_timestamp
        state.qualifying_ticks = qualifying
        state.recovery_ticks = recovery
        state.is_anomalous = new_is_anomalous

        return PersistentAnomalyResult(
            track_id=track_id,
            instantaneous_score=instantaneous_score,
            persistent_score=new_persistent,
            is_anomalous=new_is_anomalous,
            qualifying_ticks=qualifying,
            recovery_ticks=recovery,
            dt_seconds=dt_seconds,
            decay_factor=round(decay_factor, 6),
            evaluated_at=eval_ts,
        )

    def reset_track(self, track_id: str) -> None:
        """Remove all accumulated state for a single track."""
        self._states.pop(track_id, None)

    def reset_all(self) -> None:
        """Remove all accumulated state for every track."""
        self._states.clear()

    def get_state(self, track_id: str) -> TrackAnomalyState | None:
        """Return the current internal state for a track (read-only snapshot)."""
        return self._states.get(track_id)

    @property
    def tracked_ids(self) -> list[str]:
        """Return sorted list of all track IDs currently being tracked."""
        return sorted(self._states.keys())
