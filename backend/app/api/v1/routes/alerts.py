"""Operational alert query API endpoints."""

import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.user import User
from app.schemas.alert import AlertPage, AlertResponse

router = APIRouter()


def _decode_cursor(value: str | None) -> tuple[datetime, str] | None:
    if not value:
        return None
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        timestamp = datetime.fromisoformat(decoded[0])
        alert_id = str(decoded[1])
        if not (1 <= len(alert_id) <= 64):
            raise ValueError
        return timestamp, alert_id
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(status_code=400, detail="Invalid alert cursor") from None


def _encode_cursor(alert: Alert) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([alert.created_at.isoformat(), alert.id], separators=(",", ":")).encode()
    ).decode().rstrip("=")


@router.get("/alerts", response_model=AlertPage)
def list_alerts(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("alerts.read")),
    status: AlertStatus | None = Query(None),
    severity: AlertSeverity | None = Query(None),
    type: AlertType | None = Query(None),
    track_id: str | None = Query(None, max_length=36),
    sensor_id: str | None = Query(None, max_length=36),
    created_from: datetime | None = None,
    created_to: datetime | None = None,
    cursor: str | None = Query(None, max_length=256),
    limit: int = Query(50, ge=1, le=100),
):
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=400, detail="created_from must not be after created_to")

    statement = select(Alert)
    if status:
        statement = statement.where(Alert.status == status)
    if severity:
        statement = statement.where(Alert.severity == severity)
    if type:
        statement = statement.where(Alert.type == type)
    if track_id:
        statement = statement.where(Alert.track_id == track_id)
    if sensor_id:
        statement = statement.where(Alert.sensor_id == sensor_id)
    if created_from:
        statement = statement.where(Alert.created_at >= created_from.replace(tzinfo=None))
    if created_to:
        statement = statement.where(Alert.created_at <= created_to.replace(tzinfo=None))

    decoded = _decode_cursor(cursor)
    if decoded:
        statement = statement.where(
            or_(
                Alert.created_at < decoded[0],
                and_(Alert.created_at == decoded[0], Alert.id < decoded[1]),
            )
        )

    alerts = db.scalars(
        statement.order_by(Alert.created_at.desc(), Alert.id.desc()).limit(limit + 1)
    ).all()

    next_cursor = _encode_cursor(alerts[limit - 1]) if len(alerts) > limit else None
    return AlertPage(
        items=[AlertResponse.model_validate(a) for a in alerts[:limit]],
        next_cursor=next_cursor,
    )


@router.get("/alerts/{alert_id}", response_model=AlertResponse)
def get_alert(
    alert_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("alerts.read")),
):
    alert = db.get(Alert, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="Alert not found")
    return AlertResponse.model_validate(alert)
