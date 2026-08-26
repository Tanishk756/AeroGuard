"""Operational alert rule definitions and trigger evaluation."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from app.models.alert import AlertSeverity, AlertType
from app.models.threat import ThreatLevel
from app.models.track import Track, TrackState

if TYPE_CHECKING:
    from app.fusion.quality import TrackQualityScore
    from app.geofencing.engine import GeofenceEvaluationResult
    from app.threats.scoring import ThreatFactors


@dataclass(frozen=True)
class AlertCandidate:
    type: AlertType
    severity: AlertSeverity
    reason: str
    track_id: str | None = None
    sensor_id: str | None = None
    metadata_json: dict = field(default_factory=dict)


def evaluate_detection_alert(
    track: Track,
    previous_state: TrackState | None,
    threat_factors: "ThreatFactors | None" = None,
) -> AlertCandidate | None:
    """Trigger TRACK_DETECTED alert when a tentative track is confirmed to ACTIVE."""
    if previous_state == TrackState.NEW and track.state == TrackState.ACTIVE:
        severity = AlertSeverity.LOW
        if threat_factors and threat_factors.level in (ThreatLevel.HIGH, ThreatLevel.CRITICAL):
            severity = AlertSeverity.MEDIUM

        return AlertCandidate(
            type=AlertType.TRACK_DETECTED,
            severity=severity,
            track_id=track.id,
            reason=f"Track {track.id} confirmed ACTIVE ({track.classification or 'UNKNOWN'})",
            metadata_json={"track_id": track.id, "classification": track.classification},
        )
    return None


def evaluate_geofence_breach_alerts(
    track: Track,
    geofence_results: "list[GeofenceEvaluationResult]",
    threat_factors: "ThreatFactors | None" = None,
) -> list[AlertCandidate]:
    """Trigger GEOFENCE_BREACH alert for each breached active geofence volume."""
    candidates: list[AlertCandidate] = []
    if track.state in (TrackState.LOST, TrackState.ARCHIVED):
        return candidates

    for g in geofence_results:
        if g.inside:
            severity = AlertSeverity.HIGH
            if threat_factors and threat_factors.level == ThreatLevel.CRITICAL:
                severity = AlertSeverity.CRITICAL

            candidates.append(
                AlertCandidate(
                    type=AlertType.GEOFENCE_BREACH,
                    severity=severity,
                    track_id=track.id,
                    reason=f"Track {track.id} breached geofence [{g.geofence_name}]",
                    metadata_json={
                        "geofence_id": g.geofence_id,
                        "geofence_name": g.geofence_name,
                        "altitude_indeterminate": g.altitude_indeterminate,
                        "distance_to_boundary_m": g.distance_to_boundary_meters,
                    },
                )
            )
    return candidates


def evaluate_track_lost_alert(track: Track) -> AlertCandidate | None:
    """Trigger TRACK_LOST alert when track transitions into LOST state."""
    return AlertCandidate(
        type=AlertType.TRACK_LOST,
        severity=AlertSeverity.LOW,
        track_id=track.id,
        reason=f"Track {track.id} lost after timeout",
        metadata_json={"track_id": track.id, "last_seen_at": track.last_seen_at.isoformat()},
    )


def evaluate_data_quality_alert(
    track: Track, quality: "TrackQualityScore"
) -> AlertCandidate | None:
    """Trigger DATA_QUALITY_LOW alert when active track quality drops below threshold."""
    if track.state == TrackState.ACTIVE and quality.quality < 0.30:
        return AlertCandidate(
            type=AlertType.DATA_QUALITY_LOW,
            severity=AlertSeverity.MEDIUM,
            track_id=track.id,
            reason=f"Track {track.id} data quality degraded to {quality.quality:.2f}",
            metadata_json={
                "quality": quality.quality,
                "confidence": quality.confidence_component,
                "diversity": quality.diversity_component,
                "continuity": quality.continuity_component,
            },
        )
    return None
