"""Defensive intelligence query API endpoints — Stage AI3-D."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from ai.incremental.pipeline import get_intelligence_pipeline
from ai.schemas import MultiTrackIntelligenceSummary
from app.database.session import get_db
from app.dependencies import require_permission
from app.models.user import User

router = APIRouter()


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

    Reads instantly from the authoritative in-memory IncrementalIntelligenceStore snapshot in O(1) time
    with zero full-population batch recomputation.
    """
    pipeline = get_intelligence_pipeline()
    return pipeline.get_snapshot(
        db=db,
        track_id=track_id,
        group_id=group_id,
        min_priority_level=min_priority_level,
        min_priority_score=min_priority_score,
    )
