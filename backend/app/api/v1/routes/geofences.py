"""Operational geofence query and management API endpoints."""

import base64
from datetime import UTC, datetime
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_any_permission, require_permission
from app.models.geofence import Geofence
from app.models.user import User
from app.schemas.geofence import (
    GeofenceCreateRequest,
    GeofencePage,
    GeofenceResponse,
    GeofenceUpdateRequest,
)

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


@router.post("/geofences", response_model=GeofenceResponse, status_code=status.HTTP_201_CREATED)
def create_geofence(
    payload: GeofenceCreateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.create", "scenarios.write")),
):
    now = datetime.now(UTC).replace(tzinfo=None)
    geofence = Geofence(
        id=payload.id or str(uuid4()),
        name=payload.name,
        enabled=payload.enabled,
        geometry=payload.geometry,
        min_altitude=float(payload.min_altitude) if payload.min_altitude is not None else None,
        max_altitude=float(payload.max_altitude) if payload.max_altitude is not None else None,
        metadata_json=payload.metadata,
        created_at=now,
        updated_at=now,
    )
    db.add(geofence)
    db.commit()
    db.refresh(geofence)
    return GeofenceResponse.model_validate(geofence)


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


@router.put("/geofences/{geofence_id}", response_model=GeofenceResponse)
def update_geofence(
    geofence_id: str,
    payload: GeofenceUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.update", "scenarios.write")),
):
    geofence = db.get(Geofence, geofence_id)
    if geofence is None:
        raise HTTPException(status_code=404, detail="Geofence not found")

    if payload.name is not None:
        geofence.name = payload.name
    if payload.enabled is not None:
        geofence.enabled = payload.enabled
    if payload.geometry is not None:
        geofence.geometry = payload.geometry
    if payload.min_altitude is not None:
        geofence.min_altitude = float(payload.min_altitude)
    if payload.max_altitude is not None:
        geofence.max_altitude = float(payload.max_altitude)
    if payload.metadata is not None:
        geofence.metadata_json = payload.metadata

    geofence.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(geofence)
    return GeofenceResponse.model_validate(geofence)


@router.delete("/geofences/{geofence_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_geofence(
    geofence_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.delete", "scenarios.write")),
):
    geofence = db.get(Geofence, geofence_id)
    if geofence is None:
        raise HTTPException(status_code=404, detail="Geofence not found")

    db.delete(geofence)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
