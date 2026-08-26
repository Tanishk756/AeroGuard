"""Analytics service coordinating metrics queries and bounded aggregations."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.analytics.metrics import compute_analytics_summary
from app.analytics.queries import (
    aggregate_alert_metrics,
    aggregate_detection_metrics,
    aggregate_threat_metrics,
    aggregate_track_metrics,
)
from app.schemas.analytics import (
    AlertMetrics,
    AnalyticsSummaryResponse,
    DetectionMetrics,
    ThreatMetrics,
    TrackMetrics,
)


class AnalyticsService:
    def __init__(self, db: Session):
        self.db = db

    def get_summary(
        self, window_start: datetime, window_end: datetime
    ) -> AnalyticsSummaryResponse:
        return compute_analytics_summary(self.db, window_start=window_start, window_end=window_end)

    def get_detection_metrics(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> DetectionMetrics:
        data = aggregate_detection_metrics(self.db, start_time=start_time, end_time=end_time)
        return DetectionMetrics(**data)

    def get_track_metrics(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> TrackMetrics:
        data = aggregate_track_metrics(self.db, start_time=start_time, end_time=end_time)
        return TrackMetrics(**data)

    def get_alert_metrics(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> AlertMetrics:
        data = aggregate_alert_metrics(self.db, start_time=start_time, end_time=end_time)
        return AlertMetrics(**data)

    def get_threat_metrics(
        self, start_time: datetime | None = None, end_time: datetime | None = None
    ) -> ThreatMetrics:
        data = aggregate_threat_metrics(self.db, start_time=start_time, end_time=end_time)
        return ThreatMetrics(**data)
