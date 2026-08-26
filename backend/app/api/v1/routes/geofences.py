"""Operational geofence query API endpoints."""

import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.geofence import Geofence
from app.models.user import User
from app.schemas.geofence import GeofencePage, GeofenceResponse

router = APIRouter()


def _decode_cursor(value: str | None) -> tuple[datetime, str] | None:
    if not value:
        return None
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        timestamp = datetime.fromisoformat(decoded[0])
        geofence_id = str(decoded[1])
        if not (1 <= len(geofence_id) <= 64):
            raise ValueError
        return timestamp, geofence_id
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(status_code=400, detail="Invalid geofence cursor") from None


def _encode_cursor(geofence: Geofence) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([geofence.created_at.isoformat(), geofence.id], separators=(",", ":")).encode()
    ).decode().rstrip("=")


@router.get("/geofences", response_model=GeofencePage)
def list_geofences(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("scenarios.read")),
    enabled: bool | None = Query(None),
    cursor: str | None = Query(None, max_length=256),
    limit: int = Query(50, ge=1, le=100),
):
    statement = select(Geofence)
    if enabled is not None:
        statement = statement.where(Geofence.enabled == enabled)

    decoded = _decode_cursor(cursor)
    if decoded:
        statement = statement.where(
            or_(
                Geofence.created_at < decoded[0],
                and_(Geofence.created_at == decoded[0], Geofence.id < decoded[1]),
            )
        )

    geofences = db.scalars(
        statement.order_by(Geofence.created_at.desc(), Geofence.id.desc()).limit(limit + 1)
    ).all()

    next_cursor = _encode_cursor(geofences[limit - 1]) if len(geofences) > limit else None
    return GeofencePage(
        items=[GeofenceResponse.model_validate(g) for g in geofences[:limit]],
        next_cursor=next_cursor,
    )


@router.get("/geofences/{geofence_id}", response_model=GeofenceResponse)
def get_geofence(
    geofence_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("scenarios.read")),
):
    geofence = db.get(Geofence, geofence_id)
    if geofence is None:
        raise HTTPException(status_code=404, detail="Geofence not found")
    return GeofenceResponse.model_validate(geofence)
