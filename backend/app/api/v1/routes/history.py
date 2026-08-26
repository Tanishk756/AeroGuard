"""REST API routes for historical operational queries and timeline."""

from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_any_permission, require_permission
from app.history.service import HistoryService
from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.models.threat import ThreatLevel
from app.models.user import User
from app.schemas.history import (
    HistoricalAlertItem,
    HistoricalAlertsPage,
    HistoricalDetectionItem,
    HistoricalDetectionsPage,
    HistoricalThreatItem,
    HistoricalThreatsPage,
    HistoricalTrackPoint,
    HistoricalTrackStateResponse,
    TimelinePage,
)

router = APIRouter(prefix="/history", tags=["history"])


@router.get("/detections", response_model=HistoricalDetectionsPage)
def get_historical_detections(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    sensor_id: Annotated[str | None, Query()] = None,
    source_type: Annotated[str | None, Query()] = None,
    classification: Annotated[str | None, Query()] = None,
    track_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sensors.read")),
) -> HistoricalDetectionsPage:
    try:
        service = HistoryService(db)
        items, total = service.get_detections(
            start_time=start_time,
            end_time=end_time,
            sensor_id=sensor_id,
            source_type=source_type,
            classification=classification,
            track_id=track_id,
            limit=limit,
            offset=offset,
        )
        return HistoricalDetectionsPage(
            items=[
                HistoricalDetectionItem(
                    id=d.id,
                    sensor_id=d.sensor_id,
                    source_detection_id=d.source_detection_id,
                    timestamp=d.timestamp.replace(tzinfo=UTC),
                    latitude=d.latitude,
                    longitude=d.longitude,
                    altitude=d.altitude,
                    velocity=d.velocity,
                    heading=d.heading,
                    confidence=d.confidence,
                    horizontal_uncertainty=d.horizontal_uncertainty,
                    vertical_uncertainty=d.vertical_uncertainty,
                    classification=d.classification,
                    source_class=d.source_class,
                    source_type=d.source_type,
                    track_id=d.track_id,
                )
                for d in items
            ],
            total_count=total,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/tracks/{track_id}", response_model=list[HistoricalTrackPoint])
def get_historical_track_points(
    track_id: str,
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
) -> list[HistoricalTrackPoint]:
    try:
        service = HistoryService(db)
        items, _ = service.get_track_history(
            track_id=track_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )
        return [
            HistoricalTrackPoint(
                sequence=th.sequence,
                timestamp=th.timestamp.replace(tzinfo=UTC),
                latitude=th.latitude,
                longitude=th.longitude,
                altitude=th.altitude,
                velocity=th.velocity,
                heading=th.heading,
                confidence=th.confidence,
                state=th.state,
                provenance=th.provenance,
                source_detection_ids=th.source_detection_ids,
            )
            for th in items
        ]
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/tracks/{track_id}/state", response_model=HistoricalTrackStateResponse)
def get_historical_track_state_at(
    track_id: str,
    as_of_time: Annotated[datetime, Query()],
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
) -> HistoricalTrackStateResponse:
    try:
        service = HistoryService(db)
        point = service.get_track_state_at_time(track_id=track_id, as_of_time=as_of_time)
        if point is None:
            return HistoricalTrackStateResponse(
                track_id=track_id, as_of_time=as_of_time, found=False, state_point=None
            )
        return HistoricalTrackStateResponse(
            track_id=track_id,
            as_of_time=as_of_time,
            found=True,
            state_point=HistoricalTrackPoint(
                sequence=point.sequence,
                timestamp=point.timestamp.replace(tzinfo=UTC),
                latitude=point.latitude,
                longitude=point.longitude,
                altitude=point.altitude,
                velocity=point.velocity,
                heading=point.heading,
                confidence=point.confidence,
                state=point.state,
                provenance=point.provenance,
                source_detection_ids=point.source_detection_ids,
            ),
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/alerts", response_model=HistoricalAlertsPage)
def get_historical_alerts(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    alert_type: Annotated[AlertType | None, Query()] = None,
    severity: Annotated[AlertSeverity | None, Query()] = None,
    alert_status: Annotated[AlertStatus | None, Query(alias="status")] = None,
    track_id: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("alerts.read")),
) -> HistoricalAlertsPage:
    try:
        service = HistoryService(db)
        items, total = service.get_alerts(
            start_time=start_time,
            end_time=end_time,
            alert_type=alert_type,
            severity=severity,
            status=alert_status,
            track_id=track_id,
            limit=limit,
            offset=offset,
        )
        return HistoricalAlertsPage(
            items=[
                HistoricalAlertItem(
                    id=a.id,
                    type=a.type,
                    severity=a.severity,
                    status=a.status,
                    track_id=a.track_id,
                    sensor_id=a.sensor_id,
                    reason=a.reason,
                    metadata_json=a.metadata_json,
                    created_at=a.created_at.replace(tzinfo=UTC),
                    updated_at=a.updated_at.replace(tzinfo=UTC),
                    resolved_at=a.resolved_at.replace(tzinfo=UTC) if a.resolved_at else None,
                )
                for a in items
            ],
            total_count=total,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/threats", response_model=HistoricalThreatsPage)
def get_historical_threats(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    track_id: Annotated[str | None, Query()] = None,
    level: Annotated[ThreatLevel | None, Query()] = None,
    min_score: Annotated[float | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("threats.read")),
) -> HistoricalThreatsPage:
    try:
        service = HistoryService(db)
        items, total = service.get_threats(
            start_time=start_time,
            end_time=end_time,
            track_id=track_id,
            level=level,
            min_score=min_score,
            limit=limit,
            offset=offset,
        )
        return HistoricalThreatsPage(
            items=[
                HistoricalThreatItem(
                    id=th.id,
                    track_id=th.track_id,
                    score=th.score,
                    level=th.level,
                    factors=th.factors,
                    created_at=th.created_at.replace(tzinfo=UTC),
                    updated_at=th.updated_at.replace(tzinfo=UTC),
                )
                for th in items
            ],
            total_count=total,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/timeline", response_model=TimelinePage)
def get_operational_timeline(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    track_id: Annotated[list[str] | None, Query()] = None,
    sensor_id: Annotated[list[str] | None, Query()] = None,
    event_type: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission("tracks.read", "sensors.read", "alerts.read", "threats.read", "scenarios.read")
    ),
) -> TimelinePage:
    try:
        service = HistoryService(db)
        items, total = service.get_timeline(
            start_time=start_time,
            end_time=end_time,
            track_ids=track_id,
            sensor_ids=sensor_id,
            event_types=event_type,
            limit=limit,
            offset=offset,
        )
        return TimelinePage(
            items=items,
            total_count=total,
            limit=limit,
            offset=offset,
        )
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
