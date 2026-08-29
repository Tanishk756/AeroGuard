"""REST API routes for deterministic descriptive operational analytics."""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.analytics.service import AnalyticsService
from app.database.session import get_db
from app.dependencies import require_any_permission, require_permission
from app.models.user import User
from app.schemas.analytics import (
    AlertMetrics,
    AnalyticsSummaryResponse,
    DetectionMetrics,
    IntelligenceAnalyticsReport,
    ThreatMetrics,
    TrackMetrics,
)

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    window_start: Annotated[datetime, Query()],
    window_end: Annotated[datetime, Query()],
    db: Session = Depends(get_db),
    _: User = Depends(
        require_any_permission("tracks.read", "sensors.read", "alerts.read", "threats.read", "scenarios.read")
    ),
) -> AnalyticsSummaryResponse:
    try:
        service = AnalyticsService(db)
        return service.get_summary(window_start=window_start, window_end=window_end)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/detections", response_model=DetectionMetrics)
def get_detection_metrics(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("sensors.read")),
) -> DetectionMetrics:
    try:
        service = AnalyticsService(db)
        return service.get_detection_metrics(start_time=start_time, end_time=end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/tracks", response_model=TrackMetrics)
def get_track_metrics(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
) -> TrackMetrics:
    try:
        service = AnalyticsService(db)
        return service.get_track_metrics(start_time=start_time, end_time=end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/alerts", response_model=AlertMetrics)
def get_alert_metrics(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("alerts.read")),
) -> AlertMetrics:
    try:
        service = AnalyticsService(db)
        return service.get_alert_metrics(start_time=start_time, end_time=end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/threats", response_model=ThreatMetrics)
def get_threat_metrics(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("threats.read")),
) -> ThreatMetrics:
    try:
        service = AnalyticsService(db)
        return service.get_threat_metrics(start_time=start_time, end_time=end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.get("/intelligence", response_model=IntelligenceAnalyticsReport)
def get_intelligence_metrics(
    start_time: Annotated[datetime | None, Query()] = None,
    end_time: Annotated[datetime | None, Query()] = None,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("tracks.read", "threats.read")),
) -> IntelligenceAnalyticsReport:
    try:
        service = AnalyticsService(db)
        return service.get_intelligence_metrics(start_time=start_time, end_time=end_time)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
