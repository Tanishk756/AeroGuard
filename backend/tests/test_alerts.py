"""Integration tests for operational alert generation, rule triggers, deduplication, and resolution."""

from datetime import datetime, timedelta

import pytest
from sqlalchemy import func, select

from app.alerts.rules import (
    evaluate_data_quality_alert,
    evaluate_detection_alert,
    evaluate_geofence_breach_alerts,
    evaluate_track_lost_alert,
)
from app.alerts.service import AlertService
from app.fusion.quality import TrackQualityScore
from app.geofencing.engine import GeofenceEvaluationResult
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.audit import AuditEvent
from app.models.threat import ThreatLevel
from app.models.track import Track, TrackState
from app.threats.scoring import ThreatFactors


def test_track_detected_alert_on_confirmation():
    track = Track(
        id="t-al-1",
        state=TrackState.ACTIVE,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.85,
        classification="UAV",
    )

    # Transition NEW -> ACTIVE -> generates TRACK_DETECTED
    candidate = evaluate_detection_alert(track, previous_state=TrackState.NEW)
    assert candidate is not None
    assert candidate.type == AlertType.TRACK_DETECTED
    assert candidate.severity == AlertSeverity.LOW

    # Already ACTIVE -> ACTIVE -> does NOT trigger duplicate detection alert
    candidate_none = evaluate_detection_alert(track, previous_state=TrackState.ACTIVE)
    assert candidate_none is None


def test_geofence_breach_alert_generation():
    track = Track(
        id="t-al-breach",
        state=TrackState.ACTIVE,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.85,
        classification="UAV",
    )
    geo_res = [
        GeofenceEvaluationResult(
            geofence_id="geo-al-1",
            geofence_name="Restricted Airspace",
            inside=True,
            horizontal_inside=True,
            vertical_inside=True,
            altitude_indeterminate=False,
            distance_to_boundary_meters=0.0,
            reason="INSIDE_GEOFENCE",
        )
    ]
    factors_crit = ThreatFactors(
        score=90.0,
        level=ThreatLevel.CRITICAL,
        geofence_factor=1.0,
        kinematic_factor=0.8,
        classification_factor=0.85,
        track_quality=0.9,
        source_diversity=0.8,
        breached_geofences=["geo-al-1"],
        nearest_geofence_distance_meters=0.0,
        reason="Critical breach",
        evaluation_timestamp=datetime(2026, 8, 26, 12, 0, 0),
    )

    breach_cands = evaluate_geofence_breach_alerts(track, geo_res, threat_factors=factors_crit)
    assert len(breach_cands) == 1
    assert breach_cands[0].type == AlertType.GEOFENCE_BREACH
    assert breach_cands[0].severity == AlertSeverity.CRITICAL


def test_track_lost_alert_on_lifecycle_transition():
    track = Track(
        id="t-al-lost",
        state=TrackState.LOST,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.40,
    )
    lost_alert = evaluate_track_lost_alert(track)
    assert lost_alert.type == AlertType.TRACK_LOST
    assert lost_alert.severity == AlertSeverity.LOW


def test_data_quality_low_alert():
    track = Track(
        id="t-al-qual",
        state=TrackState.ACTIVE,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.20,
    )
    qual_low = TrackQualityScore(
        quality=0.22,
        confidence_component=0.20,
        diversity_component=0.30,
        continuity_component=0.20,
        residual_component=0.20,
        distinct_sensors=1,
        distinct_modalities=1,
    )
    cand = evaluate_data_quality_alert(track, qual_low)
    assert cand is not None
    assert cand.type == AlertType.DATA_QUALITY_LOW
    assert cand.severity == AlertSeverity.MEDIUM


def test_alert_deduplication_and_resolution(database):
    service = AlertService(database)
    track = Track(
        id="t-dedup-1",
        state=TrackState.ACTIVE,
        first_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        last_seen_at=datetime(2026, 8, 26, 12, 0, 0),
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.85,
    )
    database.add(track)
    database.commit()

    geo_res = [
        GeofenceEvaluationResult(
            geofence_id="geo-dedup-1",
            geofence_name="Zone A",
            inside=True,
            horizontal_inside=True,
            vertical_inside=True,
            altitude_indeterminate=False,
            distance_to_boundary_meters=0.0,
            reason="INSIDE_GEOFENCE",
        )
    ]
    candidates = evaluate_geofence_breach_alerts(track, geo_res)

    # 1. First submission -> creates 1 alert
    events1 = service.process_candidates(candidates)
    database.commit()
    assert len(events1) == 1

    alerts = database.scalars(select(Alert).where(Alert.track_id == track.id)).all()
    assert len(alerts) == 1
    assert alerts[0].status == AlertStatus.OPEN

    # 2. Duplicate submission for same condition -> does NOT create duplicate alert
    events2 = service.process_candidates(candidates)
    database.commit()
    assert len(events2) == 0

    alerts_after = database.scalars(select(Alert).where(Alert.track_id == track.id)).all()
    assert len(alerts_after) == 1

    # 3. Resolution when condition clears
    resolved_count = service.resolve_track_alerts(track.id)
    database.commit()
    assert resolved_count == 1

    alerts_resolved = database.scalars(select(Alert).where(Alert.track_id == track.id)).all()
    assert alerts_resolved[0].status == AlertStatus.RESOLVED
    assert alerts_resolved[0].resolved_at is not None

    # Verify no audit event was created for routine operational telemetry
    audit_count = database.scalar(select(func.count(AuditEvent.id)))
    assert audit_count == 0
