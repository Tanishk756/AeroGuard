"""Unit tests for geometry, gating, scoring, and tie-breaking."""

from datetime import UTC, datetime, timedelta
import math

import pytest

from app.models.detection import Detection
from app.models.sensor import SensorSourceClass
from app.models.track import Track, TrackState
from app.tracking.association import (
    angular_difference,
    calculate_distance_3d,
    generate_track_id,
    haversine_distance,
)
from app.tracking.gating import AssociationGate, GatingConfig
from app.tracking.scoring import AssociationScorer, ScoringConfig


def make_detection(
    timestamp: datetime | None = None,
    lat: float = 37.7749,
    lon: float = -122.4194,
    altitude: float | None = 100.0,
    velocity: float | None = 15.0,
    heading: float | None = 90.0,
    confidence: float = 0.85,
    classification: str | None = "UAV",
) -> Detection:
    ts = timestamp or datetime(2026, 8, 26, 12, 0, 0)
    return Detection(
        id="det-1",
        sensor_id="sensor-1",
        source_detection_id="src-1",
        timestamp=ts,
        latitude=lat,
        longitude=lon,
        altitude=altitude,
        velocity=velocity,
        heading=heading,
        confidence=confidence,
        classification=classification,
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )


def make_track(
    track_id: str = "track-1",
    state: TrackState = TrackState.ACTIVE,
    last_seen_at: datetime | None = None,
    first_seen_at: datetime | None = None,
    lat: float = 37.7749,
    lon: float = -122.4194,
    altitude: float | None = 100.0,
    velocity: float | None = 15.0,
    heading: float | None = 90.0,
    confidence: float = 0.85,
    classification: str | None = "UAV",
) -> Track:
    ts = last_seen_at or datetime(2026, 8, 26, 12, 0, 0)
    fts = first_seen_at or ts
    return Track(
        id=track_id,
        state=state,
        first_seen_at=fts,
        last_seen_at=ts,
        latitude=lat,
        longitude=lon,
        altitude=altitude,
        velocity=velocity,
        heading=heading,
        confidence=confidence,
        classification=classification,
        source_count=1,
    )


def test_haversine_distance():
    # Same point -> 0 meters
    assert haversine_distance(37.7749, -122.4194, 37.7749, -122.4194) == 0.0

    # Known distance: Equator 1 degree longitude ~ 111.19 km
    dist_1deg = haversine_distance(0.0, 0.0, 0.0, 1.0)
    assert 111_000 < dist_1deg < 112_000

    # Small displacement (~111 meters per 0.001 deg lat)
    dist_small = haversine_distance(37.7749, -122.4194, 37.7759, -122.4194)
    assert 100 < dist_small < 120


def test_distance_3d_and_missing_altitude():
    # Both altitudes present
    dist_3d, vert = calculate_distance_3d(100.0, 200.0, 150.0)
    assert vert == 50.0
    assert pytest.approx(dist_3d, rel=1e-3) == math.sqrt(100.0**2 + 50.0**2)

    # Missing altitude on one or both -> never fabricates
    dist_3d, vert = calculate_distance_3d(100.0, None, 150.0)
    assert dist_3d == 100.0
    assert vert is None

    dist_3d, vert = calculate_distance_3d(100.0, 200.0, None)
    assert dist_3d == 100.0
    assert vert is None


def test_angular_difference():
    assert angular_difference(10.0, 20.0) == 10.0
    assert angular_difference(10.0, 350.0) == 20.0  # Wrap-around across 0/360
    assert angular_difference(350.0, 10.0) == 20.0
    assert angular_difference(0.0, 180.0) == 180.0
    assert angular_difference(45.0, 225.0) == 180.0


def test_deterministic_track_id():
    id1 = generate_track_id("detection-123")
    id2 = generate_track_id("detection-123")
    id3 = generate_track_id("detection-456")
    assert id1 == id2
    assert id1 != id3
    assert len(id1) == 36


def test_gating_obvious_match_and_boundaries():
    gate = AssociationGate(GatingConfig(
        maximum_time_delta=10.0,
        maximum_horizontal_distance=500.0,
        maximum_vertical_distance=150.0,
        maximum_velocity_delta=50.0,
        maximum_heading_delta=90.0,
    ))

    t0 = datetime(2026, 8, 26, 12, 0, 0)
    track = make_track(last_seen_at=t0, lat=37.7749, lon=-122.4194, altitude=100.0, velocity=15.0, heading=90.0)

    # Exact match -> passes
    det_exact = make_detection(timestamp=t0, lat=37.7749, lon=-122.4194, altitude=100.0, velocity=15.0, heading=90.0)
    res = gate.evaluate(det_exact, track)
    assert res.passed is True
    assert res.reason == "PASSED"

    # Temporal boundary: 9.9s passes, 10.1s fails
    det_9_9s = make_detection(timestamp=t0 + timedelta(seconds=9.9))
    assert gate.evaluate(det_9_9s, track).passed is True

    det_10_1s = make_detection(timestamp=t0 + timedelta(seconds=10.1))
    res_time_fail = gate.evaluate(det_10_1s, track)
    assert res_time_fail.passed is False
    assert "Time delta" in res_time_fail.reason

    # Spatial boundary: ~111m per 0.001 deg. 0.004 deg ~ 444m (passes), 0.006 deg ~ 666m (fails)
    det_close = make_detection(timestamp=t0, lat=37.7749 + 0.004, lon=-122.4194)
    assert gate.evaluate(det_close, track).passed is True

    det_far = make_detection(timestamp=t0, lat=37.7749 + 0.006, lon=-122.4194)
    res_dist_fail = gate.evaluate(det_far, track)
    assert res_dist_fail.passed is False
    assert "Horizontal distance" in res_dist_fail.reason

    # Vertical boundary: diff=140m passes, diff=160m fails
    det_alt_pass = make_detection(timestamp=t0, altitude=240.0)
    assert gate.evaluate(det_alt_pass, track).passed is True

    det_alt_fail = make_detection(timestamp=t0, altitude=260.0)
    res_alt_fail = gate.evaluate(det_alt_fail, track)
    assert res_alt_fail.passed is False
    assert "Vertical distance" in res_alt_fail.reason

    # Velocity boundary: diff=40m/s passes, diff=60m/s fails
    det_vel_pass = make_detection(timestamp=t0, velocity=55.0)
    assert gate.evaluate(det_vel_pass, track).passed is True

    det_vel_fail = make_detection(timestamp=t0, velocity=75.0)
    res_vel_fail = gate.evaluate(det_vel_fail, track)
    assert res_vel_fail.passed is False
    assert "Velocity delta" in res_vel_fail.reason

    # Heading boundary: 90 vs 170 (diff=80 deg) passes, 90 vs 190 (diff=100 deg) fails
    det_head_pass = make_detection(timestamp=t0, heading=170.0)
    assert gate.evaluate(det_head_pass, track).passed is True

    det_head_fail = make_detection(timestamp=t0, heading=190.0)
    res_head_fail = gate.evaluate(det_head_fail, track)
    assert res_head_fail.passed is False
    assert "Heading delta" in res_head_fail.reason


def test_gating_missing_optional_values_allowed():
    gate = AssociationGate()
    t0 = datetime(2026, 8, 26, 12, 0, 0)
    track = make_track(last_seen_at=t0, altitude=None, velocity=None, heading=None)
    det = make_detection(timestamp=t0, altitude=None, velocity=None, heading=None)

    res = gate.evaluate(det, track)
    assert res.passed is True
    assert res.vertical_distance is None


def test_gating_stale_track_multiplier():
    gate = AssociationGate(GatingConfig(
        maximum_horizontal_distance=500.0,
        maximum_vertical_distance=150.0,
        stale_spatial_multiplier=1.5,
    ))

    t0 = datetime(2026, 8, 26, 12, 0, 0)
    # 0.0055 deg lat ~ 610m distance
    # For ACTIVE track (max 500m) -> fails
    active_track = make_track(state=TrackState.ACTIVE, last_seen_at=t0)
    det = make_detection(timestamp=t0, lat=37.7749 + 0.0055, lon=-122.4194)
    assert gate.evaluate(det, active_track).passed is False

    # For STALE track (max 750m) -> passes
    stale_track = make_track(state=TrackState.STALE, last_seen_at=t0)
    assert gate.evaluate(det, stale_track).passed is True


def test_scoring_normalization_and_weights():
    scorer = AssociationScorer()
    gate = AssociationGate()
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Perfect match -> score 1.0
    track = make_track(last_seen_at=t0, lat=37.7749, lon=-122.4194, altitude=100.0, velocity=20.0, heading=90.0, confidence=0.9)
    det = make_detection(timestamp=t0, lat=37.7749, lon=-122.4194, altitude=100.0, velocity=20.0, heading=90.0, confidence=0.9)
    gate_res = gate.evaluate(det, track)
    score_res = scorer.score(det, track, gate_res)

    assert score_res.score == 1.0
    assert score_res.passed is True

    # Missing velocity and heading -> renormalizes across spatial, temporal, confidence
    track_no_kin = make_track(last_seen_at=t0, velocity=None, heading=None, confidence=0.8)
    det_no_kin = make_detection(timestamp=t0, velocity=None, heading=None, confidence=0.8)
    gate_res2 = gate.evaluate(det_no_kin, track_no_kin)
    score_res2 = scorer.score(det_no_kin, track_no_kin, gate_res2)

    assert score_res2.score == 1.0
    assert score_res2.velocity_score is None
    assert score_res2.heading_score is None
    assert score_res2.passed is True


def test_scoring_below_minimum_threshold():
    scorer = AssociationScorer(ScoringConfig(min_association_score=0.60))
    gate = AssociationGate(GatingConfig(maximum_horizontal_distance=500.0, maximum_time_delta=10.0))
    t0 = datetime(2026, 8, 26, 12, 0, 0)

    # Moderate spatial distance (400m / 500m -> dist_score = 0.20)
    # Time delta 8s / 10s -> time_score = 0.20
    # Velocity diff 40 / 50 -> vel_score = 0.20
    # Heading diff 70 / 90 -> head_score = 0.22
    # Confidence diff 0.8 -> conf_score = 0.20
    track = make_track(last_seen_at=t0, lat=37.7749, lon=-122.4194, velocity=10.0, heading=10.0, confidence=0.1)
    det = make_detection(
        timestamp=t0 + timedelta(seconds=8.0),
        lat=37.7749 + 0.0036,  # ~400m
        lon=-122.4194,
        velocity=50.0,
        heading=80.0,
        confidence=0.9,
    )

    gate_res = gate.evaluate(det, track)
    assert gate_res.passed is True
    score_res = scorer.score(det, track, gate_res)
    assert score_res.score < 0.60
    assert score_res.passed is False
