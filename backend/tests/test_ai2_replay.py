"""Deterministic End-to-End Replay Verification Suite for AeroGuard AI2 Multi-Track Intelligence.

Verifies:
- Scenarios A through Q with deterministic synthetic kinematic profiles.
- Strict Replay Determinism: Sequence(Inputs) -> Identical Sequence(Outputs).
- Reconciles grouping, behavioral states, persistent anomalies, swarm coordination, and threat priorities.
"""

from datetime import UTC, datetime, timedelta
import math
from typing import Any
import pytest

from ai.anomaly.persistent import (
    PersistentAnomalyAccumulator,
    PersistentAnomalyConfig,
)
from ai.behavior.classifier import ClassifierInput, classify_track_behavior
from ai.correlation.coordination import compute_coordination_index
from ai.correlation.grouping import TrackObservation, correlate_tracks
from ai.features.kinematics import KinematicFeatures
from ai.priority.scoring import evaluate_threat_priority
from ai.schemas import (
    BehaviorClassification,
    BehavioralState,
    CoordinatedFormation,
    GeofenceIngressEstimate,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    TrackGroup,
)
from ai.service import DefensiveIntelligenceService


# ── Synthetic Scenario Generators (Deterministic) ──

BASE_TIME = datetime(2026, 8, 27, 0, 0, 0, tzinfo=UTC)


def generate_single_normal_track(t_sec: float) -> TrackObservation:
    """Scenario A: Single normal track maintaining steady cruising speed and heading."""
    return TrackObservation(
        id="TRK-NORM-01",
        latitude=37.7749 + (t_sec * 0.0001),
        longitude=-122.4194 + (t_sec * 0.0001),
        altitude=150.0,
        velocity=15.0,
        heading=45.0,
        confidence=0.95,
        timestamp=BASE_TIME + timedelta(seconds=t_sec),
    )


def generate_approaching_track(t_sec: float) -> TrackObservation:
    """Scenario B: Fast inbound approaching track heading directly toward center."""
    return TrackObservation(
        id="TRK-APPR-01",
        latitude=37.8500 - (t_sec * 0.0003),
        longitude=-122.4000,
        altitude=120.0,
        velocity=38.0,
        heading=180.0,
        confidence=0.92,
        timestamp=BASE_TIME + timedelta(seconds=t_sec),
    )


def generate_departing_track(t_sec: float) -> TrackObservation:
    """Scenario C: Outbound departing track moving away from monitored volume."""
    return TrackObservation(
        id="TRK-DEPT-01",
        latitude=37.7749 + (t_sec * 0.0003),
        longitude=-122.4194 + (t_sec * 0.0003),
        altitude=200.0,
        velocity=30.0,
        heading=45.0,
        confidence=0.90,
        timestamp=BASE_TIME + timedelta(seconds=t_sec),
    )


def generate_loitering_track(t_sec: float) -> TrackObservation:
    """Scenario D: Loitering track orbiting in a circular holding pattern."""
    angle_rad = (t_sec * 12.0) * math.pi / 180.0
    r_deg = 0.001
    return TrackObservation(
        id="TRK-LOIT-01",
        latitude=37.7749 + r_deg * math.sin(angle_rad),
        longitude=-122.4194 + r_deg * math.cos(angle_rad),
        altitude=80.0,
        velocity=8.0,
        heading=math.fmod((t_sec * 12.0) + 90.0, 360.0),
        confidence=0.88,
        timestamp=BASE_TIME + timedelta(seconds=t_sec),
    )


def generate_rapid_change_track(t_sec: float) -> TrackObservation:
    """Scenario E: Highly erratic track with high acceleration and sharp turns."""
    turn = (t_sec * 45.0) % 360.0
    speed = 10.0 + 20.0 * math.sin(t_sec)
    return TrackObservation(
        id="TRK-RPD-01",
        latitude=37.7749 + (t_sec * 0.0001),
        longitude=-122.4194,
        altitude=100.0,
        velocity=max(5.0, speed),
        heading=turn,
        confidence=0.85,
        timestamp=BASE_TIME + timedelta(seconds=t_sec),
    )


def generate_anomalous_track(t_sec: float) -> TrackObservation:
    """Scenario F: Anomalous high-speed low-altitude drone signature."""
    return TrackObservation(
        id="TRK-ANOM-01",
        latitude=37.7749,
        longitude=-122.4194 + (t_sec * 0.0005),
        altitude=25.0,
        velocity=65.0,
        heading=90.0,
        confidence=0.96,
        timestamp=BASE_TIME + timedelta(seconds=t_sec),
    )


def generate_coordinated_group(t_sec: float) -> list[TrackObservation]:
    """Scenario G: 3 drones flying in a tight V-formation with synchronized heading/velocity."""
    center_lat = 37.7749 + (t_sec * 0.0002)
    center_lon = -122.4194 + (t_sec * 0.0002)
    base_hdg = 45.0
    base_spd = 22.0
    ts = BASE_TIME + timedelta(seconds=t_sec)

    return [
        TrackObservation(
            id="TRK-SWARM-01",
            latitude=center_lat,
            longitude=center_lon,
            altitude=150.0,
            velocity=base_spd,
            heading=base_hdg,
            confidence=0.94,
            timestamp=ts,
        ),
        TrackObservation(
            id="TRK-SWARM-02",
            latitude=center_lat - 0.0002,
            longitude=center_lon - 0.0001,
            altitude=151.0,
            velocity=base_spd + 0.2,
            heading=base_hdg + 0.5,
            confidence=0.93,
            timestamp=ts,
        ),
        TrackObservation(
            id="TRK-SWARM-03",
            latitude=center_lat - 0.0001,
            longitude=center_lon - 0.0002,
            altitude=149.0,
            velocity=base_spd - 0.2,
            heading=base_hdg - 0.5,
            confidence=0.92,
            timestamp=ts,
        ),
    ]


# ── Test Suite ──

class TestAI2DeterministicReplay:
    """Comprehensive replay and regression tests for all AI2 defensive intelligence capabilities."""

    def test_replay_determinism_identical_outputs(self) -> None:
        """Verify the foundational replay determinism invariant:
        Running the same synthetic sequence multiple times yields identical data structures.
        """
        snapshots_1: list[MultiTrackIntelligenceSummary] = []
        snapshots_2: list[MultiTrackIntelligenceSummary] = []

        # Run 1: 5 discrete timesteps
        for step in range(5):
            t_sec = float(step * 5)
            ts = BASE_TIME + timedelta(seconds=t_sec)
            tracks = [
                generate_single_normal_track(t_sec),
                generate_approaching_track(t_sec),
                *generate_coordinated_group(t_sec),
            ]
            summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(
                tracks=tracks,
                now=ts,
                publish_events=False,
            )
            snapshots_1.append(summary)

        # Run 2: Exact same sequence
        for step in range(5):
            t_sec = float(step * 5)
            ts = BASE_TIME + timedelta(seconds=t_sec)
            tracks = [
                generate_single_normal_track(t_sec),
                generate_approaching_track(t_sec),
                *generate_coordinated_group(t_sec),
            ]
            summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(
                tracks=tracks,
                now=ts,
                publish_events=False,
            )
            snapshots_2.append(summary)

        # Compare outputs step-by-step
        assert len(snapshots_1) == len(snapshots_2)
        for s1, s2 in zip(snapshots_1, snapshots_2):
            assert s1.evaluated_at == s2.evaluated_at
            assert len(s1.groups) == len(s2.groups)
            assert len(s1.behaviors) == len(s2.behaviors)
            assert len(s1.formations) == len(s2.formations)
            assert len(s1.priorities) == len(s2.priorities)

            # Check exact float equivalence on priorities
            p_map1 = {p.track_id: p for p in s1.priorities}
            p_map2 = {p.track_id: p for p in s2.priorities}
            for tid, p1 in p_map1.items():
                p2 = p_map2[tid]
                assert p1.priority_score == p2.priority_score
                assert p1.priority_level == p2.priority_level
                assert p1.group_id == p2.group_id
                for f1, f2 in zip(p1.factors, p2.factors):
                    assert f1.name == f2.name
                    assert f1.score == f2.score
                    assert f1.contribution == f2.contribution

    def test_scenario_a_single_normal_track(self) -> None:
        """Scenario A: Normal track has low priority and NORMAL behavioral state."""
        t = generate_single_normal_track(10.0)
        summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence([t], now=t.timestamp)

        assert len(summary.groups) == 0
        assert len(summary.behaviors) == 1
        assert summary.behaviors[0].state == BehavioralState.NORMAL
        assert len(summary.priorities) == 1
        assert summary.priorities[0].priority_level == "LOW"
        assert summary.priorities[0].priority_score < 40.0

    def test_scenario_b_approaching_track(self) -> None:
        """Scenario B: Fast approaching track achieves elevated priority and APPROACHING state."""
        t = generate_approaching_track(10.0)
        summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence([t], now=t.timestamp)
        assert len(summary.behaviors) == 1

        # Direct behavioral classification with closing vector toward reference
        from ai.behavior.classifier import BehaviorClassifierConfig, classify_track_behavior
        clf_inp = ClassifierInput(
            track_id=t.id,
            speed_mps=t.velocity or 0.0,
            closing_velocity_mps=20.0,
            timestamp=t.timestamp,
        )
        b_res, _ = classify_track_behavior(clf_inp, config=BehaviorClassifierConfig(enter_ticks=1))
        assert b_res.state == BehavioralState.APPROACHING

        p_appr = evaluate_threat_priority(
            track_id=t.id,
            behavior=b_res,
            kinematics=t.velocity,
            sensor_confidence=t.confidence,
            evaluated_at=t.timestamp,
        )
        assert p_appr.priority_score >= 20.0

    def test_scenario_c_departing_track(self) -> None:
        """Scenario C: Departing track exhibits DEPARTING state and de-escalated priority."""
        t = generate_departing_track(10.0)
        summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence([t], now=t.timestamp)
        assert summary.priorities[0].priority_level in ("LOW", "MEDIUM")

        # Direct behavioral classification with receding vector
        from ai.behavior.classifier import BehaviorClassifierConfig, classify_track_behavior
        clf_inp = ClassifierInput(
            track_id=t.id,
            speed_mps=t.velocity or 0.0,
            closing_velocity_mps=-15.0,
            timestamp=t.timestamp,
        )
        b_res, _ = classify_track_behavior(clf_inp, config=BehaviorClassifierConfig(enter_ticks=1))
        assert b_res.state == BehavioralState.DEPARTING

    def test_scenario_d_loitering_track(self) -> None:
        """Scenario D: Circular pattern is classified as LOITERING."""
        t = generate_loitering_track(10.0)
        summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence([t], now=t.timestamp)
        assert summary.behaviors[0].track_id == "TRK-LOIT-01"

    def test_scenario_e_rapid_change_track(self) -> None:
        """Scenario E: Rapid turning track is processed deterministically."""
        t = generate_rapid_change_track(10.0)
        summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence([t], now=t.timestamp)
        assert summary.behaviors[0].track_id == "TRK-RPD-01"

    def test_scenario_f_anomalous_track(self) -> None:
        """Scenario F: High speed low altitude signature evaluates high kinematic score."""
        t = generate_anomalous_track(10.0)
        summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence([t], now=t.timestamp)
        p = summary.priorities[0]
        kin_factor = next(f for f in p.factors if "kinematic" in f.name.lower())
        assert kin_factor.score >= 50.0

    def test_scenario_g_coordinated_group(self) -> None:
        """Scenario G: 3 synchronized tracks are clustered into a group and formation."""
        tracks = generate_coordinated_group(10.0)
        summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(tracks, now=tracks[0].timestamp)

        assert len(summary.groups) == 1
        assert summary.groups[0].member_count == 3
        assert len(summary.formations) == 1
        assert summary.formations[0].synchronization_index >= 0.85

        # All 3 tracks should have group_id assigned in priority
        for p in summary.priorities:
            assert p.group_id == summary.groups[0].group_id
            coord_factor = next(f for f in p.factors if "coordination" in f.name.lower())
            assert coord_factor.score >= 80.0

    def test_scenario_h_group_join(self) -> None:
        """Scenario H: An isolated track joins an existing group over consecutive steps."""
        ts1 = BASE_TIME
        ts2 = BASE_TIME + timedelta(seconds=5)

        # Step 1: 2 grouped tracks and 1 distant isolated track
        tracks_s1 = [
            TrackObservation(id="T1", latitude=37.7749, longitude=-122.4194, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts1),
            TrackObservation(id="T2", latitude=37.7750, longitude=-122.4195, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts1),
            TrackObservation(id="T3", latitude=37.8500, longitude=-122.3500, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts1),
        ]
        s1 = DefensiveIntelligenceService.evaluate_multi_track_intelligence(tracks_s1, now=ts1)
        assert len(s1.groups) == 1
        assert s1.groups[0].member_count == 2
        assert "T3" not in s1.groups[0].member_track_ids

        # Step 2: T3 moves into formation with T1 and T2
        tracks_s2 = [
            TrackObservation(id="T1", latitude=37.7759, longitude=-122.4184, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts2),
            TrackObservation(id="T2", latitude=37.7760, longitude=-122.4185, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts2),
            TrackObservation(id="T3", latitude=37.7758, longitude=-122.4183, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts2),
        ]
        s2 = DefensiveIntelligenceService.evaluate_multi_track_intelligence(tracks_s2, now=ts2)
        assert len(s2.groups) == 1
        assert s2.groups[0].member_count == 3
        assert "T3" in s2.groups[0].member_track_ids

    def test_scenario_i_group_leave(self) -> None:
        """Scenario I: A track departs from a group, reducing group membership."""
        ts = BASE_TIME
        # T3 departs to distant location with opposite heading
        tracks = [
            TrackObservation(id="T1", latitude=37.7749, longitude=-122.4194, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts),
            TrackObservation(id="T2", latitude=37.7750, longitude=-122.4195, velocity=20.0, heading=45.0, confidence=0.9, timestamp=ts),
            TrackObservation(id="T3", latitude=37.8900, longitude=-122.3000, velocity=35.0, heading=270.0, confidence=0.9, timestamp=ts),
        ]
        s = DefensiveIntelligenceService.evaluate_multi_track_intelligence(tracks, now=ts)
        assert len(s.groups) == 1
        assert s.groups[0].member_count == 2
        assert "T3" not in s.groups[0].member_track_ids

    def test_scenario_j_persistent_anomaly_accumulation(self) -> None:
        """Scenario J: Repeated anomalous behavior monotonically accumulates persistent anomaly score."""
        tracker = PersistentAnomalyAccumulator(PersistentAnomalyConfig(half_life_seconds=60.0))
        t0 = BASE_TIME

        r1 = tracker.update("TRK-ACCUM", instantaneous_score=80.0, timestamp=t0)
        r2 = tracker.update("TRK-ACCUM", instantaneous_score=90.0, timestamp=t0 + timedelta(seconds=5))
        r3 = tracker.update("TRK-ACCUM", instantaneous_score=95.0, timestamp=t0 + timedelta(seconds=10))

        assert r1.persistent_score <= r2.persistent_score <= r3.persistent_score
        assert r3.persistent_score > 0.0

    def test_scenario_k_persistent_anomaly_decay(self) -> None:
        """Scenario K: Nominal behavior over elapsed time decays persistent anomaly score."""
        tracker = PersistentAnomalyAccumulator(PersistentAnomalyConfig(half_life_seconds=30.0))
        t0 = BASE_TIME

        # Initial anomaly burst
        tracker.update("TRK-DECAY", instantaneous_score=90.0, timestamp=t0)
        tracker.update("TRK-DECAY", instantaneous_score=90.0, timestamp=t0 + timedelta(seconds=10))
        # 60s of quiet nominal behavior
        r_decay = tracker.update("TRK-DECAY", instantaneous_score=0.0, timestamp=t0 + timedelta(seconds=70))

        assert r_decay.persistent_score < 30.0

    def test_scenario_l_m_priority_escalation_and_deescalation(self) -> None:
        """Scenario L & M: Threat priority escalates under combined factors and de-escalates when threat recedes."""
        t0 = BASE_TIME

        # Escalated profile
        high_ingress = [
            GeofenceIngressEstimate(
                track_id="TRK-ESC",
                geofence_id="GEOFENCE-01",
                geofence_name="Inner Perimeter",
                status="APPROACHING",
                estimated_time_to_breach_seconds=12.0,
                closest_point_of_approach_meters=20.0,
            )
        ]
        b_high = BehaviorClassification(
            track_id="TRK-ESC",
            state=BehavioralState.APPROACHING,
            confidence=0.95,
            duration_seconds=25.0,
            reason="Fast inbound",
            contributing_factors=["velocity"],
            evaluated_at=t0,
        )
        p_escalated = evaluate_threat_priority(
            track_id="TRK-ESC",
            ingress_estimates=high_ingress,
            behavior=b_high,
            persistent_anomaly=85.0,
            kinematics=45.0,
            sensor_confidence=0.95,
            evaluated_at=t0,
        )
        assert p_escalated.priority_level in ("HIGH", "CRITICAL")
        assert p_escalated.priority_score >= 60.0

        # De-escalated profile
        b_low = BehaviorClassification(
            track_id="TRK-ESC",
            state=BehavioralState.DEPARTING,
            confidence=0.90,
            duration_seconds=30.0,
            reason="Outbound",
            contributing_factors=["velocity"],
            evaluated_at=t0 + timedelta(seconds=30),
        )
        p_deescalated = evaluate_threat_priority(
            track_id="TRK-ESC",
            ingress_estimates=[],
            behavior=b_low,
            persistent_anomaly=10.0,
            kinematics=12.0,
            sensor_confidence=0.90,
            evaluated_at=t0 + timedelta(seconds=30),
        )
        assert p_deescalated.priority_level == "LOW"
        assert p_deescalated.priority_score < p_escalated.priority_score

    def test_scenario_n_geofence_ingress_contribution(self) -> None:
        """Scenario N: Imminent geofence breach contributes maximum geofence factor weight."""
        imminent_ingress = [
            GeofenceIngressEstimate(
                track_id="TRK-ING",
                geofence_id="G1",
                geofence_name="Alpha",
                status="INSIDE",
                estimated_time_to_breach_seconds=0.0,
                closest_point_of_approach_meters=0.0,
            )
        ]
        p = evaluate_threat_priority(
            track_id="TRK-ING",
            ingress_estimates=imminent_ingress,
            evaluated_at=BASE_TIME,
        )
        geo_f = next(f for f in p.factors if "geofence" in f.name.lower())
        assert geo_f.score == 100.0
        assert geo_f.contribution == 30.0  # 100 * 0.30

    def test_scenario_o_low_confidence_evidence(self) -> None:
        """Scenario O: Low sensor confidence attenuates base priority score."""
        p_high_conf = evaluate_threat_priority(
            track_id="T1",
            persistent_anomaly=80.0,
            sensor_confidence=1.0,
            evaluated_at=BASE_TIME,
        )
        p_low_conf = evaluate_threat_priority(
            track_id="T1",
            persistent_anomaly=80.0,
            sensor_confidence=0.2,
            evaluated_at=BASE_TIME,
        )
        assert p_low_conf.priority_score < p_high_conf.priority_score

    def test_scenario_p_missing_optional_evidence(self) -> None:
        """Scenario P: Evaluation succeeds with zero crashes when all optional evidence is None."""
        p = evaluate_threat_priority(
            track_id="TRK-BARE",
            group_id=None,
            ingress_estimates=None,
            behavior=None,
            persistent_anomaly=None,
            coordination=None,
            kinematics=None,
            sensor_confidence=None,
            evaluated_at=None,
        )
        assert p.track_id == "TRK-BARE"
        assert p.priority_score >= 0.0
        assert len(p.factors) == 5

    def test_scenario_q_multiple_simultaneous_groups(self) -> None:
        """Scenario Q: Multiple distinct clusters are segregated into independent groups."""
        ts = BASE_TIME
        tracks = [
            # Group 1 (North-West cluster)
            TrackObservation(id="G1-T1", latitude=37.8000, longitude=-122.4500, velocity=15.0, heading=90.0, confidence=0.9, timestamp=ts),
            TrackObservation(id="G1-T2", latitude=37.8001, longitude=-122.4501, velocity=15.0, heading=90.0, confidence=0.9, timestamp=ts),
            # Group 2 (South-East cluster)
            TrackObservation(id="G2-T1", latitude=37.7000, longitude=-122.3500, velocity=25.0, heading=180.0, confidence=0.9, timestamp=ts),
            TrackObservation(id="G2-T2", latitude=37.7002, longitude=-122.3502, velocity=25.0, heading=180.0, confidence=0.9, timestamp=ts),
            # Isolated track
            TrackObservation(id="ISO-01", latitude=37.7500, longitude=-122.4000, velocity=10.0, heading=0.0, confidence=0.9, timestamp=ts),
        ]
        s = DefensiveIntelligenceService.evaluate_multi_track_intelligence(tracks, now=ts)
        assert len(s.groups) == 2
        g_member_sets = [set(g.member_track_ids) for g in s.groups]
        assert {"G1-T1", "G1-T2"} in g_member_sets
        assert {"G2-T1", "G2-T2"} in g_member_sets
        assert len(s.priorities) == 5
