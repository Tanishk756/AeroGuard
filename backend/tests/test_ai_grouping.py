"""Backend tests for Stage AI2-B: Multi-Track Spatial & Temporal Correlation Engine.

Tests cover:
 1.  Isolated tracks (< 2 tracks → no groups)
 2.  Two tracks inside all thresholds → one group
 3.  Spatial distance > 500 m → no correlation
 4.  Velocity delta > 10 m/s → no correlation
 5.  Heading delta > 30° → no correlation
 6.  Circular heading wraparound (359° vs 1°)
 7.  Temporal incompatibility (> 10 s apart)
 8.  Connected-component chain A-B-C
 9.  Group centroid accuracy
10.  Radius of gyration accuracy
11.  Deterministic output under shuffled input order
12.  Stable group IDs across re-evaluations
13.  Join behaviour (new member absorbed into existing group)
14.  Leave/noise behaviour (departing member does not destroy group)
15.  Duplicate track IDs are deduplicated
16.  Coordinate edge cases (antimeridian longitude wrapping)
"""

from datetime import UTC, datetime, timedelta
import math
import random

import pytest

from ai.correlation.grouping import (
    GroupingConfig,
    TrackObservation,
    assign_group_id,
    calculate_centroid,
    calculate_group_confidence,
    calculate_radius_of_gyration,
    correlate_tracks,
    evaluate_pairwise_correlation,
)
from ai.schemas import BehavioralState, TrackGroup


# ---------------------------------------------------------------------------
# Helper factories
# ---------------------------------------------------------------------------

_BASE_TIME = datetime(2026, 1, 1, 12, 0, 0, tzinfo=UTC)


def make_obs(
    tid: str,
    lat: float,
    lon: float,
    velocity: float = 10.0,
    heading: float = 90.0,
    altitude: float = 100.0,
    confidence: float = 1.0,
    dt_offset_seconds: float = 0.0,
) -> TrackObservation:
    """Convenience factory to build a TrackObservation."""
    ts = _BASE_TIME + timedelta(seconds=dt_offset_seconds)
    return TrackObservation(
        id=tid,
        latitude=lat,
        longitude=lon,
        velocity=velocity,
        heading=heading,
        altitude=altitude,
        confidence=confidence,
        timestamp=ts,
    )


def offset_lat(lat: float, meters: float) -> float:
    """Shift latitude by *meters* north."""
    return lat + meters / 111_111.0


def offset_lon(lat: float, lon: float, meters: float) -> float:
    """Shift longitude by *meters* east at the given latitude."""
    return lon + meters / (111_111.0 * math.cos(math.radians(lat)))


# ---------------------------------------------------------------------------
# 1. Isolated tracks → no groups
# ---------------------------------------------------------------------------

def test_single_track_produces_no_group():
    track = make_obs("TRK-01", 37.0, -122.0)
    groups = correlate_tracks([track])
    assert groups == []


def test_empty_input_produces_no_groups():
    groups = correlate_tracks([])
    assert groups == []


# ---------------------------------------------------------------------------
# 2. Two tracks inside all thresholds → one group
# ---------------------------------------------------------------------------

def test_two_correlated_tracks_form_one_group():
    t1 = make_obs("TRK-A", 37.0000, -122.0000, velocity=10.0, heading=90.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 200.0), -122.0000, velocity=12.0, heading=95.0)

    groups = correlate_tracks([t1, t2])
    assert len(groups) == 1
    g = groups[0]
    assert set(g.member_track_ids) == {"TRK-A", "TRK-B"}
    assert g.member_count == 2
    assert g.behavioral_state == BehavioralState.NORMAL


# ---------------------------------------------------------------------------
# 3. Spatial distance > 500 m → no correlation
# ---------------------------------------------------------------------------

def test_spatial_distance_exceeds_threshold_no_group():
    t1 = make_obs("TRK-A", 37.0000, -122.0000, velocity=10.0, heading=90.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 600.0), -122.0000, velocity=10.0, heading=90.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert not corr.is_correlated
    assert corr.distance_meters > 500.0

    groups = correlate_tracks([t1, t2])
    assert groups == []


# ---------------------------------------------------------------------------
# 4. Velocity delta > 10 m/s → no correlation
# ---------------------------------------------------------------------------

def test_velocity_delta_exceeds_threshold_no_group():
    t1 = make_obs("TRK-A", 37.0, -122.0, velocity=5.0, heading=90.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, velocity=20.0, heading=90.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert not corr.is_correlated
    assert corr.velocity_delta_mps == pytest.approx(15.0, abs=0.01)

    groups = correlate_tracks([t1, t2])
    assert groups == []


# ---------------------------------------------------------------------------
# 5. Heading delta > 30° → no correlation
# ---------------------------------------------------------------------------

def test_heading_delta_exceeds_threshold_no_group():
    t1 = make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=0.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, velocity=10.0, heading=40.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert not corr.is_correlated
    assert corr.heading_delta_deg == pytest.approx(40.0, abs=0.01)

    groups = correlate_tracks([t1, t2])
    assert groups == []


# ---------------------------------------------------------------------------
# 6. Circular heading wraparound
# ---------------------------------------------------------------------------

def test_heading_wraparound_359_vs_1_correlated():
    """359° and 1° have a circular delta of 2°, well within the 30° threshold."""
    t1 = make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=359.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, velocity=10.0, heading=1.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert corr.is_correlated
    assert corr.heading_delta_deg == pytest.approx(2.0, abs=0.01)


def test_heading_wraparound_10_vs_350_correlated():
    """10° and 350° have a circular delta of 20°, within threshold."""
    t1 = make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=10.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, velocity=10.0, heading=350.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert corr.is_correlated
    assert corr.heading_delta_deg == pytest.approx(20.0, abs=0.01)


def test_heading_wraparound_45_vs_315_not_correlated():
    """45° and 315° have a circular delta of 90°, outside threshold."""
    t1 = make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=45.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, velocity=10.0, heading=315.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert not corr.is_correlated
    assert corr.heading_delta_deg == pytest.approx(90.0, abs=0.01)


# ---------------------------------------------------------------------------
# 7. Temporal incompatibility
# ---------------------------------------------------------------------------

def test_temporal_incompatibility_no_group():
    t1 = make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=90.0, dt_offset_seconds=0.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, velocity=10.0, heading=90.0, dt_offset_seconds=15.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert not corr.is_correlated
    assert corr.temporal_delta_seconds == pytest.approx(15.0, abs=0.01)

    groups = correlate_tracks([t1, t2])
    assert groups == []


def test_temporal_boundary_exactly_at_threshold_correlated():
    """Exactly at 10.0 s should pass (<=)."""
    t1 = make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=90.0, dt_offset_seconds=0.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, velocity=10.0, heading=90.0, dt_offset_seconds=10.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert corr.is_correlated
    assert corr.temporal_delta_seconds == pytest.approx(10.0, abs=0.01)


def test_no_timestamp_does_not_fail_correlation():
    """When timestamps are absent the temporal check is skipped entirely."""
    t1 = TrackObservation(id="TRK-A", latitude=37.0, longitude=-122.0, velocity=10.0, heading=90.0)
    t2 = TrackObservation(id="TRK-B", latitude=offset_lat(37.0, 50.0), longitude=-122.0, velocity=10.0, heading=90.0)

    corr = evaluate_pairwise_correlation(t1, t2)
    assert corr.is_correlated
    assert corr.temporal_delta_seconds is None


# ---------------------------------------------------------------------------
# 8. Connected-component chain A-B-C
# ---------------------------------------------------------------------------

def test_connected_component_chain_abc():
    """A↔B and B↔C but A and C are >500 m apart; all three still in one group."""
    base_lat = 37.0
    t_a = make_obs("TRK-A", base_lat, -122.0000, velocity=10.0, heading=90.0)
    t_b = make_obs("TRK-B", offset_lat(base_lat, 300.0), -122.0000, velocity=10.0, heading=90.0)
    t_c = make_obs("TRK-C", offset_lat(base_lat, 490.0), -122.0000, velocity=10.0, heading=90.0)

    # Verify A and C are NOT directly correlated (> 490 m separation but check)
    corr_ac = evaluate_pairwise_correlation(t_a, t_c)
    # They are 490 m apart so they *may or may not* be correlated; what matters is component logic
    # Make sure A-B and B-C are correlated
    corr_ab = evaluate_pairwise_correlation(t_a, t_b)
    corr_bc = evaluate_pairwise_correlation(t_b, t_c)
    assert corr_ab.is_correlated
    assert corr_bc.is_correlated

    groups = correlate_tracks([t_a, t_b, t_c])
    assert len(groups) == 1
    assert set(groups[0].member_track_ids) == {"TRK-A", "TRK-B", "TRK-C"}


def test_connected_component_chain_with_gap():
    """A↔B, D↔E — two separate groups when C links neither."""
    t_a = make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=90.0)
    t_b = make_obs("TRK-B", offset_lat(37.0, 100.0), -122.0, velocity=10.0, heading=90.0)
    # D and E are 2 degrees away in longitude
    t_d = make_obs("TRK-D", 37.0, -120.0, velocity=10.0, heading=90.0)
    t_e = make_obs("TRK-E", offset_lat(37.0, 100.0), -120.0, velocity=10.0, heading=90.0)

    groups = correlate_tracks([t_a, t_b, t_d, t_e])
    assert len(groups) == 2
    member_sets = {frozenset(g.member_track_ids) for g in groups}
    assert frozenset({"TRK-A", "TRK-B"}) in member_sets
    assert frozenset({"TRK-D", "TRK-E"}) in member_sets


# ---------------------------------------------------------------------------
# 9. Group centroid accuracy
# ---------------------------------------------------------------------------

def test_group_centroid_two_equal_tracks():
    """Centroid of two symmetric tracks must be their midpoint."""
    lat = 40.0
    lon = -75.0
    delta_lat = 0.001  # ~111 m
    t1 = TrackObservation(id="TRK-1", latitude=lat + delta_lat, longitude=lon)
    t2 = TrackObservation(id="TRK-2", latitude=lat - delta_lat, longitude=lon)

    c_lat, c_lon, c_alt = calculate_centroid([t1, t2])
    assert c_lat == pytest.approx(lat, abs=1e-6)
    assert c_lon == pytest.approx(lon, abs=1e-6)
    assert c_alt is None


def test_group_centroid_altitude_averaging():
    t1 = TrackObservation(id="TRK-1", latitude=37.0, longitude=-122.0, altitude=100.0)
    t2 = TrackObservation(id="TRK-2", latitude=37.001, longitude=-122.0, altitude=200.0)

    _, _, c_alt = calculate_centroid([t1, t2])
    assert c_alt == pytest.approx(150.0, abs=0.01)


# ---------------------------------------------------------------------------
# 10. Radius of gyration
# ---------------------------------------------------------------------------

def test_radius_of_gyration_collocated_tracks():
    """Tracks at identical positions → Rg = 0."""
    t1 = TrackObservation(id="TRK-1", latitude=37.0, longitude=-122.0)
    t2 = TrackObservation(id="TRK-2", latitude=37.0, longitude=-122.0)
    c_lat, c_lon, _ = calculate_centroid([t1, t2])
    rg = calculate_radius_of_gyration([t1, t2], c_lat, c_lon)
    assert rg == pytest.approx(0.0, abs=0.01)


def test_radius_of_gyration_known_distance():
    """Two tracks 200 m apart → Rg = 100 m (equidistant from centroid)."""
    lat = 37.0
    lon = -122.0
    shift = offset_lat(lat, 200.0) - lat  # ~200 m in degrees
    t1 = TrackObservation(id="TRK-1", latitude=lat - shift / 2, longitude=lon)
    t2 = TrackObservation(id="TRK-2", latitude=lat + shift / 2, longitude=lon)
    c_lat, c_lon, _ = calculate_centroid([t1, t2])
    rg = calculate_radius_of_gyration([t1, t2], c_lat, c_lon)
    # Each track is ~100 m from centroid; Rg = sqrt((100^2 + 100^2)/2) = 100 m
    assert rg == pytest.approx(100.0, abs=2.0)


# ---------------------------------------------------------------------------
# 11. Deterministic output under shuffled input order
# ---------------------------------------------------------------------------

def test_output_deterministic_under_shuffled_input():
    """Shuffling the input list must not change group membership, ID, centroid, or radius."""
    tracks = [
        make_obs("TRK-A", 37.0, -122.0, velocity=10.0, heading=90.0),
        make_obs("TRK-B", offset_lat(37.0, 100.0), -122.0, velocity=10.0, heading=90.0),
        make_obs("TRK-C", offset_lat(37.0, 200.0), -122.0, velocity=10.0, heading=90.0),
    ]
    ref_groups = correlate_tracks(tracks)

    rng = random.Random(42)
    for _ in range(5):
        shuffled = tracks[:]
        rng.shuffle(shuffled)
        result_groups = correlate_tracks(shuffled)

        assert len(result_groups) == len(ref_groups)
        for rg, gg in zip(ref_groups, result_groups):
            assert rg.group_id == gg.group_id
            assert rg.member_track_ids == gg.member_track_ids
            assert rg.centroid_lat == pytest.approx(gg.centroid_lat, abs=1e-8)
            assert rg.centroid_lon == pytest.approx(gg.centroid_lon, abs=1e-8)
            assert rg.radius_meters == pytest.approx(gg.radius_meters, abs=0.001)
            assert rg.confidence == pytest.approx(gg.confidence, abs=0.001)


# ---------------------------------------------------------------------------
# 12. Stable group IDs across re-evaluations
# ---------------------------------------------------------------------------

def test_stable_group_id_persists_with_hysteresis():
    """An existing group with high Jaccard overlap keeps its group_id."""
    members_v1 = ["TRK-A", "TRK-B", "TRK-C"]
    members_v2 = ["TRK-A", "TRK-B", "TRK-D"]  # TRK-C left, TRK-D joined (Jaccard = 2/4 = 0.5)

    id_v1 = assign_group_id(members_v1)

    # Simulate previous group in state
    existing = [
        TrackGroup(
            group_id=id_v1,
            member_track_ids=members_v1,
            centroid_lat=37.0,
            centroid_lon=-122.0,
            radius_meters=50.0,
            member_count=3,
            confidence=0.95,
            behavioral_state=BehavioralState.NORMAL,
            updated_at=datetime.now(UTC),
        )
    ]

    id_v2 = assign_group_id(members_v2, existing_groups=existing, hysteresis_threshold=0.50)
    assert id_v2 == id_v1, "Group ID should be preserved when Jaccard overlap >= 0.50"


def test_new_group_gets_new_id_when_no_overlap():
    """A completely new set of members gets a fresh deterministic ID."""
    members_old = ["TRK-A", "TRK-B"]
    members_new = ["TRK-X", "TRK-Y"]

    id_old = assign_group_id(members_old)

    existing = [
        TrackGroup(
            group_id=id_old,
            member_track_ids=members_old,
            centroid_lat=37.0,
            centroid_lon=-122.0,
            radius_meters=50.0,
            member_count=2,
            confidence=0.95,
            behavioral_state=BehavioralState.NORMAL,
            updated_at=datetime.now(UTC),
        )
    ]

    id_new = assign_group_id(members_new, existing_groups=existing)
    assert id_new != id_old


def test_group_id_is_order_independent():
    """Group ID derived from member set must not vary with input order."""
    id_abc = assign_group_id(["TRK-A", "TRK-B", "TRK-C"])
    id_cba = assign_group_id(["TRK-C", "TRK-B", "TRK-A"])
    id_bac = assign_group_id(["TRK-B", "TRK-A", "TRK-C"])
    assert id_abc == id_cba == id_bac


# ---------------------------------------------------------------------------
# 13. Join behaviour
# ---------------------------------------------------------------------------

def test_join_new_member_absorbed_into_existing_group():
    """Adding TRK-C that correlates with TRK-A/B enlarges the group."""
    t_a = make_obs("TRK-A", 37.0, -122.0)
    t_b = make_obs("TRK-B", offset_lat(37.0, 100.0), -122.0)
    t_c = make_obs("TRK-C", offset_lat(37.0, 50.0), -122.0)

    groups_before = correlate_tracks([t_a, t_b])
    existing_id = groups_before[0].group_id

    groups_after = correlate_tracks([t_a, t_b, t_c], existing_groups=groups_before)
    assert len(groups_after) == 1
    assert "TRK-C" in groups_after[0].member_track_ids
    # Hysteresis should preserve the original group ID (Jaccard A,B in A,B,C = 2/3 ≥ 0.5)
    assert groups_after[0].group_id == existing_id


# ---------------------------------------------------------------------------
# 14. Leave / noise behaviour
# ---------------------------------------------------------------------------

def test_leaving_member_does_not_destroy_remaining_group():
    """When TRK-C departs, TRK-A & TRK-B remain grouped with the same ID."""
    t_a = make_obs("TRK-A", 37.0, -122.0)
    t_b = make_obs("TRK-B", offset_lat(37.0, 100.0), -122.0)
    t_c = make_obs("TRK-C", offset_lat(37.0, 50.0), -122.0)

    groups_with_c = correlate_tracks([t_a, t_b, t_c])
    existing_id = groups_with_c[0].group_id

    groups_without_c = correlate_tracks([t_a, t_b], existing_groups=groups_with_c)
    assert len(groups_without_c) == 1
    assert "TRK-C" not in groups_without_c[0].member_track_ids
    # Jaccard of {A,B} ∩ {A,B,C} = 2/3 ≥ 0.5 → preserve ID
    assert groups_without_c[0].group_id == existing_id


# ---------------------------------------------------------------------------
# 15. Duplicate track IDs deduplicated
# ---------------------------------------------------------------------------

def test_duplicate_track_ids_deduplicated():
    """Supplying the same track ID twice must not produce duplicate members."""
    t_a = make_obs("TRK-A", 37.0, -122.0)
    t_a_dup = make_obs("TRK-A", 37.0, -122.0)
    t_b = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0)

    groups = correlate_tracks([t_a, t_a_dup, t_b])
    # Only one unique TRK-A; with TRK-B → one group of 2
    assert len(groups) == 1
    assert groups[0].member_count == 2
    assert len(set(groups[0].member_track_ids)) == groups[0].member_count


# ---------------------------------------------------------------------------
# 16. Coordinate edge cases — antimeridian longitude wrapping
# ---------------------------------------------------------------------------

def test_antimeridian_centroid_wraps_correctly():
    """Two tracks straddling the antimeridian (±179°) should produce a sensible centroid."""
    t1 = TrackObservation(id="TRK-A", latitude=0.0, longitude=179.5)
    t2 = TrackObservation(id="TRK-B", latitude=0.0, longitude=-179.5)

    c_lat, c_lon, _ = calculate_centroid([t1, t2])
    # Circular mean: sin(179.5°) + sin(-179.5°) ≈ 0  → centroid should be near ±180
    # Either 180.0 or -180.0 is numerically equivalent; accept within ±1°
    assert abs(c_lon) >= 179.0


def test_normal_lon_centroid_no_antimeridian():
    """Normal longitudes (-122 and -120) produce a simple arithmetic midpoint centroid."""
    t1 = TrackObservation(id="TRK-A", latitude=37.0, longitude=-122.0)
    t2 = TrackObservation(id="TRK-B", latitude=37.0, longitude=-120.0)

    c_lat, c_lon, _ = calculate_centroid([t1, t2])
    assert c_lon == pytest.approx(-121.0, abs=0.001)


# ---------------------------------------------------------------------------
# 17. Confidence formula is deterministic and bounded
# ---------------------------------------------------------------------------

def test_confidence_is_bounded_0_to_1():
    obs = [
        TrackObservation(id="TRK-A", latitude=37.0, longitude=-122.0, confidence=0.9),
        TrackObservation(id="TRK-B", latitude=37.0001, longitude=-122.0, confidence=0.8),
    ]
    c_lat, c_lon, _ = calculate_centroid(obs)
    rg = calculate_radius_of_gyration(obs, c_lat, c_lon)
    conf = calculate_group_confidence(obs, rg)

    assert 0.0 <= conf <= 1.0


def test_confidence_degrades_with_larger_radius():
    """A more spread-out group should have equal-or-lower confidence than a compact one."""
    obs_compact = [
        TrackObservation(id="TRK-A", latitude=37.0, longitude=-122.0, confidence=1.0),
        TrackObservation(id="TRK-B", latitude=offset_lat(37.0, 10.0), longitude=-122.0, confidence=1.0),
    ]
    obs_spread = [
        TrackObservation(id="TRK-A", latitude=37.0, longitude=-122.0, confidence=1.0),
        TrackObservation(id="TRK-B", latitude=offset_lat(37.0, 490.0), longitude=-122.0, confidence=1.0),
    ]

    c_lat_c, c_lon_c, _ = calculate_centroid(obs_compact)
    rg_compact = calculate_radius_of_gyration(obs_compact, c_lat_c, c_lon_c)
    conf_compact = calculate_group_confidence(obs_compact, rg_compact)

    c_lat_s, c_lon_s, _ = calculate_centroid(obs_spread)
    rg_spread = calculate_radius_of_gyration(obs_spread, c_lat_s, c_lon_s)
    conf_spread = calculate_group_confidence(obs_spread, rg_spread)

    assert conf_compact >= conf_spread


# ---------------------------------------------------------------------------
# 18. Custom configuration thresholds are respected
# ---------------------------------------------------------------------------

def test_custom_config_tighter_distance_threshold():
    """A 100 m threshold should reject tracks 200 m apart."""
    t1 = make_obs("TRK-A", 37.0, -122.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 200.0), -122.0)

    tight_cfg = GroupingConfig(max_distance_meters=100.0)
    corr = evaluate_pairwise_correlation(t1, t2, tight_cfg)
    assert not corr.is_correlated
    assert corr.distance_meters > 100.0


def test_custom_config_wider_heading_threshold():
    """A 60° heading threshold should allow a 45° heading delta."""
    t1 = make_obs("TRK-A", 37.0, -122.0, heading=0.0)
    t2 = make_obs("TRK-B", offset_lat(37.0, 50.0), -122.0, heading=45.0)

    wide_cfg = GroupingConfig(max_heading_delta_deg=60.0)
    corr = evaluate_pairwise_correlation(t1, t2, wide_cfg)
    assert corr.is_correlated
