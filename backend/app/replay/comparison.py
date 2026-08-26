"""Comparison engine for deterministic replay runs."""

from sqlalchemy.orm import Session

from app.analytics.queries import (
    aggregate_alert_metrics,
    aggregate_detection_metrics,
    aggregate_threat_metrics,
    aggregate_track_metrics,
)
from app.replay.models import ReplayConfig
from app.schemas.replay import (
    ReplayComparisonReport,
    ReplayComparisonRequest,
)


def compare_replay_runs(db: Session, request: ReplayComparisonRequest) -> ReplayComparisonReport:
    """Compare two replay runs based on canonical operational data over their time windows."""
    cfg1 = ReplayConfig.from_request(request.request_1)
    cfg2 = ReplayConfig.from_request(request.request_2)

    # 1. Gather Metrics
    det1 = aggregate_detection_metrics(db, cfg1.start_time, cfg1.end_time)
    det2 = aggregate_detection_metrics(db, cfg2.start_time, cfg2.end_time)

    track1 = aggregate_track_metrics(db, cfg1.start_time, cfg1.end_time)
    track2 = aggregate_track_metrics(db, cfg2.start_time, cfg2.end_time)

    alert1 = aggregate_alert_metrics(db, cfg1.start_time, cfg1.end_time)
    alert2 = aggregate_alert_metrics(db, cfg2.start_time, cfg2.end_time)

    threat1 = aggregate_threat_metrics(db, cfg1.start_time, cfg1.end_time)
    threat2 = aggregate_threat_metrics(db, cfg2.start_time, cfg2.end_time)

    differences: list[str] = []

    # Detection checks
    det_match = det1["total_detections"] == det2["total_detections"]
    if not det_match:
        differences.append(
            f"Detection count mismatch: run1={det1['total_detections']}, run2={det2['total_detections']}"
        )
    if det1["by_sensor"] != det2["by_sensor"]:
        differences.append(f"Detection sensor distribution mismatch: {det1['by_sensor']} vs {det2['by_sensor']}")

    # Track checks
    track_match = track1["total_tracks"] == track2["total_tracks"]
    if not track_match:
        differences.append(f"Track count mismatch: run1={track1['total_tracks']}, run2={track2['total_tracks']}")
    if track1["by_state"] != track2["by_state"]:
        differences.append(f"Track state distribution mismatch: {track1['by_state']} vs {track2['by_state']}")

    # Alert checks
    alert_match = alert1["total_alerts"] == alert2["total_alerts"]
    if not alert_match:
        differences.append(f"Alert count mismatch: run1={alert1['total_alerts']}, run2={alert2['total_alerts']}")
    if alert1["by_type"] != alert2["by_type"]:
        differences.append(f"Alert type mismatch: {alert1['by_type']} vs {alert2['by_type']}")

    # Threat checks
    threat_match = threat1["total_assessed"] == threat2["total_assessed"]
    if not threat_match:
        differences.append(f"Threat count mismatch: run1={threat1['total_assessed']}, run2={threat2['total_assessed']}")
    if threat1["by_level"] != threat2["by_level"]:
        differences.append(f"Threat level distribution mismatch: {threat1['by_level']} vs {threat2['by_level']}")

    identical = len(differences) == 0

    return ReplayComparisonReport(
        identical=identical,
        total_detections_match=det_match,
        total_tracks_match=track_match,
        total_alerts_match=alert_match,
        total_threats_match=threat_match,
        detections_count_1=det1["total_detections"],
        detections_count_2=det2["total_detections"],
        tracks_count_1=track1["total_tracks"],
        tracks_count_2=track2["total_tracks"],
        alerts_count_1=alert1["total_alerts"],
        alerts_count_2=alert2["total_alerts"],
        threats_count_1=threat1["total_assessed"],
        threats_count_2=threat2["total_assessed"],
        differences=differences,
    )
