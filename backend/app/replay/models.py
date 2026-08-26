"""Domain models for historical replay."""

from datetime import UTC, datetime
from typing import NamedTuple

from app.history.queries import normalize_timestamp
from app.schemas.replay import ReplayFilter, ReplayRequest


class ReplayConfig(NamedTuple):
    start_time: datetime
    end_time: datetime
    step_interval_seconds: float
    filters: ReplayFilter

    @classmethod
    def from_request(cls, req: ReplayRequest) -> "ReplayConfig":
        norm_start = normalize_timestamp(req.start_time)
        norm_end = normalize_timestamp(req.end_time)
        if norm_start > norm_end:
            raise ValueError("start_time must be less than or equal to end_time")
        return cls(
            start_time=norm_start,
            end_time=norm_end,
            step_interval_seconds=float(req.step_interval_seconds),
            filters=req.filters,
        )
