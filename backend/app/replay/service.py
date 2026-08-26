"""Replay service coordinating execution snapshots and comparisons."""

from sqlalchemy.orm import Session

from app.replay.comparison import compare_replay_runs
from app.replay.engine import ReplayEngine
from app.replay.models import ReplayConfig
from app.schemas.replay import (
    ReplayComparisonReport,
    ReplayComparisonRequest,
    ReplayRequest,
    ReplaySnapshot,
    ReplayStepRequest,
)


class ReplayService:
    def __init__(self, db: Session):
        self.db = db

    def query_snapshot(self, request: ReplayRequest) -> ReplaySnapshot:
        """Generate a replay snapshot at the start time of the requested window."""
        config = ReplayConfig.from_request(request)
        engine = ReplayEngine(self.db, config)
        return engine.get_snapshot_at(config.start_time, step_idx=0)

    def step_replay(self, request: ReplayStepRequest) -> ReplaySnapshot:
        """Advance replay state by the requested step count from current_time."""
        replay_req = ReplayRequest(
            start_time=request.start_time,
            end_time=request.end_time,
            step_interval_seconds=request.step_interval_seconds,
            filters=request.filters,
        )
        config = ReplayConfig.from_request(replay_req)
        engine = ReplayEngine(self.db, config)
        # Calculate current step offset from start_time
        dt_seconds = config.step_interval_seconds
        elapsed_seconds = (request.current_time - request.start_time).total_seconds()
        current_step = max(0, int(elapsed_seconds / dt_seconds)) if dt_seconds > 0 else 0
        target_step = current_step + request.steps
        target_time = request.start_time + (target_step * engine.dt)
        if target_time > request.end_time:
            target_time = request.end_time

        return engine.get_snapshot_at(target_time, step_idx=target_step)

    def compare_runs(self, request: ReplayComparisonRequest) -> ReplayComparisonReport:
        """Compare two replay runs on canonical operational values."""
        return compare_replay_runs(self.db, request)
