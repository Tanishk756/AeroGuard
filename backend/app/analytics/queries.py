"""Analytical query aggregations over historical operational records."""

from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.history.queries import validate_time_window
from app.models.alert import Alert, AlertType
from app.models.detection import Detection
from app.models.threat import ThreatAssessment
from app.models.track import Track


def aggregate_detection_metrics(
    db: Session, start_time: datetime | None = None, end_time: datetime | None = None
) -> dict:
    norm_start, norm_end = validate_time_window(start_time, end_time)

    stmt = select(Detection)
    if norm_start is not None:
        stmt = stmt.where(Detection.timestamp >= norm_start)
    if norm_end is not None:
        stmt = stmt.where(Detection.timestamp <= norm_end)

    detections = db.scalars(stmt).all()
    total = len(detections)
    if total == 0:
        return {
            "total_detections": 0,
            "by_sensor": {},
            "by_modality": {},
            "by_source_class": {},
            "avg_confidence": 0.0,
        }

    by_sensor: dict[str, int] = {}
    by_modality: dict[str, int] = {}
    by_source_class: dict[str, int] = {}
    conf_sum = 0.0

    for d in detections:
        by_sensor[d.sensor_id] = by_sensor.get(d.sensor_id, 0) + 1
        by_modality[d.source_type] = by_modality.get(d.source_type, 0) + 1
        by_source_class[d.source_class.value] = by_source_class.get(d.source_class.value, 0) + 1
        conf_sum += d.confidence

    return {
        "total_detections": total,
        "by_sensor": by_sensor,
        "by_modality": by_modality,
        "by_source_class": by_source_class,
        "avg_confidence": round(conf_sum / total, 4),
    }


def aggregate_track_metrics(
    db: Session, start_time: datetime | None = None, end_time: datetime | None = None
) -> dict:
    norm_start, norm_end = validate_time_window(start_time, end_time)

    stmt = select(Track)
    if norm_start is not None:
        stmt = stmt.where(Track.last_seen_at >= norm_start)
    if norm_end is not None:
        stmt = stmt.where(Track.first_seen_at <= norm_end)

    tracks = db.scalars(stmt).all()
    total = len(tracks)
    if total == 0:
        return {
            "total_tracks": 0,
            "by_state": {},
            "by_classification": {},
            "avg_confidence": 0.0,
            "avg_source_count": 0.0,
        }

    by_state: dict[str, int] = {}
    by_classification: dict[str, int] = {}
    conf_sum = 0.0
    source_sum = 0

    for t in tracks:
        by_state[t.state.value] = by_state.get(t.state.value, 0) + 1
        cls_key = t.classification or "unclassified"
        by_classification[cls_key] = by_classification.get(cls_key, 0) + 1
        conf_sum += t.confidence
        source_sum += t.source_count

    return {
        "total_tracks": total,
        "by_state": by_state,
        "by_classification": by_classification,
        "avg_confidence": round(conf_sum / total, 4),
        "avg_source_count": round(source_sum / total, 2),
    }


def aggregate_alert_metrics(
    db: Session, start_time: datetime | None = None, end_time: datetime | None = None
) -> dict:
    norm_start, norm_end = validate_time_window(start_time, end_time)

    stmt = select(Alert)
    if norm_start is not None:
        stmt = stmt.where(Alert.created_at >= norm_start)
    if norm_end is not None:
        stmt = stmt.where(Alert.created_at <= norm_end)

    alerts = db.scalars(stmt).all()
    total = len(alerts)
    if total == 0:
        return {
            "total_alerts": 0,
            "by_type": {},
            "by_severity": {},
            "by_status": {},
        }

    by_type: dict[str, int] = {}
    by_severity: dict[str, int] = {}
    by_status: dict[str, int] = {}

    for a in alerts:
        by_type[a.type.value] = by_type.get(a.type.value, 0) + 1
        by_severity[a.severity.value] = by_severity.get(a.severity.value, 0) + 1
        by_status[a.status.value] = by_status.get(a.status.value, 0) + 1

    return {
        "total_alerts": total,
        "by_type": by_type,
        "by_severity": by_severity,
        "by_status": by_status,
    }


def aggregate_threat_metrics(
    db: Session, start_time: datetime | None = None, end_time: datetime | None = None
) -> dict:
    norm_start, norm_end = validate_time_window(start_time, end_time)

    stmt = select(ThreatAssessment)
    if norm_start is not None:
        stmt = stmt.where(ThreatAssessment.updated_at >= norm_start)
    if norm_end is not None:
        stmt = stmt.where(ThreatAssessment.updated_at <= norm_end)

    threats = db.scalars(stmt).all()
    total = len(threats)
    if total == 0:
        return {
            "total_assessed": 0,
            "by_level": {},
            "avg_score": 0.0,
            "max_score": 0.0,
        }

    by_level: dict[str, int] = {}
    score_sum = 0.0
    max_score = 0.0

    for th in threats:
        by_level[th.level.value] = by_level.get(th.level.value, 0) + 1
        score_sum += th.score
        if th.score > max_score:
            max_score = th.score

    return {
        "total_assessed": total,
        "by_level": by_level,
        "avg_score": round(score_sum / total, 2),
        "max_score": round(max_score, 2),
    }


def aggregate_intelligence_metrics(
    db: Session, start_time: datetime | None = None, end_time: datetime | None = None
) -> dict:
    """Aggregate defensive intelligence snapshots, swarm groups, and behavior events."""
    from app.models.intelligence_history import (
        BehaviorEventHistory,
        IntelligenceSnapshot,
        TrackGroupHistory,
    )

    norm_start, norm_end = validate_time_window(start_time, end_time)

    # 1. Query snapshots
    snap_stmt = select(IntelligenceSnapshot)
    if norm_start is not None:
        snap_stmt = snap_stmt.where(IntelligenceSnapshot.timestamp >= norm_start)
    if norm_end is not None:
        snap_stmt = snap_stmt.where(IntelligenceSnapshot.timestamp <= norm_end)

    snapshots = list(db.scalars(snap_stmt.order_by(IntelligenceSnapshot.timestamp.asc())).all())
    total_snapshots = len(snapshots)

    peak_threat = 0.0
    threat_time_series: list[dict] = []
    for s in snapshots:
        if s.peak_threat_score > peak_threat:
            peak_threat = s.peak_threat_score
        threat_time_series.append({
            "timestamp": s.timestamp.isoformat() if s.timestamp else None,
            "peak_threat_score": s.peak_threat_score,
            "group_count": s.group_count,
            "formation_count": s.formation_count,
            "active_track_count": s.active_track_count,
        })

    # Sample time series to max 50 points if dense
    if len(threat_time_series) > 50:
        step = len(threat_time_series) // 50
        threat_time_series = threat_time_series[::step]

    # 2. Query group history
    grp_stmt = select(TrackGroupHistory)
    if norm_start is not None:
        grp_stmt = grp_stmt.where(TrackGroupHistory.timestamp >= norm_start)
    if norm_end is not None:
        grp_stmt = grp_stmt.where(TrackGroupHistory.timestamp <= norm_end)

    group_rows = list(db.scalars(grp_stmt.order_by(TrackGroupHistory.timestamp.asc())).all())
    total_groups = len(group_rows)

    group_state_dist: dict[str, int] = {}
    total_members = 0
    max_members = 0
    coord_sum = 0.0
    coord_count = 0
    coordination_peaks: list[dict] = []

    for gr in group_rows:
        group_state_dist[gr.behavioral_state] = group_state_dist.get(gr.behavioral_state, 0) + 1
        total_members += gr.member_count
        if gr.member_count > max_members:
            max_members = gr.member_count

        if gr.coordination_index is not None:
            coord_sum += gr.coordination_index
            coord_count += 1
            if gr.coordination_index >= 0.70:
                coordination_peaks.append({
                    "timestamp": gr.timestamp.isoformat() if gr.timestamp else None,
                    "group_id": gr.group_id,
                    "member_count": gr.member_count,
                    "coordination_index": round(gr.coordination_index, 3),
                    "formation_type": gr.formation_type or "DYNAMIC",
                })

    # Sort coordination peaks by highest coordination index
    coordination_peaks.sort(key=lambda p: p["coordination_index"], reverse=True)
    coordination_peaks = coordination_peaks[:20]

    # 3. Query behavior event transitions
    beh_stmt = select(BehaviorEventHistory)
    if norm_start is not None:
        beh_stmt = beh_stmt.where(BehaviorEventHistory.timestamp >= norm_start)
    if norm_end is not None:
        beh_stmt = beh_stmt.where(BehaviorEventHistory.timestamp <= norm_end)

    behavior_rows = list(db.scalars(beh_stmt.order_by(BehaviorEventHistory.timestamp.asc())).all())
    total_behaviors = len(behavior_rows)

    behavior_dist: dict[str, int] = {}
    for b in behavior_rows:
        behavior_dist[b.new_state] = behavior_dist.get(b.new_state, 0) + 1

    return {
        "window_start": norm_start or (datetime.now() if not snapshots else snapshots[0].timestamp),
        "window_end": norm_end or (datetime.now() if not snapshots else snapshots[-1].timestamp),
        "total_snapshots": total_snapshots,
        "total_group_events": total_groups,
        "total_behavior_transitions": total_behaviors,
        "behavior_distribution": behavior_dist,
        "group_state_distribution": group_state_dist,
        "avg_group_size": round(total_members / total_groups, 2) if total_groups > 0 else 0.0,
        "max_group_size": max_members,
        "avg_coordination_index": round(coord_sum / coord_count, 3) if coord_count > 0 else 0.0,
        "peak_threat_score": round(peak_threat, 2),
        "threat_score_time_series": threat_time_series,
        "coordination_peaks": coordination_peaks,
    }
