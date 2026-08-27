"""Deterministic sensor confidence and observation quality modeling.

Computes confidence in the physical measurement quality and observation
consistency, strictly decoupled from target hostility classification.
"""

from datetime import UTC, datetime
import math

# Baseline sensor modality reliability weights
MODALITY_BASE_CONFIDENCE: dict[str, float] = {
    "RADAR": 0.90,
    "RF": 0.85,
    "EO_IR": 0.80,
    "CAMERA": 0.75,
    "ACOUSTIC": 0.65,
    "FUSION": 0.95,
    "MANUAL": 0.60,
    "UNKNOWN": 0.50,
}


def compute_sensor_confidence(
    provenance: str | None = None,
    source_count: int = 1,
    last_seen_at: datetime | None = None,
    now: datetime | None = None,
    track_confidence: float = 1.0,
    sample_count: int = 1,
    speed_variance: float = 0.0,
) -> float:
    """Compute normalized sensor observation confidence in [0.0, 1.0].

    Parameters:
    - provenance: Primary sensor type (e.g. RADAR, RF, EO_IR, FUSION)
    - source_count: Number of distinct fused sensor sources
    - last_seen_at: Timestamp of most recent observation
    - now: Current reference time for age calculation
    - track_confidence: Kinematic tracker state confidence
    - sample_count: Number of historical observation samples
    - speed_variance: Kinematic measurement variance penalty
    """
    prov_key = (provenance or "UNKNOWN").upper()
    base_conf = MODALITY_BASE_CONFIDENCE.get(prov_key, 0.50)

    # 1. Multi-source consensus bonus (+0.05 per additional source, capped at +0.15)
    source_bonus = min(0.15, max(0, source_count - 1) * 0.05)

    # 2. History depth bonus (more samples -> higher confidence in track validity)
    history_factor = min(1.0, 0.5 + (sample_count * 0.05))

    # 3. Observation freshness decay (exponential decay after 5 seconds of latency)
    freshness_factor = 1.0
    if last_seen_at is not None:
        ref_time = now or datetime.now(UTC)
        # Normalize both to UTC or naive
        if ref_time.tzinfo is not None:
            ref_dt = ref_time.astimezone(UTC)
        else:
            ref_dt = ref_time.replace(tzinfo=UTC)

        if last_seen_at.tzinfo is not None:
            seen_dt = last_seen_at.astimezone(UTC)
        else:
            seen_dt = last_seen_at.replace(tzinfo=UTC)

        age_seconds = max(0.0, (ref_dt - seen_dt).total_seconds())
        if age_seconds > 3.0:
            # Half-life of ~15 seconds for stale observations
            freshness_factor = math.exp(-0.046 * (age_seconds - 3.0))

    # 4. Measurement noise penalty for high variance
    variance_penalty = 0.0
    if speed_variance > 100.0:
        variance_penalty = min(0.20, (speed_variance - 100.0) / 1000.0)

    # 5. Composite score calculation
    raw_confidence = (
        (base_conf + source_bonus)
        * history_factor
        * freshness_factor
        * track_confidence
        - variance_penalty
    )

    return round(max(0.05, min(1.0, raw_confidence)), 3)
