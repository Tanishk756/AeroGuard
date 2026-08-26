"""History service providing unified access to historical queries and timelines."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.history.queries import (
    get_track_state_at,
    query_historical_alerts,
    query_historical_detections,
    query_historical_threats,
    query_historical_track_points,
)
from app.history.timeline import build_operational_timeline
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import TrackHistory
from app.schemas.history import TimelineItem


class HistoryService:
    def __init__(self, db: Session):
        self.db = db

    def get_detections(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        sensor_id: str | None = None,
        source_type: str | None = None,
        classification: str | None = None,
        track_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Detection], int]:
        return query_historical_detections(
            self.db,
            start_time=start_time,
            end_time=end_time,
            sensor_id=sensor_id,
            source_type=source_type,
            classification=classification,
            track_id=track_id,
            limit=limit,
            offset=offset,
        )

    def get_track_history(
        self,
        track_id: str,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TrackHistory], int]:
        return query_historical_track_points(
            self.db,
            track_id=track_id,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
            offset=offset,
        )

    def get_track_state_at_time(self, track_id: str, as_of_time: datetime) -> TrackHistory | None:
        return get_track_state_at(self.db, track_id=track_id, as_of_time=as_of_time)

    def get_alerts(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        alert_type: AlertType | None = None,
        severity: AlertSeverity | None = None,
        status: AlertStatus | None = None,
        track_id: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[Alert], int]:
        return query_historical_alerts(
            self.db,
            start_time=start_time,
            end_time=end_time,
            alert_type=alert_type,
            severity=severity,
            status=status,
            track_id=track_id,
            limit=limit,
            offset=offset,
        )

    def get_threats(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        track_id: str | None = None,
        level: ThreatLevel | None = None,
        min_score: float | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[ThreatAssessment], int]:
        return query_historical_threats(
            self.db,
            start_time=start_time,
            end_time=end_time,
            track_id=track_id,
            level=level,
            min_score=min_score,
            limit=limit,
            offset=offset,
        )

    def get_timeline(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        track_ids: list[str] | None = None,
        sensor_ids: list[str] | None = None,
        event_types: list[str] | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[TimelineItem], int]:
        return build_operational_timeline(
            self.db,
            start_time=start_time,
            end_time=end_time,
            track_ids=track_ids,
            sensor_ids=sensor_ids,
            event_types=event_types,
            limit=limit,
            offset=offset,
        )
