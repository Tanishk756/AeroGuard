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
