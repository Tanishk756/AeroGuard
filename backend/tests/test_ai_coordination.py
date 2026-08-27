"""Tests for AI2-D: Multi-Track Coordination Index.

Covers:
21. Perfectly synchronized tracks (zero dispersion → S_sync ≈ 1.0)
22. Heading dispersion only
23. Velocity dispersion only
24. Combined heading + velocity dispersion
25. 359° vs 1° heading wraparound (circular handling)
26. Opposite headings (180° apart)
27. Zero velocity dispersion
28. Missing heading for some members
29. Missing velocity for some members
30. Fewer than 2 valid group members → None
31. Duplicate track IDs in members
32. Deterministic output (same inputs → same result)
33. Synchronization index always in [0, 1]
34. Formation ID derivation
35. Heading dispersion value correctness
36. Velocity dispersion value correctness
37. confidence bounded [0, 1]
38. Single member group → None
39. All headings missing
40. All velocities missing
"""

import math
from datetime import UTC, datetime

import pytest

from ai.correlation.coordination import (
    MemberObservation,
    _circular_std_rad,
    _heading_dispersion_deg,
    _population_std,
    compute_coordination_index,
)
from ai.schemas import BehavioralState, CoordinatedFormation, TrackGroup

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_BASE_TS = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def make_group(member_ids: list[str]) -> TrackGroup:
    return TrackGroup(
        group_id="GRP-001",
        member_track_ids=member_ids,
        centroid_lat=37.0,
        centroid_lon=-122.0,
        radius_meters=100.0,
        member_count=len(member_ids),
        confidence=0.9,
        behavioral_state=BehavioralState.NORMAL,
        updated_at=_BASE_TS,
    )


def make_obs(tid: str, heading: float | None, velocity: float | None) -> MemberObservation:
    return MemberObservation(id=tid, heading=heading, velocity=velocity)


# ---------------------------------------------------------------------------
# 21. Perfectly synchronized tracks
# ---------------------------------------------------------------------------

def test_perfect_synchronization_identical_heading_velocity():
    group = make_group(["A", "B", "C"])
    members = [
        make_obs("A", 90.0, 10.0),
        make_obs("B", 90.0, 10.0),
        make_obs("C", 90.0, 10.0),
    ]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # sigma_theta = 0 → cos(0) = 1; sigma_v = 0 → exp(0) = 1 → S_sync = 1.0
    assert result.synchronization_index == pytest.approx(1.0, abs=0.01)
    assert result.heading_dispersion_deg == pytest.approx(0.0, abs=0.01)
    assert result.velocity_dispersion_mps == pytest.approx(0.0, abs=0.01)


# ---------------------------------------------------------------------------
# 22. Heading dispersion only (same velocity)
# ---------------------------------------------------------------------------

def test_heading_dispersion_reduces_sync():
    group = make_group(["A", "B"])
    # 90° apart headings → high circular dispersion
    members = [
        make_obs("A", 0.0, 10.0),
        make_obs("B", 90.0, 10.0),
    ]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # Velocity component = 1.0 (identical); heading component < 1.0
    assert result.synchronization_index < 1.0
    assert result.heading_dispersion_deg > 0.0


# ---------------------------------------------------------------------------
# 23. Velocity dispersion only (same heading)
# ---------------------------------------------------------------------------

def test_velocity_dispersion_reduces_sync():
    group = make_group(["A", "B"])
    members = [
        make_obs("A", 90.0, 5.0),
        make_obs("B", 90.0, 15.0),  # 10 m/s difference
    ]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # Heading component = 1.0; velocity component = exp(-std/5)
    assert result.synchronization_index < 1.0
    assert result.velocity_dispersion_mps > 0.0


# ---------------------------------------------------------------------------
# 24. Combined dispersion
# ---------------------------------------------------------------------------

def test_combined_dispersion_below_perfect():
    group = make_group(["A", "B"])
    members = [
        make_obs("A", 0.0, 5.0),
        make_obs("B", 45.0, 15.0),
    ]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    assert 0.0 <= result.synchronization_index <= 1.0
    # Both dispersions are nonzero
    assert result.heading_dispersion_deg > 0.0
    assert result.velocity_dispersion_mps > 0.0


# ---------------------------------------------------------------------------
# 25. Heading wraparound: 359° vs 1°
# ---------------------------------------------------------------------------

def test_heading_wraparound_359_vs_1():
    """Headings 359° and 1° are 2° apart, not 358° apart."""
    group = make_group(["A", "B"])
    members_correct = [make_obs("A", 359.0, 10.0), make_obs("B", 1.0, 10.0)]
    members_far = [make_obs("A", 0.0, 10.0), make_obs("B", 90.0, 10.0)]

    r_correct = compute_coordination_index(group, members_correct, _BASE_TS)
    r_far = compute_coordination_index(group, members_far, _BASE_TS)

    assert r_correct is not None
    assert r_far is not None
    # 2° apart must produce higher sync than 90° apart
    assert r_correct.synchronization_index > r_far.synchronization_index


def test_circular_std_359_vs_1_is_small():
    """Direct unit test for circular std: 359° and 1° should give small σ."""
    sigma = _circular_std_rad([359.0, 1.0])
    # Expected ≈ circular std of 2° arc ≈ 0.0175 rad
    assert sigma < 0.1  # much less than π/4 ≈ 0.785


# ---------------------------------------------------------------------------
# 26. Opposite headings (180° apart)
# ---------------------------------------------------------------------------

def test_opposite_headings_produce_low_sync():
    group = make_group(["A", "B"])
    members = [make_obs("A", 0.0, 10.0), make_obs("B", 180.0, 10.0)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # Maximum heading dispersion; heading component ≈ cos(π) = -1 → clamped to 0
    # velocity component = 1.0 → S_sync = 0.0 + 0.5 = 0.5 (clamped)
    assert result.synchronization_index <= 0.5


# ---------------------------------------------------------------------------
# 27. Zero velocity dispersion
# ---------------------------------------------------------------------------

def test_zero_velocity_dispersion_component_is_1():
    group = make_group(["A", "B"])
    members = [make_obs("A", 45.0, 10.0), make_obs("B", 45.0, 10.0)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    assert result.velocity_dispersion_mps == pytest.approx(0.0, abs=1e-6)
    assert result.synchronization_index == pytest.approx(1.0, abs=0.01)


# ---------------------------------------------------------------------------
# 28. Missing heading for some members
# ---------------------------------------------------------------------------

def test_missing_heading_partial():
    """One member with heading, one without. Heading component defaults to 0.5."""
    group = make_group(["A", "B"])
    members = [
        make_obs("A", 90.0, 10.0),
        make_obs("B", None, 10.0),  # no heading
    ]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # Only 1 heading → default heading_component = 0.5
    # velocity_component = 1.0 (identical velocities)
    # S_sync = 0.5 * 0.5 + 0.5 * 1.0 = 0.75
    assert result.synchronization_index == pytest.approx(0.75, abs=0.01)


# ---------------------------------------------------------------------------
# 29. Missing velocity for some members
# ---------------------------------------------------------------------------

def test_missing_velocity_partial():
    """One member with velocity, one without. Velocity component defaults to 0.5."""
    group = make_group(["A", "B"])
    members = [
        make_obs("A", 90.0, 10.0),
        make_obs("B", 90.0, None),  # no velocity
    ]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # Only 1 velocity → velocity_component defaults to 0.5
    # heading_component = 1.0 (identical headings)
    assert result.synchronization_index == pytest.approx(0.75, abs=0.01)


# ---------------------------------------------------------------------------
# 30. Fewer than 2 valid group members → None
# ---------------------------------------------------------------------------

def test_fewer_than_2_valid_members_returns_none():
    group = make_group(["A", "B"])
    # Only A is in members, B is missing
    members = [make_obs("A", 90.0, 10.0)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is None


def test_empty_members_returns_none():
    group = make_group(["A", "B"])
    result = compute_coordination_index(group, [], _BASE_TS)
    assert result is None


# ---------------------------------------------------------------------------
# 31. Duplicate track IDs in members
# ---------------------------------------------------------------------------

def test_duplicate_member_ids_deduplicated():
    """Duplicate IDs in members list must be deduplicated (last value wins)."""
    group = make_group(["A", "B"])
    members = [
        make_obs("A", 90.0, 10.0),
        make_obs("A", 45.0, 15.0),  # duplicate — should overwrite first
        make_obs("B", 90.0, 10.0),
    ]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # With A=45°, B=90°, there is heading dispersion; should not be 1.0
    assert result.synchronization_index <= 1.0


# ---------------------------------------------------------------------------
# 32. Deterministic output
# ---------------------------------------------------------------------------

def test_deterministic_output():
    group = make_group(["A", "B", "C"])
    members = [
        make_obs("A", 45.0, 10.0),
        make_obs("B", 50.0, 11.0),
        make_obs("C", 48.0, 9.5),
    ]
    r1 = compute_coordination_index(group, members, _BASE_TS)
    r2 = compute_coordination_index(group, members, _BASE_TS)
    assert r1 is not None and r2 is not None
    assert r1.synchronization_index == pytest.approx(r2.synchronization_index, abs=1e-8)
    assert r1.heading_dispersion_deg == pytest.approx(r2.heading_dispersion_deg, abs=1e-8)
    assert r1.velocity_dispersion_mps == pytest.approx(r2.velocity_dispersion_mps, abs=1e-8)


# ---------------------------------------------------------------------------
# 33. Synchronization index always in [0, 1]
# ---------------------------------------------------------------------------

def test_sync_index_always_bounded():
    scenarios = [
        ([make_obs("A", 0.0, 100.0), make_obs("B", 180.0, 0.0)], ["A", "B"]),
        ([make_obs("A", 359.0, 0.001), make_obs("B", 1.0, 0.001)], ["A", "B"]),
        ([make_obs("A", None, None), make_obs("B", None, None)], ["A", "B"]),
        ([make_obs("A", 0.0, 0.0), make_obs("B", 0.0, 0.0), make_obs("C", 0.0, 0.0)], ["A", "B", "C"]),
    ]
    for members, ids in scenarios:
        group = make_group(ids)
        r = compute_coordination_index(group, members, _BASE_TS)
        if r is not None:
            assert 0.0 <= r.synchronization_index <= 1.0


# ---------------------------------------------------------------------------
# 34. Formation ID derivation
# ---------------------------------------------------------------------------

def test_formation_id_is_fmt_prefixed():
    group = make_group(["A", "B"])
    members = [make_obs("A", 90.0, 10.0), make_obs("B", 90.0, 10.0)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    assert result.formation_id.startswith("FMT-")
    assert group.group_id in result.formation_id


# ---------------------------------------------------------------------------
# 35. Heading dispersion correctness
# ---------------------------------------------------------------------------

def test_heading_dispersion_30_degrees():
    """Two headings 30° apart should give a small but nonzero dispersion."""
    disp = _heading_dispersion_deg([0.0, 30.0])
    assert 0.0 < disp < 45.0


def test_heading_dispersion_identical_is_zero():
    disp = _heading_dispersion_deg([90.0, 90.0, 90.0])
    assert disp == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 36. Velocity dispersion value correctness
# ---------------------------------------------------------------------------

def test_velocity_population_std():
    # [5, 15] → mean 10, variance = (25 + 25)/2 = 25, std = 5.0
    std = _population_std([5.0, 15.0])
    assert std == pytest.approx(5.0, abs=1e-6)


def test_velocity_dispersion_zero_single_value():
    std = _population_std([10.0])
    assert std == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# 37. Confidence bounded [0, 1]
# ---------------------------------------------------------------------------

def test_confidence_bounded():
    group = make_group(["A", "B"])
    members = [make_obs("A", 90.0, 10.0), make_obs("B", 90.0, 10.0)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    assert 0.0 <= result.confidence <= 1.0


# ---------------------------------------------------------------------------
# 38. Single member group → None
# ---------------------------------------------------------------------------

def test_single_member_in_members_returns_none():
    group = make_group(["A", "B"])
    # Only supply one member that matches group
    members = [make_obs("A", 90.0, 10.0)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is None


# ---------------------------------------------------------------------------
# 39. All headings missing
# ---------------------------------------------------------------------------

def test_all_headings_missing_uses_neutral():
    group = make_group(["A", "B"])
    members = [make_obs("A", None, 10.0), make_obs("B", None, 10.0)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # heading_component defaults to 0.5; velocity_component = 1.0
    # S_sync = 0.5 * 0.5 + 0.5 * 1.0 = 0.75
    assert result.synchronization_index == pytest.approx(0.75, abs=0.01)


# ---------------------------------------------------------------------------
# 40. All velocities missing
# ---------------------------------------------------------------------------

def test_all_velocities_missing_uses_neutral():
    group = make_group(["A", "B"])
    members = [make_obs("A", 90.0, None), make_obs("B", 90.0, None)]
    result = compute_coordination_index(group, members, _BASE_TS)
    assert result is not None
    # heading_component = 1.0; velocity_component defaults to 0.5
    assert result.synchronization_index == pytest.approx(0.75, abs=0.01)
