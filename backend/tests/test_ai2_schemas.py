"""Unit tests for Stage AI2 multi-track intelligence contracts and behavioral schemas."""

from datetime import UTC, datetime
import pytest
from pydantic import ValidationError

from ai.schemas import (
    BehavioralState,
    BehaviorClassification,
    CoordinatedFormation,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    ThreatPriorityFactor,
    TrackGroup,
)


def test_behavioral_state_enum_completeness():
    """Verify all 7 required operational behavioral states exist."""
    expected_states = {
        "NORMAL",
        "APPROACHING",
        "DEPARTING",
        "LOITERING",
        "RAPID_CHANGE",
        "COORDINATED",
        "ANOMALOUS",
    }
    actual_states = {s.value for s in BehavioralState}
    assert actual_states == expected_states
    assert len(BehavioralState) == 7


def test_track_group_valid_construction():
    """Verify valid TrackGroup construction."""
    now = datetime.now(UTC)
    group = TrackGroup(
        group_id="GRP-ALPHA-01",
        member_track_ids=["TRK-01", "TRK-02", "TRK-03"],
        centroid_lat=37.7749,
        centroid_lon=-122.4194,
        centroid_alt=150.0,
        radius_meters=85.5,
        member_count=3,
        confidence=0.92,
        behavioral_state=BehavioralState.COORDINATED,
        updated_at=now,
    )
    assert group.group_id == "GRP-ALPHA-01"
    assert len(group.member_track_ids) == 3
    assert group.behavioral_state == BehavioralState.COORDINATED
    assert group.radius_meters == 85.5


def test_track_group_rejects_empty_or_duplicate_members():
    """Verify TrackGroup validator rejects empty lists and duplicates."""
    with pytest.raises(ValidationError):
        TrackGroup(
            group_id="GRP-01",
            member_track_ids=[],
            centroid_lat=37.77,
            centroid_lon=-122.41,
        )

    with pytest.raises(ValidationError):
        TrackGroup(
            group_id="GRP-01",
            member_track_ids=["TRK-01", "TRK-01"],
            centroid_lat=37.77,
            centroid_lon=-122.41,
        )


def test_behavior_classification_validation():
    """Verify BehaviorClassification validation and bounds."""
    now = datetime.now(UTC)
    classification = BehaviorClassification(
        track_id="TRK-100",
        state=BehavioralState.LOITERING,
        confidence=0.88,
        duration_seconds=45.2,
        reason="Compact orbit detected with radius 42m over 45s",
        contributing_factors=["low_directional_consistency", "elevated_radius_of_gyration"],
        evaluated_at=now,
    )
    assert classification.track_id == "TRK-100"
    assert classification.state == BehavioralState.LOITERING
    assert classification.duration_seconds == 45.2

    # Negative duration rejected
    with pytest.raises(ValidationError):
        BehaviorClassification(
            track_id="TRK-100",
            state=BehavioralState.NORMAL,
            confidence=0.8,
            duration_seconds=-5.0,
            reason="Invalid duration",
        )

    # Confidence > 1.0 rejected
    with pytest.raises(ValidationError):
        BehaviorClassification(
            track_id="TRK-100",
            state=BehavioralState.NORMAL,
            confidence=1.5,
            duration_seconds=10.0,
            reason="Invalid confidence",
        )


def test_coordinated_formation_validation():
    """Verify CoordinatedFormation validation and minimum member bounds."""
    formation = CoordinatedFormation(
        formation_id="FORM-01",
        group_id="GRP-01",
        member_track_ids=["TRK-01", "TRK-02"],
        synchronization_index=0.94,
        heading_dispersion_deg=8.5,
        velocity_dispersion_mps=1.2,
        confidence=0.91,
    )
    assert formation.synchronization_index == 0.94
    assert len(formation.member_track_ids) == 2

    # Single track formation rejected (< 2 members)
    with pytest.raises(ValidationError):
        CoordinatedFormation(
            formation_id="FORM-01",
            group_id="GRP-01",
            member_track_ids=["TRK-01"],
            synchronization_index=0.9,
            heading_dispersion_deg=5.0,
            velocity_dispersion_mps=1.0,
            confidence=0.9,
        )

    # Synchronization index > 1.0 rejected
    with pytest.raises(ValidationError):
        CoordinatedFormation(
            formation_id="FORM-01",
            group_id="GRP-01",
            member_track_ids=["TRK-01", "TRK-02"],
            synchronization_index=1.25,
            heading_dispersion_deg=5.0,
            velocity_dispersion_mps=1.0,
            confidence=0.9,
        )


def test_threat_priority_assessment_bounds():
    """Verify ThreatPriorityAssessment score bounds (0-100) and factor breakdown."""
    assessment = ThreatPriorityAssessment(
        track_id="TRK-200",
        group_id="GRP-ALPHA",
        priority_score=78.5,
        priority_level="HIGH",
        confidence=0.95,
        factors=[
            ThreatPriorityFactor(
                name="geofence_ingress",
                score=85.0,
                weight=0.30,
                contribution=25.5,
                description="Approaching Sector Alpha in ~14s",
            ),
            ThreatPriorityFactor(
                name="behavioral_state",
                score=70.0,
                weight=0.25,
                contribution=17.5,
                description="Rapid change and closing vector",
            ),
        ],
        reason="High priority defensive concern due to imminent perimeter ingress",
    )
    assert assessment.priority_score == 78.5
    assert assessment.priority_level == "HIGH"
    assert len(assessment.factors) == 2

    # Priority score > 100 rejected
    with pytest.raises(ValidationError):
        ThreatPriorityAssessment(
            track_id="TRK-200",
            priority_score=110.0,
            priority_level="CRITICAL",
            confidence=0.9,
            reason="Invalid score",
        )

    # Priority score < 0 rejected
    with pytest.raises(ValidationError):
        ThreatPriorityAssessment(
            track_id="TRK-200",
            priority_score=-10.0,
            priority_level="LOW",
            confidence=0.9,
            reason="Invalid score",
        )


def test_multi_track_intelligence_summary_serialization():
    """Verify MultiTrackIntelligenceSummary serialization round-trip."""
    now = datetime.now(UTC)
    group = TrackGroup(
        group_id="GRP-01",
        member_track_ids=["TRK-01", "TRK-02"],
        centroid_lat=37.7749,
        centroid_lon=-122.4194,
        radius_meters=45.0,
        member_count=2,
        confidence=0.95,
        behavioral_state=BehavioralState.NORMAL,
        updated_at=now,
    )
    behavior = BehaviorClassification(
        track_id="TRK-01",
        state=BehavioralState.NORMAL,
        confidence=0.95,
        duration_seconds=60.0,
        reason="Nominal linear flight",
        evaluated_at=now,
    )
    priority = ThreatPriorityAssessment(
        track_id="TRK-01",
        group_id="GRP-01",
        priority_score=25.0,
        priority_level="LOW",
        confidence=0.95,
        reason="Low defensive concern",
        evaluated_at=now,
    )

    summary = MultiTrackIntelligenceSummary(
        groups=[group],
        behaviors=[behavior],
        formations=[],
        priorities=[priority],
        evaluated_at=now,
    )

    data = summary.model_dump(mode="json")
    assert isinstance(data, dict)
    assert len(data["groups"]) == 1
    assert data["groups"][0]["group_id"] == "GRP-01"
    assert data["behaviors"][0]["state"] == "NORMAL"
    assert data["priorities"][0]["priority_score"] == 25.0

    # Validate reconstructed instance
    reconstructed = MultiTrackIntelligenceSummary.model_validate(data)
    assert reconstructed.groups[0].group_id == group.group_id
    assert reconstructed.behaviors[0].state == BehavioralState.NORMAL
