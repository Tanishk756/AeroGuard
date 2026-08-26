"""Unified operational timeline aggregation and normalization."""

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.history.queries import (
    MAX_PAGE_LIMIT,
    query_historical_alerts,
    query_historical_detections,
    query_historical_threats,
    validate_time_window,
)
from app.models.alert import AlertType
from app.models.track import TrackHistory
from app.schemas.history import TimelineEventType, TimelineItem

EVENT_TYPE_PRECEDENCE = {
    TimelineEventType.DETECTION: 1,
    TimelineEventType.TRACK_UPDATE: 2,
    TimelineEventType.GEOFENCE_EVENT: 3,
    TimelineEventType.THREAT_ASSESSMENT: 4,
    TimelineEventType.ALERT_RAISED: 5,
    TimelineEventType.ALERT_RESOLVED: 6,
}


def build_operational_timeline(
    db: Session,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
    track_ids: list[str] | None = None,
    sensor_ids: list[str] | None = None,
    event_types: list[str] | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[list[TimelineItem], int]:
    """Aggregate, normalize, and sort operational timeline items deterministically."""
    norm_start, norm_end = validate_time_window(start_time, end_time)
    page_limit = max(1, min(limit, MAX_PAGE_LIMIT))
    page_offset = max(0, offset)

    selected_types = set(event_types) if event_types else None
    timeline_items: list[TimelineItem] = []

    # 1. Detections
    if selected_types is None or TimelineEventType.DETECTION.value in selected_types:
        dets, _ = query_historical_detections(
            db, start_time=norm_start, end_time=norm_end, limit=MAX_PAGE_LIMIT * 5
        )
        for d in dets:
            if track_ids and d.track_id not in track_ids:
                continue
            if sensor_ids and d.sensor_id not in sensor_ids:
                continue
            timeline_items.append(
                TimelineItem(
                    event_type=TimelineEventType.DETECTION,
                    timestamp=d.timestamp.replace(tzinfo=UTC),
                    entity_id=d.id,
                    track_id=d.track_id,
                    sensor_id=d.sensor_id,
                    summary=f"Observation from {d.sensor_id} (conf={d.confidence:.2f})",
                    payload={
                        "latitude": d.latitude,
                        "longitude": d.longitude,
                        "altitude": d.altitude,
                        "velocity": d.velocity,
                        "heading": d.heading,
                        "classification": d.classification,
                    },
                )
            )

    # 2. Track State History Updates
    if selected_types is None or TimelineEventType.TRACK_UPDATE.value in selected_types:
        stmt = select(TrackHistory)
        if norm_start is not None:
            stmt = stmt.where(TrackHistory.timestamp >= norm_start)
        if norm_end is not None:
            stmt = stmt.where(TrackHistory.timestamp <= norm_end)
        if track_ids:
            stmt = stmt.where(TrackHistory.track_id.in_(track_ids))

        track_histories = db.scalars(stmt.limit(MAX_PAGE_LIMIT * 5)).all()
        for th in track_histories:
            timeline_items.append(
                TimelineItem(
                    event_type=TimelineEventType.TRACK_UPDATE,
                    timestamp=th.timestamp.replace(tzinfo=UTC),
                    entity_id=th.id,
                    track_id=th.track_id,
                    sensor_id=None,
                    summary=f"Track {th.track_id} updated to state {th.state.value} (seq={th.sequence})",
                    payload={
                        "sequence": th.sequence,
                        "state": th.state.value,
                        "confidence": th.confidence,
                        "latitude": th.latitude,
                        "longitude": th.longitude,
                        "altitude": th.altitude,
                    },
                )
            )

    # 3. Threat Assessments
    if selected_types is None or TimelineEventType.THREAT_ASSESSMENT.value in selected_types:
        threats, _ = query_historical_threats(
            db, start_time=norm_start, end_time=norm_end, limit=MAX_PAGE_LIMIT * 5
        )
        for th in threats:
            if track_ids and th.track_id not in track_ids:
                continue
            timeline_items.append(
                TimelineItem(
                    event_type=TimelineEventType.THREAT_ASSESSMENT,
                    timestamp=th.updated_at.replace(tzinfo=UTC),
                    entity_id=th.id,
                    track_id=th.track_id,
                    sensor_id=None,
                    summary=f"Threat priority evaluated at {th.score:.1f} ({th.level.value}) for track {th.track_id}",
                    payload={
                        "score": th.score,
                        "level": th.level.value,
                        "factors": th.factors,
                    },
                )
            )

    # 4. Alerts Raised & Resolved
    if (
        selected_types is None
        or TimelineEventType.ALERT_RAISED.value in selected_types
        or TimelineEventType.ALERT_RESOLVED.value in selected_types
        or TimelineEventType.GEOFENCE_EVENT.value in selected_types
    ):
        alerts, _ = query_historical_alerts(
            db, start_time=norm_start, end_time=norm_end, limit=MAX_PAGE_LIMIT * 5
        )
        for a in alerts:
            if track_ids and a.track_id not in track_ids:
                continue
            if sensor_ids and a.sensor_id not in sensor_ids:
                continue

            # Geofence breach event classification
            if a.type == AlertType.GEOFENCE_BREACH:
                if selected_types is None or TimelineEventType.GEOFENCE_EVENT.value in selected_types:
                    timeline_items.append(
                        TimelineItem(
                            event_type=TimelineEventType.GEOFENCE_EVENT,
                            timestamp=a.created_at.replace(tzinfo=UTC),
                            entity_id=f"geofence-{a.id}",
                            track_id=a.track_id,
                            sensor_id=a.sensor_id,
                            summary=f"Geofence penetration alert: {a.reason}",
                            payload={"severity": a.severity.value, "reason": a.reason, "metadata": a.metadata_json},
                        )
                    )

            if selected_types is None or TimelineEventType.ALERT_RAISED.value in selected_types:
                timeline_items.append(
                    TimelineItem(
                        event_type=TimelineEventType.ALERT_RAISED,
                        timestamp=a.created_at.replace(tzinfo=UTC),
                        entity_id=f"alert-raised-{a.id}",
                        track_id=a.track_id,
                        sensor_id=a.sensor_id,
                        summary=f"Alert raised: {a.type.value} ({a.severity.value})",
                        payload={"type": a.type.value, "severity": a.severity.value, "reason": a.reason},
                    )
                )

            if (
                a.resolved_at is not None
                and (selected_types is None or TimelineEventType.ALERT_RESOLVED.value in selected_types)
                and (norm_start is None or a.resolved_at >= norm_start)
                and (norm_end is None or a.resolved_at <= norm_end)
            ):
                timeline_items.append(
                    TimelineItem(
                        event_type=TimelineEventType.ALERT_RESOLVED,
                        timestamp=a.resolved_at.replace(tzinfo=UTC),
                        entity_id=f"alert-resolved-{a.id}",
                        track_id=a.track_id,
                        sensor_id=a.sensor_id,
                        summary=f"Alert resolved: {a.type.value}",
                        payload={"type": a.type.value, "severity": a.severity.value},
                    )
                )

    # Deterministic sorting
    timeline_items.sort(
        key=lambda item: (
            item.timestamp,
            EVENT_TYPE_PRECEDENCE.get(item.event_type, 99),
            item.entity_id,
        )
    )

    total_count = len(timeline_items)
    paginated_items = timeline_items[page_offset : page_offset + page_limit]
    return paginated_items, total_count
