"""Read-only audit event query API."""

import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.audit import AuditEvent
from app.models.user import User
from app.schemas.audit import AuditEventPage, AuditEventResponse

router = APIRouter()


def _decode_cursor(value: str | None) -> tuple[datetime, str] | None:
    if not value:
        return None
    try:
        decoded = json.loads(base64.urlsafe_b64decode(value.encode()).decode())
        timestamp = datetime.fromisoformat(decoded[0])
        event_id = str(decoded[1])
        if len(event_id) != 36:
            raise ValueError
        return timestamp, event_id
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(status_code=400, detail="Invalid audit cursor") from None


def _encode_cursor(event: AuditEvent) -> str:
    return base64.urlsafe_b64encode(json.dumps([event.timestamp.isoformat(), event.id], separators=(",", ":")).encode()).decode().rstrip("=")


@router.get("/audit/events", response_model=AuditEventPage)
def list_events(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("audit.read")),
    event_type: str | None = Query(None, max_length=64), result: str | None = Query(None, max_length=16),
    actor_id: str | None = Query(None, max_length=36), target_type: str | None = Query(None, max_length=64),
    target_id: str | None = Query(None, max_length=128), permission: str | None = Query(None, max_length=128),
    date_from: datetime | None = None, date_to: datetime | None = None,
    cursor: str | None = Query(None, max_length=256), limit: int = Query(50, ge=1, le=100),
):
    if date_from and date_to and date_from > date_to:
        raise HTTPException(status_code=400, detail="date_from must not be after date_to")
    statement = select(AuditEvent)
    if event_type: statement = statement.where(AuditEvent.event_type == event_type)
    if result: statement = statement.where(AuditEvent.result == result)
    if actor_id: statement = statement.where(AuditEvent.actor_user_id == actor_id)
    if target_type: statement = statement.where(AuditEvent.target_type == target_type)
    if target_id: statement = statement.where(AuditEvent.target_id == target_id)
    if permission: statement = statement.where(AuditEvent.permission == permission)
    if date_from: statement = statement.where(AuditEvent.timestamp >= date_from.replace(tzinfo=None))
    if date_to: statement = statement.where(AuditEvent.timestamp <= date_to.replace(tzinfo=None))
    decoded = _decode_cursor(cursor)
    if decoded: statement = statement.where(or_(AuditEvent.timestamp < decoded[0], and_(AuditEvent.timestamp == decoded[0], AuditEvent.id < decoded[1])))
    events = db.scalars(statement.order_by(AuditEvent.timestamp.desc(), AuditEvent.id.desc()).limit(limit + 1)).all()
    next_cursor = _encode_cursor(events[limit - 1]) if len(events) > limit else None
    return AuditEventPage(items=[AuditEventResponse.model_validate(event) for event in events[:limit]], next_cursor=next_cursor)


@router.get("/audit/events/{event_id}", response_model=AuditEventResponse)
def get_event(event_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission("audit.read"))):
    event = db.get(AuditEvent, event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return AuditEventResponse.model_validate(event)