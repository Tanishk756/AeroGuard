"""Defensive intelligence query API endpoints — Stage AI2-F."""

from datetime import UTC, datetime
from typing import Any

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.schemas import MultiTrackIntelligenceSummary
from ai.service import DefensiveIntelligenceService
from app.database.session import get_db
from app.dependencies import require_permission
from app.models.track import Track, TrackState
from app.models.user import User

router = APIRouter()

PRIORITY_LEVEL_ORDER = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


@router.get("/intelligence/summary", response_model=MultiTrackIntelligenceSummary)
def get_multi_track_intelligence_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("tracks.read")),
    track_id: str | None = Query(None, min_length=1, max_length=64),
    group_id: str | None = Query(None, min_length=1, max_length=64),
    min_priority_level: str | None = Query(None, pattern="^(LOW|MEDIUM|HIGH|CRITICAL)$"),
    min_priority_score: float | None = Query(None, ge=0.0, le=100.0),
) -> MultiTrackIntelligenceSummary:
    """Retrieve aggregate defensive multi-track intelligence summary across active airspace tracks.

    Combines spatial grouping (AI2-B), behavioral classification (AI2-C),
    formation coordination (AI2-D), and explainable threat prioritization (AI2-E).
    """
    # 1. Fetch active tracks from authoritative operational database
    tracks_stmt = select(Track).where(
        Track.state.in_([TrackState.ACTIVE, TrackState.NEW, TrackState.STALE])
    )
    active_tracks = list(db.scalars(tracks_stmt).all())

    # 2. Evaluate multi-track intelligence
    summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(
        active_tracks,
        publish_events=False,
    )

    # 3. Apply optional filters
    groups = summary.groups
    formations = summary.formations
    behaviors = summary.behaviors
    priorities = summary.priorities

    if track_id:
        groups = [g for g in groups if track_id in g.member_track_ids]
        formations = [f for f in formations if track_id in f.member_track_ids]
        behaviors = [b for b in behaviors if b.track_id == track_id]
        priorities = [p for p in priorities if p.track_id == track_id]

    if group_id:
        groups = [g for g in groups if g.group_id == group_id]
        formations = [f for f in formations if f.group_id == group_id]
        member_ids = {mid for g in groups for mid in g.member_track_ids}
        behaviors = [b for b in behaviors if b.track_id in member_ids]
        priorities = [p for p in priorities if p.track_id in member_ids]

    if min_priority_score is not None:
        priorities = [p for p in priorities if p.priority_score >= min_priority_score]

    if min_priority_level:
        target_rank = PRIORITY_LEVEL_ORDER.get(min_priority_level.upper(), 0)
        priorities = [
            p for p in priorities
            if PRIORITY_LEVEL_ORDER.get(p.priority_level, 0) >= target_rank
        ]

    return MultiTrackIntelligenceSummary(
        groups=groups,
        behaviors=behaviors,
        formations=formations,
        priorities=priorities,
        evaluated_at=summary.evaluated_at,
    )
