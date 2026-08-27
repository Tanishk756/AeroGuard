"""Unit tests for AeroGuard AI sensor confidence and explainable anomaly scoring."""

from datetime import UTC, datetime, timedelta
import pytest

from ai.anomaly.models import AnomalyScoringConfig
from ai.anomaly.scoring import evaluate_anomaly
from ai.confidence.sensor import compute_sensor_confidence
from ai.schemas import AnomalyCategory, KinematicFeatures


def test_sensor_confidence_modalities_and_bonus():
    """Verify sensor confidence scoring across modalities and source counts."""
    radar_conf = compute_sensor_confidence(provenance="RADAR", source_count=1)
    acoustic_conf = compute_sensor_confidence(provenance="ACOUSTIC", source_count=1)
    assert radar_conf > acoustic_conf

    # Multi-source bonus
    fused_conf = compute_sensor_confidence(provenance="RADAR", source_count=3)
    assert fused_conf >= radar_conf


def test_sensor_confidence_freshness_decay():
    """Verify observation freshness decay over time."""
    now = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    fresh_time = now - timedelta(seconds=1)
    stale_time = now - timedelta(seconds=30)

    fresh_conf = compute_sensor_confidence(provenance="RADAR", last_seen_at=fresh_time, now=now)
    stale_conf = compute_sensor_confidence(provenance="RADAR", last_seen_at=stale_time, now=now)

    assert fresh_conf > stale_conf
    assert stale_conf < 0.5


def test_anomaly_scoring_nominal_flight():
    """Verify nominal straight-and-level flight produces LOW anomaly score and NORMAL category."""
    features = KinematicFeatures(
        speed_mps=18.0,
        acceleration_mps2=0.2,
        vertical_speed_mps=0.1,
        heading_deg=90.0,
        turn_rate_dps=1.2,
        directional_consistency=0.99,
        sample_count=20,
        timespan_seconds=20.0,
    )
    assessment = evaluate_anomaly("TRK-001", features, sensor_confidence=0.95)

    assert assessment.anomaly_score < 25.0
    assert assessment.anomaly_level == "LOW"
    assert assessment.primary_category == AnomalyCategory.NORMAL
    assert len(assessment.factors) == 5
    assert "nominal" in assessment.summary.lower()


def test_anomaly_scoring_erratic_heading():
    """Verify high turn rate and erratic heading triggers ERRATIC_HEADING anomaly."""
    features = KinematicFeatures(
        speed_mps=22.0,
        acceleration_mps2=1.0,
        vertical_speed_mps=0.5,
        heading_deg=180.0,
        turn_rate_dps=52.0,  # Extreme turn rate
        directional_consistency=0.45,
        sample_count=15,
        timespan_seconds=15.0,
    )
    assessment = evaluate_anomaly("TRK-002", features, sensor_confidence=0.90)

    assert assessment.anomaly_score >= 40.0
    assert assessment.primary_category == AnomalyCategory.ERRATIC_HEADING
    turn_factor = next(f for f in assessment.factors if "Turn" in f.name)
    assert turn_factor.score > 70.0
    assert turn_factor.severity in ("HIGH", "CRITICAL")


def test_anomaly_scoring_rapid_altitude_change():
    """Verify extreme climb/dive rate triggers RAPID_ALTITUDE_CHANGE anomaly."""
    features = KinematicFeatures(
        speed_mps=20.0,
        acceleration_mps2=0.5,
        vertical_speed_mps=22.0,  # Extreme climb rate (+22 m/s)
        heading_deg=45.0,
        turn_rate_dps=2.0,
        directional_consistency=0.95,
        sample_count=12,
        timespan_seconds=12.0,
    )
    assessment = evaluate_anomaly("TRK-003", features, sensor_confidence=0.95)

    assert assessment.anomaly_score >= 40.0
    assert assessment.primary_category == AnomalyCategory.RAPID_ALTITUDE_CHANGE
    vert_factor = next(f for f in assessment.factors if "Vertical" in f.name)
    assert vert_factor.score > 80.0
    assert "climb" in vert_factor.description


def test_anomaly_scoring_loitering_pattern():
    """Verify detected circular loitering triggers LOITERING_PATTERN anomaly."""
    features = KinematicFeatures(
        speed_mps=15.0,
        acceleration_mps2=0.2,
        vertical_speed_mps=0.0,
        heading_deg=270.0,
        turn_rate_dps=12.0,
        directional_consistency=0.15,
        loiter_radius_meters=180.0,
        sample_count=30,
        timespan_seconds=40.0,
    )
    assessment = evaluate_anomaly("TRK-004", features, sensor_confidence=0.90)

    assert assessment.anomaly_score >= 30.0
    assert assessment.primary_category == AnomalyCategory.LOITERING_PATTERN
    loiter_factor = next(f for f in assessment.factors if "Loitering" in f.name)
    assert loiter_factor.score >= 50.0


def test_anomaly_scoring_confidence_moderation():
    """Verify degraded sensor confidence dampens anomaly score to mitigate false alarms."""
    features = KinematicFeatures(
        speed_mps=25.0,
        acceleration_mps2=8.0,
        vertical_speed_mps=15.0,
        heading_deg=90.0,
        turn_rate_dps=40.0,
        directional_consistency=0.6,
        sample_count=10,
        timespan_seconds=10.0,
    )
    high_conf_assessment = evaluate_anomaly("TRK-005", features, sensor_confidence=1.0)
    low_conf_assessment = evaluate_anomaly("TRK-005", features, sensor_confidence=0.2)

    assert high_conf_assessment.anomaly_score > low_conf_assessment.anomaly_score
