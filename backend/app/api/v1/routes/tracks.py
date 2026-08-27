"""Track query and history API endpoints."""

import base64
import json
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.track import Track, TrackHistory, TrackState
from app.models.user import User
from app.schemas.track import TrackHistoryPage, TrackHistoryResponse, TrackPage, TrackResponse

router = APIRouter()


def _decode_cursor(value: str | None) -> tuple[datetime, str] | None:
    if not value:
        return None
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        timestamp = datetime.fromisoformat(decoded[0])
        track_id = str(decoded[1])
        if len(track_id) != 36:
            raise ValueError
        return timestamp, track_id
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(status_code=400, detail="Invalid track cursor") from None


def _encode_cursor(track: Track) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([track.last_seen_at.isoformat(), track.id], separators=(",", ":")).encode()
    ).decode().rstrip("=")


def _decode_history_cursor(value: str | None) -> int | None:
    if not value:
        return None
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        seq = int(decoded[0])
        if seq < 0:
            raise ValueError
        return seq
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(status_code=400, detail="Invalid track history cursor") from None


def _encode_history_cursor(entry: TrackHistory) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([entry.sequence], separators=(",", ":")).encode()
    ).decode().rstrip("=")


@router.get("/tracks", response_model=TrackPage)
def list_tracks(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
    state: TrackState | None = Query(None),
    classification: str | None = Query(None, max_length=64),
    last_seen_from: datetime | None = None,
    last_seen_to: datetime | None = None,
    cursor: str | None = Query(None, max_length=256),
    limit: int = Query(50, ge=1, le=100),
):
    if last_seen_from and last_seen_to and last_seen_from > last_seen_to:
        raise HTTPException(status_code=400, detail="last_seen_from must not be after last_seen_to")

    statement = select(Track)
    if state:
        statement = statement.where(Track.state == state)
    if classification:
        statement = statement.where(Track.classification == classification)
    if last_seen_from:
        statement = statement.where(Track.last_seen_at >= last_seen_from.replace(tzinfo=None))
    if last_seen_to:
        statement = statement.where(Track.last_seen_at <= last_seen_to.replace(tzinfo=None))

    decoded = _decode_cursor(cursor)
    if decoded:
        statement = statement.where(
            or_(
                Track.last_seen_at < decoded[0],
                and_(Track.last_seen_at == decoded[0], Track.id < decoded[1]),
            )
        )

    tracks = db.scalars(
        statement.order_by(Track.last_seen_at.desc(), Track.id.desc()).limit(limit + 1)
    ).all()

    next_cursor = _encode_cursor(tracks[limit - 1]) if len(tracks) > limit else None
    return TrackPage(
        items=[TrackResponse.model_validate(t) for t in tracks[:limit]],
        next_cursor=next_cursor,
    )


@router.get("/tracks/{track_id}", response_model=TrackResponse)
def get_track(
    track_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
):
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return TrackResponse.model_validate(track)


@router.get("/tracks/{track_id}/history", response_model=TrackHistoryPage)
def get_track_history(
    track_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
    sequence_from: int | None = Query(None, ge=0),
    cursor: str | None = Query(None, max_length=256),
    limit: int = Query(50, ge=1, le=100),
):
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    statement = select(TrackHistory).where(TrackHistory.track_id == track_id)
    if sequence_from is not None:
        statement = statement.where(TrackHistory.sequence >= sequence_from)

    decoded_seq = _decode_history_cursor(cursor)
    if decoded_seq is not None:
        statement = statement.where(TrackHistory.sequence > decoded_seq)

    history_entries = db.scalars(
        statement.order_by(TrackHistory.sequence.asc()).limit(limit + 1)
    ).all()

    next_cursor = (
        _encode_history_cursor(history_entries[limit - 1])
        if len(history_entries) > limit
        else None
    )

    return TrackHistoryPage(
        items=[TrackHistoryResponse.model_validate(h) for h in history_entries[:limit]],
        next_cursor=next_cursor,
    )


@router.get("/tracks/{track_id}/intelligence")
def get_track_intelligence(
    track_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
):
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")

    from ai.service import DefensiveIntelligenceService

    summary = DefensiveIntelligenceService.evaluate_track(db, track, publish_events=False)
    if summary is None:
        raise HTTPException(
            status_code=500,
            detail="Failed to evaluate defensive intelligence for track",
        )
    return summary
