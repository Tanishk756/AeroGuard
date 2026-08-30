"""Stage PR1-B Automated Scheduler Status REST API Route."""

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.dependencies import require_permission
from app.models.scheduler import SchedulerLock
from app.models.user import User
from app.schemas.scheduler import JobStatusResponse, SchedulerStatusResponse
from app.services.scheduler import AeroGuardOperationalScheduler, get_scheduler

router = APIRouter()


@router.get("/scheduler/status", response_model=SchedulerStatusResponse)
def get_scheduler_status(
    user: User = Depends(require_permission("incidents.read")),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
    scheduler: AeroGuardOperationalScheduler = Depends(get_scheduler),
):
    """Retrieve operational background scheduler state and registered job history."""
    locks = list(db.scalars(select(SchedulerLock).order_by(SchedulerLock.job_name.asc())).all())
    known_jobs = {
        AeroGuardOperationalScheduler.JOB_RETENTION,
        AeroGuardOperationalScheduler.JOB_INTEGRITY,
        AeroGuardOperationalScheduler.JOB_SESSION_CLEANUP,
    }

    lock_map = {lock.job_name: lock for lock in locks}
    job_responses: list[JobStatusResponse] = []

    for job_name in sorted(known_jobs):
        lock = lock_map.get(job_name)
        if lock:
            job_responses.append(
                JobStatusResponse(
                    job_name=lock.job_name,
                    last_run_at=lock.last_run_at,
                    last_status=lock.last_status or "IDLE",
                    last_duration_ms=lock.last_duration_ms,
                    records_processed=lock.records_processed,
                    error_message=lock.error_message,
                    retry_count=lock.retry_count,
                    locked_by=lock.locked_by,
                    expires_at=lock.expires_at,
                )
            )
        else:
            job_responses.append(
                JobStatusResponse(
                    job_name=job_name,
                    last_status="IDLE",
                    records_processed=0,
                    retry_count=0,
                )
            )

    return SchedulerStatusResponse(
        enabled=settings.scheduler_enabled,
        running=scheduler.running,
        worker_id=scheduler.worker_id,
        jobs=job_responses,
    )
