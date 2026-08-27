"""Operational alert service managing alert generation, deduplication, and lifecycle."""

from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.alerts.events import AlertRaised
from app.alerts.rules import AlertCandidate
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType


class AlertService:
    def __init__(self, db: Session):
        self.db = db

    def process_candidates(
        self,
        candidates: list[AlertCandidate],
        now: datetime | None = None,
    ) -> list[AlertRaised]:
        """Process alert candidates with strict deduplication and write new Alert records."""
        eval_time = now or datetime.now(UTC).replace(tzinfo=None)
        raised_events: list[AlertRaised] = []

        for cand in candidates:
            # Check for existing non-resolved alert for this track and alert type
            query = select(Alert).where(
                Alert.type == cand.type,
                Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
            )
            if cand.track_id:
                query = query.where(Alert.track_id == cand.track_id)
            if cand.sensor_id:
                query = query.where(Alert.sensor_id == cand.sensor_id)

            existing_alerts = self.db.scalars(query).all()

            # For GEOFENCE_BREACH, deduplicate by specific geofence_id in metadata
            is_duplicate = False
            target_geofence = cand.metadata_json.get("geofence_id")
            for alert in existing_alerts:
                if cand.type == AlertType.GEOFENCE_BREACH:
                    if alert.metadata_json.get("geofence_id") == target_geofence:
                        is_duplicate = True
                        # Escalate severity if candidate is higher
                        if cand.severity == AlertSeverity.CRITICAL and alert.severity != AlertSeverity.CRITICAL:
                            alert.severity = AlertSeverity.CRITICAL
                            alert.updated_at = eval_time
                        break
                else:
                    is_duplicate = True
                    break

            if is_duplicate:
                continue

            # Create new persistent Alert record
            new_alert = Alert(
                type=cand.type,
                severity=cand.severity,
                status=AlertStatus.OPEN,
                track_id=cand.track_id,
                sensor_id=cand.sensor_id,
                reason=cand.reason[:512],
                metadata_json=cand.metadata_json,
                created_at=eval_time,
                updated_at=eval_time,
            )
            self.db.add(new_alert)

            raised_events.append(
                AlertRaised(
                    alert_id=new_alert.id,
                    type=new_alert.type.value,
                    severity=new_alert.severity.value,
                    track_id=new_alert.track_id,
                    sensor_id=new_alert.sensor_id,
                    reason=new_alert.reason,
                    timestamp=eval_time,
                )
            )

            try:
                from app.core.events import get_event_bus
                from app.schemas.events import RealtimeChannel, RealtimeEventType

                get_event_bus().publish(
                    event_type=RealtimeEventType.ALERT_CREATED,
                    channel=RealtimeChannel.OPERATIONAL,
                    payload={
                        "id": new_alert.id,
                        "type": new_alert.type.value,
                        "severity": new_alert.severity.value,
                        "status": new_alert.status.value,
                        "track_id": new_alert.track_id,
                        "sensor_id": new_alert.sensor_id,
                        "reason": new_alert.reason,
                        "metadata_json": new_alert.metadata_json or {},
                        "created_at": new_alert.created_at.isoformat() if new_alert.created_at else eval_time.isoformat(),
                        "updated_at": new_alert.updated_at.isoformat() if new_alert.updated_at else eval_time.isoformat(),
                    },
                    resource_type="alert",
                    resource_id=new_alert.id,
                )
            except Exception:
                pass

        return raised_events

    def resolve_track_alerts(
        self,
        track_id: str,
        alert_types: list[AlertType] | None = None,
        now: datetime | None = None,
    ) -> int:
        """Resolve active alerts for a track when operational conditions clear."""
        eval_time = now or datetime.now(UTC).replace(tzinfo=None)
        query = select(Alert).where(
            Alert.track_id == track_id,
            Alert.status.in_([AlertStatus.OPEN, AlertStatus.ACKNOWLEDGED]),
        )
        if alert_types:
            query = query.where(Alert.type.in_(alert_types))

        active_alerts = self.db.scalars(query).all()
        for alert in active_alerts:
            alert.status = AlertStatus.RESOLVED
            alert.resolved_at = eval_time
            alert.updated_at = eval_time
            try:
                from app.core.events import get_event_bus
                from app.schemas.events import RealtimeChannel, RealtimeEventType

                get_event_bus().publish(
                    event_type=RealtimeEventType.ALERT_UPDATED,
                    channel=RealtimeChannel.OPERATIONAL,
                    payload={
                        "id": alert.id,
                        "type": alert.type.value,
                        "severity": alert.severity.value,
                        "status": alert.status.value,
                        "track_id": alert.track_id,
                        "sensor_id": alert.sensor_id,
                        "reason": alert.reason,
                        "metadata_json": alert.metadata_json or {},
                        "resolved_at": alert.resolved_at.isoformat() if alert.resolved_at else None,
                        "created_at": alert.created_at.isoformat() if alert.created_at else None,
                        "updated_at": alert.updated_at.isoformat() if alert.updated_at else None,
                    },
                    resource_type="alert",
                    resource_id=alert.id,
                )
            except Exception:
                pass

        return len(active_alerts)
