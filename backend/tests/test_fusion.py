"""Unit and integration tests for multi-sensor fusion, quality scoring, and classification reconciliation."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import select

from app.fusion.classification import reconcile_classification
from app.fusion.consensus import fuse_kinematics
from app.fusion.quality import (
    calculate_source_diversity,
    compute_track_quality,
    decay_coasting_confidence,
)
from app.models.association import TrackAssociation, TrackAssociationDecision
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.track import Track, TrackState


def make_detection(
    det_id: str = "det-1",
    sensor_id: str = "sensor-1",
    lat: float = 37.7749,
    lon: float = -122.4194,
    altitude: float | None = 100.0,
    velocity: float | None = 15.0,
    heading: float | None = 90.0,
    confidence: float = 0.85,
    horizontal_uncertainty: float | None = None,
    classification: str | None = "UAV",
    timestamp: datetime | None = None,
) -> Detection:
    ts = timestamp or datetime(2026, 8, 26, 12, 0, 0)
    return Detection(
        id=det_id,
        sensor_id=sensor_id,
        source_detection_id=f"src-{det_id}",
        timestamp=ts,
        latitude=lat,
        longitude=lon,
        altitude=altitude,
        velocity=velocity,
        heading=heading,
        confidence=confidence,
        horizontal_uncertainty=horizontal_uncertainty,
        classification=classification,
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )


def make_track(
    track_id: str = "track-1",
    lat: float = 37.7740,
    lon: float = -122.4190,
    altitude: float | None = 100.0,
    velocity: float | None = 10.0,
    heading: float | None = 80.0,
    confidence: float = 0.80,
    classification: str | None = "UAV",
    source_count: int = 1,
) -> Track:
    ts = datetime(2026, 8, 26, 12, 0, 0)
    return Track(
        id=track_id,
        state=TrackState.ACTIVE,
        first_seen_at=ts,
        last_seen_at=ts,
        latitude=lat,
        longitude=lon,
        altitude=altitude,
        velocity=velocity,
        heading=heading,
        confidence=confidence,
        classification=classification,
        source_count=source_count,
    )


def test_fuse_kinematics_uncertainty_and_confidence_weighting():
    track = make_track(lat=37.7700, lon=-122.4100, confidence=0.80)
    # High certainty detection (small horizontal_uncertainty) -> higher weight
    det_certain = make_detection(lat=37.7800, lon=-122.4200, confidence=0.90, horizontal_uncertainty=2.0)
    fused_certain = fuse_kinematics(track, det_certain)
    assert fused_certain.weight_applied > 0.1

    # Low certainty detection (large horizontal_uncertainty) -> lower weight
    det_uncertain = make_detection(lat=37.7800, lon=-122.4200, confidence=0.90, horizontal_uncertainty=50.0)
    fused_uncertain = fuse_kinematics(track, det_uncertain)
    assert fused_uncertain.weight_applied < fused_certain.weight_applied


def test_fuse_kinematics_missing_dimensions_never_fabricated():
    track = make_track(altitude=None, velocity=None, heading=None)
    det = make_detection(altitude=None, velocity=None, heading=None)
    fused = fuse_kinematics(track, det)
    assert fused.altitude is None
    assert fused.velocity is None
    assert fused.heading is None

    # Only detection has altitude -> preserved without fabricating track velocity/heading
    det_with_alt = make_detection(altitude=150.0, velocity=None, heading=None)
    fused2 = fuse_kinematics(track, det_with_alt)
    assert fused2.altitude == 150.0
    assert fused2.velocity is None


def test_fuse_kinematics_heading_minimal_angular_interpolation():
    track = make_track(heading=10.0)
    # Detection across 0/360 boundary (350 deg, diff is 20 deg counterclockwise)
    det = make_detection(heading=350.0)
    fused = fuse_kinematics(track, det)
    # Interpolated heading should be near 360/0, not near (10+350)/2 = 180!
    assert (fused.heading <= 10.0 or fused.heading >= 340.0)
    assert not (150.0 <= fused.heading <= 210.0)


def test_source_diversity_calculation():
    # 0 sensors
    assert calculate_source_diversity(0, 0) == 0.0
    # 1 sensor, 1 modality -> baseline 0.30
    assert calculate_source_diversity(1, 1) == 0.30
    # 2 sensors, 1 modality -> 0.40 * 1 + 0.30 * 1 = 0.70
    assert calculate_source_diversity(2, 1) == 0.70
    # 2 sensors, 2 modalities (e.g. Radar + Optical) -> 0.40 * 1 + 0.30 * 2 = 1.00
    assert calculate_source_diversity(2, 2) == 1.00
    # Capped at 1.0
    assert calculate_source_diversity(5, 4) == 1.00


def test_coasting_confidence_decay():
    # Zero elapsed -> no decay
    assert decay_coasting_confidence(0.80, 0.0) == 0.80

    # 30 seconds elapsed (1 half-life with tau=30s) -> decays to ~0.40
    decayed_30s = decay_coasting_confidence(0.80, 30.0, half_life_seconds=30.0)
    assert pytest.approx(decayed_30s, rel=1e-2) == 0.40

    # 60 seconds elapsed (2 half-lives) -> decays to ~0.20
    decayed_60s = decay_coasting_confidence(0.80, 60.0, half_life_seconds=30.0)
    assert pytest.approx(decayed_60s, rel=1e-2) == 0.20

    # Never decays below 0.0
    assert decay_coasting_confidence(0.80, 10000.0) >= 0.0


def test_track_quality_scoring_and_bounds(database):
    sensor1 = Sensor(id="s-q1", name="Radar 1", source_type="radar", source_class=SensorSourceClass.SIMULATION)
    sensor2 = Sensor(id="s-q2", name="Optical 1", source_type="optical", source_class=SensorSourceClass.SIMULATION)
    database.add_all([sensor1, sensor2])
    database.commit()

    t0 = datetime(2026, 8, 26, 12, 0, 0)
    track = Track(
        id="track-q1",
        state=TrackState.ACTIVE,
        first_seen_at=t0,
        last_seen_at=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.85,
        source_count=2,
    )
    database.add(track)

    d1 = Detection(
        id="det-q1",
        sensor_id=sensor1.id,
        source_detection_id="src-q1",
        timestamp=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.85,
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    d2 = Detection(
        id="det-q2",
        sensor_id=sensor2.id,
        source_detection_id="src-q2",
        timestamp=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.80,
        source_class=SensorSourceClass.SIMULATION,
        source_type="optical",
        metadata_json={},
    )
    database.add_all([d1, d2])
    database.commit()

    # Add associations from both sensors
    a1 = TrackAssociation(
        id="assoc-q1",
        detection_id=d1.id,
        track_id=track.id,
        sensor_id=sensor1.id,
        timestamp=t0,
        distance_meters=10.0,
        score=0.95,
        decision=TrackAssociationDecision.ASSOCIATED,
        reason="Match",
        created_at=t0,
    )
    a2 = TrackAssociation(
        id="assoc-q2",
        detection_id=d2.id,
        track_id=track.id,
        sensor_id=sensor2.id,
        timestamp=t0,
        distance_meters=15.0,
        score=0.90,
        decision=TrackAssociationDecision.ASSOCIATED,
        reason="Match",
        created_at=t0,
    )
    database.add_all([a1, a2])
    database.commit()

    quality = compute_track_quality(database, track, latest_distance_meters=10.0, now=t0)
    assert 0.0 <= quality.quality <= 1.0
    assert quality.distinct_sensors == 2
    assert quality.distinct_modalities == 2
    assert quality.diversity_component == 1.0
    assert quality.confidence_component == 0.85


def test_classification_reconciliation_voting_and_tie_breaking(database):
    sensor = Sensor(id="s-v1", name="Radar V", source_type="radar", source_class=SensorSourceClass.SIMULATION)
    database.add(sensor)
    database.commit()

    t0 = datetime(2026, 8, 26, 12, 0, 0)
    track = Track(
        id="track-v1",
        state=TrackState.ACTIVE,
        first_seen_at=t0,
        last_seen_at=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.80,
        classification="UAV",
        source_count=1,
    )
    d1 = Detection(
        id="det-v1",
        sensor_id=sensor.id,
        source_detection_id="src-v1",
        timestamp=t0,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.90,
        classification="DRONE",
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    d2 = Detection(
        id="det-v2",
        sensor_id=sensor.id,
        source_detection_id="src-v2",
        timestamp=t0 + timedelta(seconds=2),
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.40,
        classification="BIRD",
        source_class=SensorSourceClass.SIMULATION,
        source_type="radar",
        metadata_json={},
    )
    database.add_all([track, d1, d2])
    database.commit()

    a1 = TrackAssociation(
        id="a-v1",
        detection_id=d1.id,
        track_id=track.id,
        sensor_id=sensor.id,
        timestamp=d1.timestamp,
        decision=TrackAssociationDecision.ASSOCIATED,
        reason="Match",
        created_at=t0,
    )
    a2 = TrackAssociation(
        id="a-v2",
        detection_id=d2.id,
        track_id=track.id,
        sensor_id=sensor.id,
        timestamp=d2.timestamp,
        decision=TrackAssociationDecision.ASSOCIATED,
        reason="Match",
        created_at=t0,
    )
    database.add_all([a1, a2])
    database.commit()

    res = reconcile_classification(database, track, latest_detection=d2)
    # DRONE has 0.90 score, BIRD has 0.40 score -> DRONE wins!
    assert res.reconciled_classification == "DRONE"
    assert res.evidence_scores["DRONE"] == 0.90
    assert res.evidence_scores["BIRD"] == 0.40
