"""Pydantic schemas for Stage PR1-B Automated Scheduler Status & Job State."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class JobStatusResponse(BaseModel):
    """Schema representing execution state and metadata for a single scheduled job."""

    job_name: str
    last_run_at: datetime | None = None
    last_status: Literal["IDLE", "RUNNING", "SUCCESS", "FAILURE"] = "IDLE"
    last_duration_ms: float | None = None
    records_processed: int = 0
    error_message: str | None = None
    retry_count: int = 0
    locked_by: str | None = None
    expires_at: datetime | None = None


class SchedulerStatusResponse(BaseModel):
    """Schema representing overall application background scheduler status."""

    enabled: bool
    running: bool
    worker_id: str
    jobs: list[JobStatusResponse] = Field(default_factory=list)
