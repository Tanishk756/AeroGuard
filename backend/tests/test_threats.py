"""Integration tests for operational threat assessment scoring, factor explainability, and upsert persistence."""

from datetime import datetime

import pytest
from sqlalchemy import func, select

from app.fusion.quality import TrackQualityScore
from app.geofencing.engine import GeofenceEvaluationResult
from app.models.audit import AuditEvent
from app.models.geofence import Geofence
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackState
from app.threats.scoring import ThreatScoringConfig, calculate_threat_score
from app.threats.service import ThreatAssessmentService


def test_threat_scoring_factors_and_bounds():
    track = Track(
        id="t-th-1",
        state=TrackState.ACTIVE,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        altitude=100.0,
        velocity=35.0,  # 35 m/s
        confidence=0.90,
        classification="UAV",
    )
    quality = TrackQualityScore(
        quality=0.85,
        confidence_component=0.90,
        diversity_component=0.70,
        continuity_component=0.90,
        residual_component=0.80,
        distinct_sensors=2,
        distinct_modalities=2,
    )

    # 1. Inside geofence -> high priority / CRITICAL
    geo_res_breached = [
        GeofenceEvaluationResult(
            geofence_id="geo-1",
            geofence_name="Alpha Perimeter",
            inside=True,
            horizontal_inside=True,
            vertical_inside=True,
            altitude_indeterminate=False,
            distance_to_boundary_meters=0.0,
            reason="INSIDE_GEOFENCE",
        )
    ]
    threat_breached = calculate_threat_score(track, quality, geo_res_breached)
    assert 0.0 <= threat_breached.score <= 100.0
    assert threat_breached.level == ThreatLevel.CRITICAL
    assert threat_breached.geofence_factor == 1.00
    assert threat_breached.breached_geofences == ["geo-1"]

    # 2. Far outside geofence -> lower score
    geo_res_far = [
        GeofenceEvaluationResult(
            geofence_id="geo-1",
            geofence_name="Alpha Perimeter",
            inside=False,
            horizontal_inside=False,
            vertical_inside=False,
            altitude_indeterminate=False,
            distance_to_boundary_meters=10000.0,
            reason="OUTSIDE_HORIZONTAL",
        )
    ]
    threat_far = calculate_threat_score(track, quality, geo_res_far)
    assert threat_far.score < threat_breached.score
    assert threat_far.geofence_factor == 0.00


def test_threat_level_threshold_mapping():
    cfg = ThreatScoringConfig(
        threshold_critical=80.0,
        threshold_high=55.0,
        threshold_medium=25.0,
    )
    track_bird = Track(
        id="t-th-bird",
        state=TrackState.ACTIVE,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        altitude=50.0,
        velocity=5.0,
        confidence=0.50,
        classification="BIRD",
    )
    quality_low = TrackQualityScore(
        quality=0.30,
        confidence_component=0.50,
        diversity_component=0.30,
        continuity_component=0.30,
        residual_component=0.30,
        distinct_sensors=1,
        distinct_modalities=1,
    )
    res = calculate_threat_score(track_bird, quality_low, [], config=cfg)
    assert res.score < 25.0
    assert res.level == ThreatLevel.LOW


def test_threat_assessment_service_upsert_and_event(database):
    # Add an active geofence
    geo = Geofence(
        id="geo-srv-1",
        name="Service Test Zone",
        enabled=True,
        geometry={"type": "bbox", "min_lat": 37.0, "max_lat": 38.0, "min_lon": -123.0, "max_lon": -122.0},
        metadata_json={},
    )
    track = Track(
        id="track-srv-th",
        state=TrackState.ACTIVE,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.5,
        longitude=-122.5,
        altitude=100.0,
        velocity=20.0,
        confidence=0.85,
        classification="UAV",
    )
    database.add_all([geo, track])
    database.commit()

    service = ThreatAssessmentService(database)
    quality = TrackQualityScore(
        quality=0.80,
        confidence_component=0.85,
        diversity_component=0.70,
        continuity_component=0.80,
        residual_component=0.80,
        distinct_sensors=2,
        distinct_modalities=2,
    )

    # First evaluation -> inserts record
    eval1 = service.evaluate_track(track, quality)
    database.commit()

    stored1 = database.scalar(
        select(ThreatAssessment).where(ThreatAssessment.track_id == track.id)
    )
    assert stored1 is not None
    assert stored1.score == eval1.factors.score
    assert stored1.level == eval1.factors.level
    assert eval1.event.track_id == track.id

    # Second evaluation with updated quality -> updates existing record (upsert)
    quality2 = TrackQualityScore(
        quality=0.40,
        confidence_component=0.50,
        diversity_component=0.30,
        continuity_component=0.40,
        residual_component=0.40,
        distinct_sensors=1,
        distinct_modalities=1,
    )
    eval2 = service.evaluate_track(track, quality2)
    database.commit()

    all_stored = database.scalars(
        select(ThreatAssessment).where(ThreatAssessment.track_id == track.id)
    ).all()
    assert len(all_stored) == 1
    assert all_stored[0].score == eval2.factors.score

    # Verify no audit event was created for routine operational telemetry
    audit_count = database.scalar(select(func.count(AuditEvent.id)))
    assert audit_count == 0
