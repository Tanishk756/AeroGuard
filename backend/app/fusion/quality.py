"""Deterministic track quality, source diversity, and coasting confidence decay models."""

from dataclasses import dataclass
import math
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.association import TrackAssociation
from app.models.sensor import Sensor
from app.models.track import Track, TrackState


@dataclass(frozen=True)
class QualityConfig:
    weight_confidence: float = 0.40
    weight_diversity: float = 0.25
    weight_continuity: float = 0.20
    weight_residual: float = 0.15
    diversity_window_seconds: float = 60.0
    coast_decay_half_life_seconds: float = 30.0
    maximum_horizontal_gate: float = 500.0


@dataclass(frozen=True)
class TrackQualityScore:
    quality: float
    confidence_component: float
    diversity_component: float
    continuity_component: float
    residual_component: float
    distinct_sensors: int
    distinct_modalities: int


def calculate_source_diversity(
    distinct_sensors: int, distinct_modalities: int
) -> float:
    """Calculate bounded [0.0, 1.0] source diversity metric.

    Multiple detections from the same single sensor yield a baseline score (0.30),
    while corroboration across multiple distinct sensors and sensor modalities increases
    the diversity score up to 1.0.
    """
    if distinct_sensors <= 0:
        return 0.0
    if distinct_sensors == 1:
        return 0.30
    score = 0.40 * (distinct_sensors - 1) + 0.30 * distinct_modalities
    return round(max(0.0, min(1.0, score)), 4)


def decay_coasting_confidence(
    confidence: float,
    coast_elapsed_seconds: float,
    half_life_seconds: float = 30.0,
) -> float:
    """Apply deterministic exponential confidence decay during coasting (STALE state).

    Decays smoothly over time without dropping below 0.0.
    """
    if coast_elapsed_seconds <= 0 or confidence <= 0:
        return confidence
    decay_rate = math.log(2.0) / max(half_life_seconds, 1.0)
    decayed = confidence * math.exp(-decay_rate * coast_elapsed_seconds)
    return round(max(0.0, min(1.0, decayed)), 4)


def compute_track_quality(
    db: Session,
    track: Track,
    latest_distance_meters: float | None = None,
    now: datetime | None = None,
    config: QualityConfig | None = None,
) -> TrackQualityScore:
    """Compute deterministic composite track quality score and factor breakdown."""
    cfg = config or QualityConfig()
    eval_time = now or track.last_seen_at

    # 1. Query distinct contributing sensors and modalities in diversity window
    window_start = eval_time - timedelta(seconds=cfg.diversity_window_seconds)
    sensor_query = (
        select(Sensor.id, Sensor.source_type)
        .join(TrackAssociation, TrackAssociation.sensor_id == Sensor.id)
        .where(
            TrackAssociation.track_id == track.id,
            TrackAssociation.timestamp >= window_start,
        )
        .distinct()
    )
    sensor_rows = db.execute(sensor_query).all()
    distinct_sensors = len(sensor_rows) if sensor_rows else max(track.source_count, 1)
    distinct_modalities = len({row[1] for row in sensor_rows}) if sensor_rows else 1

    diversity_score = calculate_source_diversity(distinct_sensors, distinct_modalities)

    # 2. Temporal continuity
    time_since_seen = max(0.0, (eval_time - track.last_seen_at).total_seconds())
    continuity_score = max(0.0, min(1.0, 1.0 - (time_since_seen / (cfg.diversity_window_seconds * 0.5))))

    # 3. Spatial residual agreement
    if latest_distance_meters is not None:
        residual_score = max(0.0, min(1.0, 1.0 - (latest_distance_meters / cfg.maximum_horizontal_gate)))
    else:
        residual_score = 1.0

    # 4. Composite quality
    confidence_comp = track.confidence
    composite = (
        cfg.weight_confidence * confidence_comp
        + cfg.weight_diversity * diversity_score
        + cfg.weight_continuity * continuity_score
        + cfg.weight_residual * residual_score
    )
    final_quality = round(max(0.0, min(1.0, composite)), 4)

    return TrackQualityScore(
        quality=final_quality,
        confidence_component=round(confidence_comp, 4),
        diversity_component=diversity_score,
        continuity_component=round(continuity_score, 4),
        residual_component=round(residual_score, 4),
        distinct_sensors=distinct_sensors,
        distinct_modalities=distinct_modalities,
    )
