"""Comprehensive test suite for Stage AI2-E Explainable Defensive Threat Prioritization Engine."""

from datetime import UTC, datetime, timedelta
import math
import pytest
from sqlalchemy.orm import Session

from ai.anomaly.models import AnomalyScoringConfig
from ai.anomaly.persistent import (
    PersistentAnomalyAccumulator,
    PersistentAnomalyConfig,
    PersistentAnomalyResult,
)
from ai.anomaly.scoring import evaluate_anomaly
from ai.behavior.classifier import (
    BehaviorClassifierConfig,
    ClassifierInput,
    classify_track_behavior,
)
from ai.correlation.coordination import compute_coordination_index
from ai.correlation.grouping import TrackGroup, correlate_tracks
from ai.priority.scoring import (
    BEHAVIOR_PRIORITY_MAP,
    PriorityScoringConfig,
    classify_priority_level,
    evaluate_threat_priority,
    normalize_anomaly_component,
    normalize_behavior_component,
    normalize_coordination_component,
    normalize_geofence_component,
    normalize_kinematic_component,
)
from ai.schemas import (
    AnomalyAssessment,
    AnomalyCategory,
    BehaviorClassification,
    BehavioralState,
    CoordinatedFormation,
    GeofenceIngressEstimate,
    KinematicFeatures,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    ThreatPriorityFactor,
)
from ai.service import DefensiveIntelligenceService
from app.models.geofence import Geofence
from app.models.sensor import SensorSourceClass
from app.models.track import Track, TrackHistory, TrackState


# ─────────────────────────────────────────────────────────────────────────────
# 1. Formula & Exact Weights
# ─────────────────────────────────────────────────────────────────────────────

def test_priority_weights_sum_to_one():
    """Verify default priority scoring weights sum exactly to 1.00."""
    cfg = PriorityScoringConfig()
    total_weight = (
        cfg.weight_geofence
        + cfg.weight_behavior
        + cfg.weight_anomaly
        + cfg.weight_coordination
        + cfg.weight_kinematic
    )
    assert math.isclose(total_weight, 1.00, rel_tol=1e-9)
    assert cfg.weight_geofence == 0.30
    assert cfg.weight_behavior == 0.25
    assert cfg.weight_anomaly == 0.20
    assert cfg.weight_coordination == 0.15
    assert cfg.weight_kinematic == 0.10


def test_all_components_zero():
    """Verify priority assessment when all components are zero."""
    res = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=0.0,
        p_behavior_override=0.0,
        p_anomaly_override=0.0,
        p_coordination_override=0.0,
        p_kinematic_override=0.0,
        sensor_confidence=1.0,
    )
    assert res.priority_score == 0.0
    assert res.priority_level == "LOW"
    assert len(res.factors) == 5
    assert all(f.contribution == 0.0 for f in res.factors)


def test_all_components_maximum():
    """Verify priority assessment when all components are maximum (100.0)."""
    res = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=100.0,
        p_behavior_override=100.0,
        p_anomaly_override=100.0,
        p_coordination_override=100.0,
        p_kinematic_override=100.0,
        sensor_confidence=1.0,
    )
    assert res.priority_score == 100.0
    assert res.priority_level == "CRITICAL"
    assert len(res.factors) == 5
    # Factor contributions: 30 + 25 + 20 + 15 + 10 = 100
    contribs = {f.name: f.contribution for f in res.factors}
    assert contribs["Defensive Geofence Ingress & Proximity"] == 30.0
    assert contribs["Behavioral Classification"] == 25.0
    assert contribs["Persistent Anomaly Profile"] == 20.0
    assert contribs["Multi-Track Coordination"] == 15.0
    assert contribs["Kinematic Dynamics & Velocity"] == 10.0


def test_exact_weighted_formula():
    """Verify mathematical calculation with arbitrary component values."""
    # P_base = 0.30*80 + 0.25*60 + 0.20*50 + 0.15*40 + 0.10*20
    #        = 24.0 + 15.0 + 10.0 + 6.0 + 2.0 = 57.0
    # P_scaled (conf=1.0) = 57.0 * (0.30 + 0.70*1.0) = 57.0
    res = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=80.0,
        p_behavior_override=60.0,
        p_anomaly_override=50.0,
        p_coordination_override=40.0,
        p_kinematic_override=20.0,
        sensor_confidence=1.0,
    )
    assert res.priority_score == 57.0
    assert res.priority_level == "MEDIUM"


# ─────────────────────────────────────────────────────────────────────────────
# 2. Confidence Scaling & Boundaries
# ─────────────────────────────────────────────────────────────────────────────

def test_confidence_scaling_zero():
    """Verify confidence scaling when sensor confidence is 0.0 (preserves 30% baseline)."""
    # P_base = 100.0
    # P_scaled = 100.0 * (0.30 + 0.70 * 0.0) = 30.0
    res = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=100.0,
        p_behavior_override=100.0,
        p_anomaly_override=100.0,
        p_coordination_override=100.0,
        p_kinematic_override=100.0,
        sensor_confidence=0.0,
    )
    assert res.priority_score == 30.0
    assert res.priority_level == "MEDIUM"
    assert res.confidence == 0.0


def test_confidence_scaling_one():
    """Verify confidence scaling when sensor confidence is 1.0 (100% full weight)."""
    # P_base = 80.0
    # P_scaled = 80.0 * (0.30 + 0.70 * 1.0) = 80.0
    res = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=80.0,
        p_behavior_override=80.0,
        p_anomaly_override=80.0,
        p_coordination_override=80.0,
        p_kinematic_override=80.0,
        sensor_confidence=1.0,
    )
    assert res.priority_score == 80.0
    assert res.priority_level == "CRITICAL"


def test_confidence_scaling_midpoint():
    """Verify confidence scaling at intermediate confidence (C_s = 0.50)."""
    # P_base = 100.0
    # scale = 0.30 + 0.70 * 0.50 = 0.65
    # P_final = 65.0
    res = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=100.0,
        p_behavior_override=100.0,
        p_anomaly_override=100.0,
        p_coordination_override=100.0,
        p_kinematic_override=100.0,
        sensor_confidence=0.5,
    )
    assert res.priority_score == 65.0
    assert res.priority_level == "HIGH"


def test_score_clamping():
    """Verify priority score clamping to [0.0, 100.0]."""
    res_high = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=200.0,
        p_behavior_override=150.0,
        p_anomaly_override=120.0,
        p_coordination_override=100.0,
        p_kinematic_override=100.0,
        sensor_confidence=1.5,
    )
    assert res_high.priority_score == 100.0
    assert res_high.confidence == 1.0

    res_low = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=-50.0,
        p_behavior_override=-20.0,
        p_anomaly_override=-10.0,
        p_coordination_override=-5.0,
        p_kinematic_override=0.0,
        sensor_confidence=-0.5,
    )
    assert res_low.priority_score == 0.0
    assert res_low.confidence == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 3. Exact Priority Level Boundaries
# ─────────────────────────────────────────────────────────────────────────────

def test_priority_level_boundaries():
    """Test exact boundary transitions for LOW, MEDIUM, HIGH, CRITICAL."""
    cfg = PriorityScoringConfig()
    # LOW < 30.0
    assert classify_priority_level(0.0, cfg) == "LOW"
    assert classify_priority_level(29.9, cfg) == "LOW"

    # MEDIUM in [30.0, 60.0)
    assert classify_priority_level(30.0, cfg) == "MEDIUM"
    assert classify_priority_level(59.9, cfg) == "MEDIUM"

    # HIGH in [60.0, 80.0)
    assert classify_priority_level(60.0, cfg) == "HIGH"
    assert classify_priority_level(79.9, cfg) == "HIGH"

    # CRITICAL >= 80.0
    assert classify_priority_level(80.0, cfg) == "CRITICAL"
    assert classify_priority_level(100.0, cfg) == "CRITICAL"


# ─────────────────────────────────────────────────────────────────────────────
# 4. Behavioral State Normalization
# ─────────────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize(
    ("state", "expected_score"),
    [
        (BehavioralState.NORMAL, 10.0),
        (BehavioralState.DEPARTING, 20.0),
        (BehavioralState.LOITERING, 50.0),
        (BehavioralState.APPROACHING, 70.0),
        (BehavioralState.COORDINATED, 80.0),
        (BehavioralState.RAPID_CHANGE, 85.0),
        (BehavioralState.ANOMALOUS, 90.0),
    ],
)
def test_behavior_state_deterministic_mapping(state: BehavioralState, expected_score: float):
    """Verify exact score mapping for each of the 7 AI2 behavioral states."""
    score, desc = normalize_behavior_component(state)
    assert score == expected_score
    assert state.value in desc

    # Also test passing BehaviorClassification instance
    b_class = BehaviorClassification(
        track_id="TRK-B01",
        state=state,
        confidence=0.9,
        duration_seconds=15.0,
        reason=f"Testing {state.value}",
        evaluated_at=datetime.now(UTC),
    )
    score_obj, desc_obj = normalize_behavior_component(b_class)
    assert score_obj == expected_score
    assert "Testing" in desc_obj


def test_behavior_missing_fallback():
    """Verify missing behavior defaults to NORMAL baseline (10.0)."""
    score, desc = normalize_behavior_component(None)
    assert score == 10.0
    assert "NORMAL" in desc


# ─────────────────────────────────────────────────────────────────────────────
# 5. Geofence Normalization & Boundaries
# ─────────────────────────────────────────────────────────────────────────────

def test_geofence_inside_normalization():
    """Verify INSIDE geofence status maps to 100.0."""
    est = GeofenceIngressEstimate(
        track_id="TRK-G01",
        geofence_id="GEO-01",
        geofence_name="Alpha Zone",
        status="INSIDE",
        evaluated_at=datetime.now(UTC),
    )
    score, desc = normalize_geofence_component([est])
    assert score == 100.0
    assert "INSIDE" in desc
    assert "Alpha Zone" in desc


def test_geofence_approaching_normalization_time_scaling():
    """Verify APPROACHING geofence status maps deterministically between 30 and 100."""
    now = datetime.now(UTC)

    # Imminent breach (TTB = 0s) -> 100.0
    est_0 = GeofenceIngressEstimate(
        track_id="TRK-G01",
        geofence_id="GEO-01",
        geofence_name="Alpha Zone",
        estimated_time_to_breach_seconds=0.0,
        status="APPROACHING",
        evaluated_at=now,
    )
    score_0, _ = normalize_geofence_component([est_0])
    assert score_0 == 100.0

    # Intermediate breach (TTB = 30s) -> 100 - (30/60)*70 = 65.0
    est_30 = GeofenceIngressEstimate(
        track_id="TRK-G01",
        geofence_id="GEO-01",
        geofence_name="Alpha Zone",
        estimated_time_to_breach_seconds=30.0,
        status="APPROACHING",
        evaluated_at=now,
    )
    score_30, desc_30 = normalize_geofence_component([est_30])
    assert score_30 == 65.0
    assert "30.0s" in desc_30

    # Horizon limit (TTB = 60s) -> 30.0
    est_60 = GeofenceIngressEstimate(
        track_id="TRK-G01",
        geofence_id="GEO-01",
        geofence_name="Alpha Zone",
        estimated_time_to_breach_seconds=60.0,
        status="APPROACHING",
        evaluated_at=now,
    )
    score_60, _ = normalize_geofence_component([est_60])
    assert score_60 == 30.0

    # Distant breach (TTB = 120s > 60s) -> 30.0
    est_120 = GeofenceIngressEstimate(
        track_id="TRK-G01",
        geofence_id="GEO-01",
        geofence_name="Alpha Zone",
        estimated_time_to_breach_seconds=120.0,
        status="APPROACHING",
        evaluated_at=now,
    )
    score_120, _ = normalize_geofence_component([est_120])
    assert score_120 == 30.0


def test_geofence_diverging_and_no_intersection():
    """Verify DIVERGING maps to 15.0 and NO_INTERSECTION maps to 0.0."""
    now = datetime.now(UTC)
    est_div = GeofenceIngressEstimate(
        track_id="TRK-G01",
        geofence_id="GEO-01",
        geofence_name="Alpha",
        status="DIVERGING",
        evaluated_at=now,
    )
    score_div, _ = normalize_geofence_component([est_div])
    assert score_div == 15.0

    est_none = GeofenceIngressEstimate(
        track_id="TRK-G01",
        geofence_id="GEO-01",
        geofence_name="Alpha",
        status="NO_INTERSECTION",
        evaluated_at=now,
    )
    score_none, _ = normalize_geofence_component([est_none])
    assert score_none == 0.0


def test_geofence_missing_fallback():
    """Verify missing / empty geofence estimates fallback to 0.0."""
    score_none, _ = normalize_geofence_component(None)
    assert score_none == 0.0

    score_empty, _ = normalize_geofence_component([])
    assert score_empty == 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 6. Persistent Anomaly Integration
# ─────────────────────────────────────────────────────────────────────────────

def test_persistent_anomaly_integration():
    """Verify integration with AI2-D PersistentAnomalyAccumulator."""
    accum = PersistentAnomalyAccumulator(PersistentAnomalyConfig())
    t0 = datetime.now(UTC)

    # Accumulate anomaly ticks (first tick initializes baseline, second tick blends new score)
    accum.update("TRK-A01", instantaneous_score=85.0, timestamp=t0)
    r2 = accum.update("TRK-A01", instantaneous_score=85.0, timestamp=t0 + timedelta(seconds=10))
    score2, desc2 = normalize_anomaly_component(r2)
    assert score2 == round(r2.persistent_score, 1)
    assert score2 > 0.0

    # Directly pass PersistentAnomalyResult
    res = evaluate_threat_priority(
        track_id="TRK-A01",
        persistent_anomaly=r2,
        sensor_confidence=1.0,
    )
    assert res.factors[2].name == "Persistent Anomaly Profile"
    assert res.factors[2].score == round(r2.persistent_score, 1)


def test_persistent_anomaly_missing_fallback():
    """Verify missing persistent anomaly defaults to 0.0."""
    score, desc = normalize_anomaly_component(None)
    assert score == 0.0
    assert "fallback" in desc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 7. Coordination Integration
# ─────────────────────────────────────────────────────────────────────────────

def test_coordination_integration():
    """Verify integration with AI2-D CoordinatedFormation synchronization index."""
    formation = CoordinatedFormation(
        formation_id="FMT-GRP-01",
        group_id="GRP-01",
        member_track_ids=["TRK-01", "TRK-02"],
        synchronization_index=0.88,
        heading_dispersion_deg=5.0,
        velocity_dispersion_mps=0.8,
        confidence=0.95,
        evaluated_at=datetime.now(UTC),
    )
    score, desc = normalize_coordination_component(formation)
    assert score == 88.0
    assert "FMT-GRP-01" in desc

    # Raw float sync index in [0, 1]
    score_raw, _ = normalize_coordination_component(0.75)
    assert score_raw == 75.0


def test_coordination_missing_fallback():
    """Verify missing coordination evidence defaults to 0.0."""
    score, desc = normalize_coordination_component(None)
    assert score == 0.0
    assert "fallback" in desc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 8. Kinematic Integration
# ─────────────────────────────────────────────────────────────────────────────

def test_kinematic_integration_features():
    """Verify kinematic normalization from AI1 KinematicFeatures."""
    features = KinematicFeatures(
        speed_mps=25.0,        # 25/50 * 40 = 20 pts
        acceleration_mps2=5.0, # 5/10 * 30 = 15 pts
        turn_rate_dps=30.0,    # 30/60 * 30 = 15 pts
        directional_consistency=0.9,
    )
    score, desc = normalize_kinematic_component(features)
    # Expected: 20 + 15 + 15 = 50.0
    assert score == 50.0
    assert "speed=25.0" in desc


def test_kinematic_integration_anomaly_assessment():
    """Verify kinematic normalization from AI1 AnomalyAssessment."""
    assessment = AnomalyAssessment(
        track_id="TRK-K01",
        anomaly_score=64.2,
        anomaly_level="HIGH",
        primary_category=AnomalyCategory.RAPID_ALTITUDE_CHANGE,
        sensor_confidence=0.95,
        summary="High vertical speed",
        evaluated_at=datetime.now(UTC),
    )
    score, desc = normalize_kinematic_component(assessment)
    assert score == 64.2
    assert "RAPID_ALTITUDE_CHANGE" in desc


def test_kinematic_missing_fallback():
    """Verify missing kinematic evidence defaults to 0.0."""
    score, desc = normalize_kinematic_component(None)
    assert score == 0.0
    assert "fallback" in desc.lower()


# ─────────────────────────────────────────────────────────────────────────────
# 9. Explainable Factor Reconciliation & Idempotence
# ─────────────────────────────────────────────────────────────────────────────

def test_explainable_factor_reconciliation():
    """Verify sum of factor contributions equals base score mathematically."""
    res = evaluate_threat_priority(
        track_id="TRK-001",
        p_geofence_override=75.0,
        p_behavior_override=85.0,
        p_anomaly_override=60.0,
        p_coordination_override=90.0,
        p_kinematic_override=45.0,
        sensor_confidence=0.8,
    )
    # Expected base:
    # 0.30*75 + 0.25*85 + 0.20*60 + 0.15*90 + 0.10*45
    # = 22.5 + 21.25 + 12.0 + 13.5 + 4.5 = 73.75
    sum_contributions = sum(f.contribution for f in res.factors)
    assert math.isclose(sum_contributions, 73.75, abs_tol=0.01)

    # Scaled score:
    # 73.75 * (0.30 + 0.70*0.8) = 73.75 * 0.86 = 63.425 -> 63.4
    assert res.priority_score == 63.4
    assert res.priority_level == "HIGH"


def test_deterministic_repeated_evaluation():
    """Verify priority evaluation is 100% deterministic and idempotent."""
    t0 = datetime(2026, 8, 27, 12, 0, 0, tzinfo=UTC)
    res1 = evaluate_threat_priority(
        track_id="TRK-DET-01",
        p_geofence_override=65.0,
        p_behavior_override=70.0,
        p_anomaly_override=40.0,
        p_coordination_override=80.0,
        p_kinematic_override=30.0,
        sensor_confidence=0.95,
        evaluated_at=t0,
    )
    res2 = evaluate_threat_priority(
        track_id="TRK-DET-01",
        p_geofence_override=65.0,
        p_behavior_override=70.0,
        p_anomaly_override=40.0,
        p_coordination_override=80.0,
        p_kinematic_override=30.0,
        sensor_confidence=0.95,
        evaluated_at=t0,
    )
    assert res1.model_dump() == res2.model_dump()


def test_per_track_isolation():
    """Verify evaluations for separate tracks are completely isolated."""
    t1 = evaluate_threat_priority(
        track_id="TRK-ISO-01",
        p_geofence_override=100.0,
        sensor_confidence=1.0,
    )
    t2 = evaluate_threat_priority(
        track_id="TRK-ISO-02",
        p_geofence_override=0.0,
        sensor_confidence=1.0,
    )
    assert t1.track_id == "TRK-ISO-01"
    assert t2.track_id == "TRK-ISO-02"
    assert t1.priority_score > t2.priority_score


def test_malformed_out_of_range_handling():
    """Verify graceful handling of out-of-range or malformed inputs."""
    res = evaluate_threat_priority(
        track_id="TRK-MAL",
        behavior="UNRECOGNIZED_BEHAVIOR_STATE",
        coordination=-2.5,
        kinematics=999.0,
        sensor_confidence=5.0,
    )
    assert 0.0 <= res.priority_score <= 100.0
    assert res.confidence == 1.0
    assert res.priority_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")


# ─────────────────────────────────────────────────────────────────────────────
# 10. Service Integration Tests (AI1 + AI2)
# ─────────────────────────────────────────────────────────────────────────────

def test_defensive_service_evaluate_track_with_priority(database: Session):
    """Verify DefensiveIntelligenceService.evaluate_track computes and includes priority."""
    now = datetime.now(UTC).replace(tzinfo=None)

    # 1. Create track with history
    track = Track(
        id="TRK-PRIO-001",
        state=TrackState.ACTIVE,
        first_seen_at=now - timedelta(seconds=20),
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=150.0,
        velocity=30.0,
        heading=45.0,
        confidence=0.95,
        classification="UAV",
        source_count=2,
        created_at=now,
        updated_at=now,
    )
    database.add(track)

    for i in range(5):
        hist = TrackHistory(
            track_id="TRK-PRIO-001",
            sequence=i + 1,
            timestamp=now - timedelta(seconds=20 - (i * 4)),
            latitude=37.7749 + (i * 0.0003),
            longitude=-122.4194 + (i * 0.0003),
            altitude=150.0,
            velocity=30.0,
            heading=45.0,
            confidence=0.95,
            state=TrackState.ACTIVE,
            provenance=SensorSourceClass.REAL,
            source_detection_ids=[f"DET-PRIO-{i}"],
            created_at=now,
        )
        database.add(hist)

    geofence = Geofence(
        id="GEO-PRIO-01",
        name="Sector Bravo",
        geometry={"type": "BBOX", "min_lat": 37.7700, "max_lat": 37.7800, "min_lon": -122.4300, "max_lon": -122.4100},
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    database.add(geofence)
    database.commit()

    summary = DefensiveIntelligenceService.evaluate_track(
        database, track, geofences=[geofence], publish_events=False
    )

    assert summary is not None
    assert summary.track_id == "TRK-PRIO-001"
    assert summary.priority is not None
    assert summary.priority.track_id == "TRK-PRIO-001"
    assert 0.0 <= summary.priority.priority_score <= 100.0
    assert summary.priority.priority_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(summary.priority.factors) == 5


def test_defensive_service_evaluate_multi_track_intelligence():
    """Verify DefensiveIntelligenceService.evaluate_multi_track_intelligence."""
    t0 = datetime.now(UTC)

    # 3 tracks flying in close formation
    tracks = [
        {
            "id": "TRK-MT-01",
            "latitude": 37.7749,
            "longitude": -122.4194,
            "altitude": 100.0,
            "velocity": 20.0,
            "heading": 90.0,
            "confidence": 0.95,
            "timestamp": t0,
        },
        {
            "id": "TRK-MT-02",
            "latitude": 37.7751,
            "longitude": -122.4192,
            "altitude": 102.0,
            "velocity": 20.2,
            "heading": 91.0,
            "confidence": 0.92,
            "timestamp": t0,
        },
        {
            "id": "TRK-MT-03",
            "latitude": 37.7748,
            "longitude": -122.4195,
            "altitude": 99.0,
            "velocity": 19.8,
            "heading": 89.5,
            "confidence": 0.90,
            "timestamp": t0,
        },
    ]

    summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(tracks, now=t0)

    assert isinstance(summary, MultiTrackIntelligenceSummary)
    assert len(summary.groups) == 1
    assert summary.groups[0].member_count == 3
    assert len(summary.formations) == 1
    assert summary.formations[0].synchronization_index > 0.85
    assert len(summary.behaviors) == 3
    assert len(summary.priorities) == 3

    # All tracks should receive coordinated priority contribution
    for p in summary.priorities:
        assert p.priority_score > 0.0
        assert len(p.factors) == 5
        coord_factor = next(f for f in p.factors if f.name == "Multi-Track Coordination")
        assert coord_factor.score > 80.0
