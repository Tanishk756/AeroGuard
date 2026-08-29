"""Deterministic descriptive metrics calculation."""

from datetime import datetime

from sqlalchemy.orm import Session

from app.analytics.queries import (
    aggregate_alert_metrics,
    aggregate_detection_metrics,
    aggregate_intelligence_metrics,
    aggregate_threat_metrics,
    aggregate_track_metrics,
)
from app.models.alert import AlertType
from app.schemas.analytics import (
    AlertMetrics,
    AnalyticsSummaryResponse,
    DetectionMetrics,
    IntelligenceAnalyticsReport,
    ThreatMetrics,
    TrackMetrics,
)


def compute_analytics_summary(
    db: Session, window_start: datetime, window_end: datetime
) -> AnalyticsSummaryResponse:
    """Compute comprehensive bounded descriptive metrics over operational history."""
    det_data = aggregate_detection_metrics(db, window_start, window_end)
    track_data = aggregate_track_metrics(db, window_start, window_end)
    alert_data = aggregate_alert_metrics(db, window_start, window_end)
    threat_data = aggregate_threat_metrics(db, window_start, window_end)
    intel_data = aggregate_intelligence_metrics(db, window_start, window_end)

    geofence_breaches = alert_data.get("by_type", {}).get(AlertType.GEOFENCE_BREACH.value, 0)

    return AnalyticsSummaryResponse(
        window_start=window_start,
        window_end=window_end,
        detections=DetectionMetrics(**det_data),
        tracks=TrackMetrics(**track_data),
        alerts=AlertMetrics(**alert_data),
        threats=ThreatMetrics(**threat_data),
        intelligence=IntelligenceAnalyticsReport(**intel_data),
        geofence_breach_count=geofence_breaches,
    )
