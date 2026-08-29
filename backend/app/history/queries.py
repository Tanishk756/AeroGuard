"""Bounded historical queries over operational truth tables."""

from datetime import UTC, datetime, timedelta
from typing import Any, Sequence

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory


MAX_QUERY_WINDOW_SECONDS = 30 * 86400  # 30 days max window
MAX_PAGE_LIMIT = 100


def normalize_timestamp(t: datetime | None) -> datetime | None:
    """Convert timezone-aware datetime to naive UTC datetime, leaving naive as UTC."""
    if t is None:
        return None
    if t.tzinfo is not None:
        return t.astimezone(UTC).replace(tzinfo=None)
    return t


def validate_time_window(start_time: datetime | None, end_time: datetime | None) -> tuple[datetime | None, datetime | None]:
    """Validate and normalize naive UTC time boundaries."""
    norm_start = normalize_timestamp(start_time)
    norm_end = normalize_timestamp(end_time)

    if norm_start and norm_end:
        if norm_start > norm_end:
            raise ValueError("start_time must be less than or equal to end_time")
        if (norm_end - norm_start).total_seconds() > MAX_QUERY_WINDOW_SECONDS:
            raise ValueError(f"Time window exceeds maximum allowed limit of {MAX_QUERY_WINDOW_SECONDS // 86400} days")

    return norm_start, norm_end


def query_historical_detections(
    db: Session,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    sensor_id: str | None = None,
    source_type: str | None = None,
    classification: str | None = None,
    track_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Detection], int]:
    """Query historical detections by time range and filters with deterministic sorting."""
    norm_start, norm_end = validate_time_window(start_time, end_time)
    page_limit = max(1, min(limit, MAX_PAGE_LIMIT))
    page_offset = max(0, offset)

    statement = select(Detection)
    count_stmt = select(func.count(Detection.id))

    if norm_start is not None:
        statement = statement.where(Detection.timestamp >= norm_start)
        count_stmt = count_stmt.where(Detection.timestamp >= norm_start)
    if norm_end is not None:
        statement = statement.where(Detection.timestamp <= norm_end)
        count_stmt = count_stmt.where(Detection.timestamp <= norm_end)
    if sensor_id is not None:
        statement = statement.where(Detection.sensor_id == sensor_id)
        count_stmt = count_stmt.where(Detection.sensor_id == sensor_id)
    if source_type is not None:
        statement = statement.where(Detection.source_type == source_type)
        count_stmt = count_stmt.where(Detection.source_type == source_type)
    if classification is not None:
        statement = statement.where(Detection.classification == classification)
        count_stmt = count_stmt.where(Detection.classification == classification)
    if track_id is not None:
        statement = statement.where(Detection.track_id == track_id)
        count_stmt = count_stmt.where(Detection.track_id == track_id)

    total_count = db.scalar(count_stmt) or 0
    items = list(
        db.scalars(
            statement.order_by(Detection.timestamp.asc(), Detection.id.asc())
            .limit(page_limit)
            .offset(page_offset)
        ).all()
    )
    return items, total_count


def query_historical_track_points(
    db: Session,
    track_id: str,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TrackHistory], int]:
    """Query append-only historical track points for a track."""
    norm_start, norm_end = validate_time_window(start_time, end_time)
    page_limit = max(1, min(limit, MAX_PAGE_LIMIT))
    page_offset = max(0, offset)

    statement = select(TrackHistory).where(TrackHistory.track_id == track_id)
    count_stmt = select(func.count(TrackHistory.id)).where(TrackHistory.track_id == track_id)

    if norm_start is not None:
        statement = statement.where(TrackHistory.timestamp >= norm_start)
        count_stmt = count_stmt.where(TrackHistory.timestamp >= norm_start)
    if norm_end is not None:
        statement = statement.where(TrackHistory.timestamp <= norm_end)
        count_stmt = count_stmt.where(TrackHistory.timestamp <= norm_end)

    total_count = db.scalar(count_stmt) or 0
    items = list(
        db.scalars(
            statement.order_by(TrackHistory.sequence.asc(), TrackHistory.timestamp.asc())
            .limit(page_limit)
            .offset(page_offset)
        ).all()
    )
    return items, total_count


def get_track_state_at(db: Session, track_id: str, as_of_time: datetime) -> TrackHistory | None:
    """Retrieve the latest known historical track state point at or before as_of_time."""
    norm_time = normalize_timestamp(as_of_time)
    statement = (
        select(TrackHistory)
        .where(TrackHistory.track_id == track_id, TrackHistory.timestamp <= norm_time)
        .order_by(TrackHistory.timestamp.desc(), TrackHistory.sequence.desc())
        .limit(1)
    )
    return db.scalar(statement)


def query_historical_alerts(
    db: Session,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    alert_type: AlertType | None = None,
    severity: AlertSeverity | None = None,
    status: AlertStatus | None = None,
    track_id: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[Alert], int]:
    """Query historical alerts with deterministic sorting."""
    norm_start, norm_end = validate_time_window(start_time, end_time)
    page_limit = max(1, min(limit, MAX_PAGE_LIMIT))
    page_offset = max(0, offset)

    statement = select(Alert)
    count_stmt = select(func.count(Alert.id))

    if norm_start is not None:
        statement = statement.where(Alert.created_at >= norm_start)
        count_stmt = count_stmt.where(Alert.created_at >= norm_start)
    if norm_end is not None:
        statement = statement.where(Alert.created_at <= norm_end)
        count_stmt = count_stmt.where(Alert.created_at <= norm_end)
    if alert_type is not None:
        statement = statement.where(Alert.type == alert_type)
        count_stmt = count_stmt.where(Alert.type == alert_type)
    if severity is not None:
        statement = statement.where(Alert.severity == severity)
        count_stmt = count_stmt.where(Alert.severity == severity)
    if status is not None:
        statement = statement.where(Alert.status == status)
        count_stmt = count_stmt.where(Alert.status == status)
    if track_id is not None:
        statement = statement.where(Alert.track_id == track_id)
        count_stmt = count_stmt.where(Alert.track_id == track_id)

    total_count = db.scalar(count_stmt) or 0
    items = list(
        db.scalars(
            statement.order_by(Alert.created_at.asc(), Alert.id.asc())
            .limit(page_limit)
            .offset(page_offset)
        ).all()
    )
    return items, total_count


def query_historical_threats(
    db: Session,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    track_id: str | None = None,
    level: ThreatLevel | None = None,
    min_score: float | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[ThreatAssessment], int]:
    """Query historical threat assessments with deterministic sorting."""
    norm_start, norm_end = validate_time_window(start_time, end_time)
    page_limit = max(1, min(limit, MAX_PAGE_LIMIT))
    page_offset = max(0, offset)

    statement = select(ThreatAssessment)
    count_stmt = select(func.count(ThreatAssessment.id))

    if norm_start is not None:
        statement = statement.where(ThreatAssessment.updated_at >= norm_start)
        count_stmt = count_stmt.where(ThreatAssessment.updated_at >= norm_start)
    if norm_end is not None:
        statement = statement.where(ThreatAssessment.updated_at <= norm_end)
        count_stmt = count_stmt.where(ThreatAssessment.updated_at <= norm_end)
    if track_id is not None:
        statement = statement.where(ThreatAssessment.track_id == track_id)
        count_stmt = count_stmt.where(ThreatAssessment.track_id == track_id)
    if level is not None:
        statement = statement.where(ThreatAssessment.level == level)
        count_stmt = count_stmt.where(ThreatAssessment.level == level)
    if min_score is not None:
        statement = statement.where(ThreatAssessment.score >= min_score)
        count_stmt = count_stmt.where(ThreatAssessment.score >= min_score)

    total_count = db.scalar(count_stmt) or 0
    items = list(
        db.scalars(
            statement.order_by(ThreatAssessment.updated_at.asc(), ThreatAssessment.id.asc())
            .limit(page_limit)
            .offset(page_offset)
        ).all()
    )
    return items, total_count


def get_intelligence_snapshot_at(
    db: Session,
    as_of_time: datetime,
    max_age_seconds: float = 60.0,
) -> tuple[dict | None, datetime | None]:
    """Retrieve the closest historical intelligence snapshot JSON at or before as_of_time."""
    from app.models.intelligence_history import IntelligenceSnapshot

    norm_time = normalize_timestamp(as_of_time)
    if norm_time is None:
        return None, None

    min_time = norm_time - timedelta(seconds=max_age_seconds)
    statement = (
        select(IntelligenceSnapshot)
        .where(
            IntelligenceSnapshot.timestamp <= norm_time,
            IntelligenceSnapshot.timestamp >= min_time,
        )
        .order_by(IntelligenceSnapshot.timestamp.desc(), IntelligenceSnapshot.created_at.desc())
        .limit(1)
    )
    row = db.scalar(statement)
    if row is None:
        return None, None
    return row.summary_json, row.timestamp


def query_historical_groups_at(
    db: Session,
    as_of_time: datetime,
    max_age_seconds: float = 30.0,
) -> list[Any]:
    """Retrieve the latest known group states at or before as_of_time within a lookback window."""
    from app.models.intelligence_history import TrackGroupHistory

    norm_time = normalize_timestamp(as_of_time)
    if norm_time is None:
        return []

    min_time = norm_time - timedelta(seconds=max_age_seconds)
    statement = (
        select(TrackGroupHistory)
        .where(
            TrackGroupHistory.timestamp <= norm_time,
            TrackGroupHistory.timestamp >= min_time,
        )
        .order_by(TrackGroupHistory.group_id.asc(), TrackGroupHistory.timestamp.desc())
    )
    all_rows = list(db.scalars(statement).all())
    # Deduplicate by group_id preserving the latest timestamp per group
    seen_groups: set[str] = set()
    latest_groups = []
    for r in all_rows:
        if r.group_id not in seen_groups:
            seen_groups.add(r.group_id)
            latest_groups.append(r)
    return latest_groups
