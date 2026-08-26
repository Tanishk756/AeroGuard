"""Operational threat assessment query API endpoints."""

import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.user import User
from app.schemas.threat import ThreatAssessmentPage, ThreatAssessmentResponse

router = APIRouter()


def _decode_cursor(value: str | None) -> tuple[datetime, str] | None:
    if not value:
        return None
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        timestamp = datetime.fromisoformat(decoded[0])
        threat_id = str(decoded[1])
        if not (1 <= len(threat_id) <= 64):
            raise ValueError
        return timestamp, threat_id
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(status_code=400, detail="Invalid threat cursor") from None


def _encode_cursor(threat: ThreatAssessment) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([threat.updated_at.isoformat(), threat.id], separators=(",", ":")).encode()
    ).decode().rstrip("=")


@router.get("/threats", response_model=ThreatAssessmentPage)
def list_threats(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("threats.read")),
    level: ThreatLevel | None = Query(None),
    min_score: float | None = Query(None, ge=0.0, le=100.0),
    cursor: str | None = Query(None, max_length=256),
    limit: int = Query(50, ge=1, le=100),
):
    statement = select(ThreatAssessment)
    if level:
        statement = statement.where(ThreatAssessment.level == level)
    if min_score is not None:
        statement = statement.where(ThreatAssessment.score >= min_score)

    decoded = _decode_cursor(cursor)
    if decoded:
        statement = statement.where(
            or_(
                ThreatAssessment.updated_at < decoded[0],
                and_(ThreatAssessment.updated_at == decoded[0], ThreatAssessment.id < decoded[1]),
            )
        )

    threats = db.scalars(
        statement.order_by(ThreatAssessment.updated_at.desc(), ThreatAssessment.id.desc()).limit(limit + 1)
    ).all()

    next_cursor = _encode_cursor(threats[limit - 1]) if len(threats) > limit else None
    return ThreatAssessmentPage(
        items=[ThreatAssessmentResponse.model_validate(t) for t in threats[:limit]],
        next_cursor=next_cursor,
    )


@router.get("/threats/{track_id}", response_model=ThreatAssessmentResponse)
def get_threat_by_track(
    track_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("threats.read")),
):
    threat = db.scalar(
        select(ThreatAssessment).where(ThreatAssessment.track_id == track_id)
    )
    if threat is None:
        raise HTTPException(status_code=404, detail="Threat assessment not found for track")
    return ThreatAssessmentResponse.model_validate(threat)
