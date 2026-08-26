"""REST API routes for stateless deterministic historical replay and comparison."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_any_permission
from app.models.user import User
from app.replay.service import ReplayService
from app.schemas.replay import (
    ReplayComparisonReport,
    ReplayComparisonRequest,
    ReplayRequest,
    ReplaySnapshot,
    ReplayStepRequest,
)

router = APIRouter(prefix="/replay", tags=["replay"])


@router.post("/query", response_model=ReplaySnapshot)
def query_replay_snapshot(
    request: ReplayRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.read", "tracks.read", "scenarios.run")),
) -> ReplaySnapshot:
    try:
        service = ReplayService(db)
        return service.query_snapshot(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/step", response_model=ReplaySnapshot)
def step_replay_snapshot(
    request: ReplayStepRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.read", "tracks.read", "scenarios.run")),
) -> ReplaySnapshot:
    try:
        service = ReplayService(db)
        return service.step_replay(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e


@router.post("/compare", response_model=ReplayComparisonReport)
def compare_replay_histories(
    request: ReplayComparisonRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.read", "tracks.read", "scenarios.run")),
) -> ReplayComparisonReport:
    try:
        service = ReplayService(db)
        return service.compare_runs(request)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from e
