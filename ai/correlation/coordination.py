"""Multi-track coordination index computation — Stage AI2-D.

ARCHITECTURE
------------
Computes a deterministic synchronization index for an AI2-B correlated group,
measuring how tightly group members are flying in formation.

FORMULA
-------
The synchronization index S_sync is defined as:

    S_sync = 0.50 × cos(σ_θ) + 0.50 × exp(−σ_v / 5.0)

where:
    σ_θ = heading dispersion in radians (circular standard deviation)
    σ_v = velocity dispersion in m/s    (population standard deviation)

Both components are bounded [0, 1]:
    cos(σ_θ) → 1.0 when all headings identical, → -1.0 at maximum dispersion
    exp(-σ_v/5) → 1.0 when all velocities identical, → 0 at very high dispersion

Final index is clamped to [0.0, 1.0].

CIRCULAR HEADING STATISTICS
----------------------------
To correctly handle the 360°/0° wraparound, heading dispersion is computed
as the circular standard deviation:

    R̄ = |Σ exp(i × heading_k)| / N
    σ_circ = sqrt(−2 × ln(R̄))   (in radians)

where R̄ is the mean resultant length of the unit circle vectors.

This ensures that headings such as 359° and 1° are treated as 2° apart,
not 358° apart.

MISSING DATA
------------
- Missing heading for a member → that member is excluded from σ_θ calculation.
  If fewer than 2 headings remain, heading component defaults to 0.5.
- Missing velocity for a member → excluded from σ_v calculation.
  If fewer than 2 velocities remain, velocity component defaults to 0.5.
- Fewer than 2 members total → returns None (cannot compute coordination).

DEFENSIVE BOUNDARY
------------------
This module produces informational operational situational-awareness metrics.
It must NOT be used for weapon targeting, engagement authorization,
fire-control, jamming, or interception planning.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from ai.schemas import CoordinatedFormation, TrackGroup


# ─────────────────────────────────────────────────────────────────────────────
# Observation input
# ─────────────────────────────────────────────────────────────────────────────

@dataclass(frozen=True)
class MemberObservation:
    """Minimal per-track input for coordination index computation.

    Reuses the same field names as TrackObservation in ai.correlation.grouping
    for easy integration.
    """

    id: str
    heading: float | None = None    # degrees [0, 360)
    velocity: float | None = None   # m/s, >= 0


def member_obs_from_any(obj: Any) -> MemberObservation:
    """Convert a dict, dataclass, or model into a MemberObservation."""
    if isinstance(obj, MemberObservation):
        return obj
    if isinstance(obj, dict):
        return MemberObservation(
            id=str(obj["id"]),
            heading=float(obj["heading"]) if obj.get("heading") is not None else None,
            velocity=float(obj["velocity"]) if obj.get("velocity") is not None else None,
        )
    return MemberObservation(
        id=str(getattr(obj, "id", getattr(obj, "track_id", ""))),
        heading=float(getattr(obj, "heading", None)) if getattr(obj, "heading", None) is not None else None,
        velocity=float(getattr(obj, "velocity", None)) if getattr(obj, "velocity", None) is not None else None,
    )


# ─────────────────────────────────────────────────────────────────────────────
# Core math helpers
# ─────────────────────────────────────────────────────────────────────────────

def _circular_std_rad(headings_deg: list[float]) -> float:
    """Compute circular standard deviation in radians from headings in degrees.

    Uses the directional statistics formula:
        R̄ = mean resultant length
        σ_circ = sqrt(-2 × ln(R̄))

    Returns 0.0 for a single heading (no dispersion by definition).
    Returns π/2 (≈ 1.571 rad) as a practical upper bound for maximally
    dispersed headings (R̄ → 0 → σ_circ → ∞, capped at π).
    """
    if len(headings_deg) < 1:
        return 0.0
    if len(headings_deg) == 1:
        return 0.0

    sin_sum = sum(math.sin(math.radians(h)) for h in headings_deg)
    cos_sum = sum(math.cos(math.radians(h)) for h in headings_deg)
    n = len(headings_deg)
    r_bar = math.sqrt(sin_sum ** 2 + cos_sum ** 2) / n

    # Clamp r_bar to avoid log(0); cap sigma at π (maximum possible circular std)
    r_bar = max(1e-10, min(1.0, r_bar))
    sigma = min(math.pi, math.sqrt(-2.0 * math.log(r_bar)))

    return sigma


def _population_std(values: list[float]) -> float:
    """Compute population standard deviation. Returns 0.0 for < 2 values."""
    n = len(values)
    if n < 2:
        return 0.0
    mean = sum(values) / n
    variance = sum((v - mean) ** 2 for v in values) / n
    return math.sqrt(variance)


def _heading_dispersion_deg(headings_deg: list[float]) -> float:
    """Return circular heading dispersion in degrees [0, 180]."""
    sigma_rad = _circular_std_rad(headings_deg)
    # Clamp to [0, pi] then convert
    sigma_rad = min(math.pi, sigma_rad)
    return math.degrees(sigma_rad)


# ─────────────────────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────────────────────

def compute_coordination_index(
    group: TrackGroup,
    members: list[Any],
    evaluated_at: datetime | None = None,
) -> CoordinatedFormation | None:
    """Compute the synchronization index for an AI2-B track group.

    Parameters
    ----------
    group:       TrackGroup as produced by ai.correlation.grouping.correlate_tracks.
    members:     Observations for each group member (must match group.member_track_ids).
                 Accepts MemberObservation, dict, or any object with .id/.heading/.velocity.
    evaluated_at: Timestamp for the result. Defaults to datetime.now(UTC).

    Returns
    -------
    CoordinatedFormation if the group has >= 2 unique members with a valid result,
    None otherwise (e.g., insufficient members).

    Notes
    -----
    - Duplicate member IDs in `members` are deduplicated (last value wins).
    - Members present in `members` but not in `group.member_track_ids` are ignored.
    - Missing heading/velocity fields reduce the evidence used but never crash.
    """
    eval_ts = evaluated_at or datetime.now(UTC)

    # Normalize and deduplicate by ID
    obs_map: dict[str, MemberObservation] = {}
    for m in members:
        obs = member_obs_from_any(m)
        obs_map[obs.id] = obs

    # Only consider members that are actually in the group
    valid_ids = [mid for mid in group.member_track_ids if mid in obs_map]
    if len(valid_ids) < 2:
        return None

    valid_obs = [obs_map[mid] for mid in valid_ids]

    # ── Heading component ─────────────────────────────────────────────────
    headings = [o.heading for o in valid_obs if o.heading is not None]
    if len(headings) >= 2:
        sigma_theta_rad = _circular_std_rad(headings)
        # cos(sigma_theta) ∈ [-1, 1]; clamp to [0, 1] since the formula uses
        # this as a non-negative contribution to the synchronization index.
        # cos = 1 at zero dispersion, cos = -1 at maximum (π radians) dispersion.
        heading_component = max(0.0, math.cos(sigma_theta_rad))
        heading_dispersion = _heading_dispersion_deg(headings)
    else:
        # Insufficient heading data → neutral contribution
        heading_component = 0.5
        heading_dispersion = 0.0

    # ── Velocity component ────────────────────────────────────────────────
    velocities = [o.velocity for o in valid_obs if o.velocity is not None]
    if len(velocities) >= 2:
        sigma_v = _population_std(velocities)
        velocity_component = math.exp(-sigma_v / 5.0)  # (0, 1]
        velocity_dispersion = round(sigma_v, 3)
    else:
        # Insufficient velocity data → neutral contribution
        velocity_component = 0.5
        velocity_dispersion = 0.0

    # ── Synchronization index ─────────────────────────────────────────────
    # S_sync = 0.50 × cos(σ_θ) + 0.50 × exp(-σ_v / 5.0)
    s_sync = 0.50 * heading_component + 0.50 * velocity_component
    s_sync = round(max(0.0, min(1.0, s_sync)), 4)

    # ── Confidence ────────────────────────────────────────────────────────
    # Evidence quality: how many members provided usable heading + velocity
    heading_coverage = len(headings) / len(valid_obs)
    velocity_coverage = len(velocities) / len(valid_obs)
    evidence_quality = (heading_coverage + velocity_coverage) / 2.0
    # Scale by group size — larger groups give stronger evidence
    size_factor = min(1.0, len(valid_obs) / 5.0)
    confidence = round(max(0.0, min(1.0, evidence_quality * (0.6 + 0.4 * size_factor))), 3)

    # Formation ID: deterministic from group_id
    formation_id = f"FMT-{group.group_id}"

    return CoordinatedFormation(
        formation_id=formation_id,
        group_id=group.group_id,
        member_track_ids=valid_ids,
        synchronization_index=s_sync,
        heading_dispersion_deg=round(heading_dispersion, 3),
        velocity_dispersion_mps=velocity_dispersion,
        confidence=confidence,
        evaluated_at=eval_ts,
    )
