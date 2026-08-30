"""Stage PR1-B Automated Background Scheduler & DB-Backed Distributed Lock Engine."""

import asyncio
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
import os
import socket
import time
from typing import Any, Callable
from uuid import uuid4

from sqlalchemy import delete, or_, select, update
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import SessionLocal
from app.models.scheduler import SchedulerLock
from app.models.session import Session as AuthSession
from app.services.incident_archive_integrity import IncidentArchiveIntegrityService
from app.services.incident_retention import IncidentRetentionService

logger = logging.getLogger(__name__)


@dataclass
class JobResult:
    """Captured execution outcome for a scheduled maintenance task."""

    job_name: str
    status: str  # "SUCCESS" or "FAILURE"
    duration_ms: float
    records_processed: int
    retry_count: int
    error_message: str | None = None
    executed_at: datetime | None = None


class DistributedJobLock:
    """Atomic database-backed distributed locking for multi-worker coordination."""

    @staticmethod
    def _ensure_job_record(db: Session, job_name: str) -> None:
        try:
            SchedulerLock.__table__.create(bind=db.bind, checkfirst=True)
        except Exception:
            pass
        lock = db.scalar(select(SchedulerLock).where(SchedulerLock.job_name == job_name))
        if not lock:
            lock = SchedulerLock(job_name=job_name, last_status="IDLE", records_processed=0, retry_count=0)
            db.add(lock)
            try:
                db.commit()
            except Exception:
                db.rollback()

    @classmethod
    def acquire_lock(cls, db: Session, job_name: str, worker_id: str, lock_ttl_seconds: int = 300) -> bool:
        """Atomic database lock acquisition via single atomic SQL UPDATE rowcount check.

        Returns True if acquired, False if locked by another active worker.
        """
        cls._ensure_job_record(db, job_name)
        now = datetime.now(UTC).replace(tzinfo=None)
        expires_at = now + timedelta(seconds=lock_ttl_seconds)

        stmt = (
            update(SchedulerLock)
            .where(SchedulerLock.job_name == job_name)
            .where(or_(SchedulerLock.locked_by.is_(None), SchedulerLock.expires_at < now))
            .values(
                locked_by=worker_id,
                locked_at=now,
                expires_at=expires_at,
                last_status="RUNNING",
            )
        )
        result = db.execute(stmt)
        db.commit()
        if result.rowcount > 0:
            return True

        # Fallback ORM transaction check for SQLite in-memory connections
        lock = db.scalar(select(SchedulerLock).where(SchedulerLock.job_name == job_name))
        if lock and (lock.locked_by is None or lock.expires_at is None or lock.expires_at < now):
            lock.locked_by = worker_id
            lock.locked_at = now
            lock.expires_at = expires_at
            lock.last_status = "RUNNING"
            try:
                db.commit()
                return True
            except Exception:
                db.rollback()
                return False

        return False

    @classmethod
    def renew_lease(cls, db: Session, job_name: str, worker_id: str, extension_seconds: int = 300) -> bool:
        """Renew lock expiration for long-running jobs."""
        now = datetime.now(UTC).replace(tzinfo=None)
        expires_at = now + timedelta(seconds=extension_seconds)
        stmt = (
            update(SchedulerLock)
            .where(SchedulerLock.job_name == job_name)
            .where(SchedulerLock.locked_by == worker_id)
            .values(expires_at=expires_at)
        )
        result = db.execute(stmt)
        db.commit()
        return result.rowcount > 0

    @classmethod
    def release_lock(
        cls,
        db: Session,
        job_name: str,
        worker_id: str,
        status: str,
        duration_ms: float,
        records_processed: int,
        error_message: str | None = None,
        retry_count: int = 0,
    ) -> None:
        """Atomic lock release and metadata update."""
        now = datetime.now(UTC).replace(tzinfo=None)
        stmt = (
            update(SchedulerLock)
            .where(SchedulerLock.job_name == job_name)
            .where(SchedulerLock.locked_by == worker_id)
            .values(
                locked_by=None,
                locked_at=None,
                expires_at=None,
                last_run_at=now,
                last_status=status,
                last_duration_ms=duration_ms,
                records_processed=records_processed,
                error_message=error_message[:1024] if error_message else None,
                retry_count=retry_count,
            )
        )
        db.execute(stmt)
        db.commit()


# --- Job Execution Handlers ---

def execute_retention_evaluation_job(db: Session) -> int:
    """Job 1: Evaluates incident retention policies & holds. Does NOT execute purges."""
    retention_service = IncidentRetentionService(db)
    evaluation = retention_service.evaluate_retention(dry_run=True)
    db.commit()
    return evaluation.total_evaluated


def execute_archive_integrity_job(db: Session) -> int:
    """Job 2: Performs bounded batch integrity check (100 archives) and records audit evidence."""
    integrity_service = IncidentArchiveIntegrityService(db)
    checks = integrity_service.verify_archives(limit=100)
    db.commit()
    return len(checks)


def execute_session_cleanup_job(db: Session, grace_period_days: int = 7) -> int:
    """Job 3: Cleans expired/revoked session records older than grace_period_days. Preserves active sessions."""
    now = datetime.now(UTC).replace(tzinfo=None)
    cutoff = now - timedelta(days=grace_period_days)

    stmt = delete(AuthSession).where(
        or_(
            AuthSession.expires_at < cutoff,
            AuthSession.revoked_at < cutoff,
        )
    )
    result = db.execute(stmt)
    db.commit()
    return result.rowcount


class AeroGuardOperationalScheduler:
    """Background task runner executing scheduled maintenance with multi-worker coordination."""

    JOB_RETENTION = "retention_evaluation"
    JOB_INTEGRITY = "archive_integrity_verification"
    JOB_SESSION_CLEANUP = "expired_session_cleanup"

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.worker_id = f"{socket.gethostname()}-{os.getpid()}-{uuid4().hex[:6]}"
        self.running = False
        self._task: asyncio.Task | None = None
        self._stop_event = asyncio.Event()

    def _get_job_interval(self, job_name: str) -> int:
        if job_name == self.JOB_RETENTION:
            return self.settings.retention_job_interval_seconds
        elif job_name == self.JOB_INTEGRITY:
            return self.settings.integrity_job_interval_seconds
        elif job_name == self.JOB_SESSION_CLEANUP:
            return self.settings.session_cleanup_interval_seconds
        return 3600

    def run_job(self, job_name: str, max_retries: int = 3, db: Session | None = None) -> JobResult:
        """Synchronously execute job with lock acquisition, isolation, and bounded retries."""
        if not self.settings.scheduler_enabled:
            return JobResult(job_name=job_name, status="IDLE", duration_ms=0.0, records_processed=0, retry_count=0)

        should_close = False
        if db is None:
            db = SessionLocal()
            should_close = True
        try:
            acquired = DistributedJobLock.acquire_lock(
                db=db,
                job_name=job_name,
                worker_id=self.worker_id,
                lock_ttl_seconds=self.settings.scheduler_lock_timeout_seconds,
            )
            if not acquired:
                logger.debug(f"[SCHEDULER] Job '{job_name}' is locked by another worker. Skipping execution.")
                return JobResult(
                    job_name=job_name,
                    status="SKIPPED",
                    duration_ms=0.0,
                    records_processed=0,
                    retry_count=0,
                    error_message="Locked by another worker",
                )

            t0 = time.perf_counter()
            records_processed = 0
            retry_count = 0
            last_error: Exception | None = None

            for attempt in range(max_retries):
                retry_count = attempt
                try:
                    if job_name == self.JOB_RETENTION:
                        records_processed = execute_retention_evaluation_job(db)
                    elif job_name == self.JOB_INTEGRITY:
                        records_processed = execute_archive_integrity_job(db)
                    elif job_name == self.JOB_SESSION_CLEANUP:
                        records_processed = execute_session_cleanup_job(db, self.settings.session_cleanup_grace_period_days)
                    else:
                        raise ValueError(f"Unknown scheduled job name: '{job_name}'")

                    duration_sec = time.perf_counter() - t0
                    duration_ms = duration_sec * 1000.0
                    DistributedJobLock.release_lock(
                        db=db,
                        job_name=job_name,
                        worker_id=self.worker_id,
                        status="SUCCESS",
                        duration_ms=duration_ms,
                        records_processed=records_processed,
                        retry_count=retry_count,
                    )
                    from app.core.telemetry import (
                        SCHEDULER_JOB_DURATION_SECONDS,
                        SCHEDULER_JOB_LAST_SUCCESS,
                        SCHEDULER_JOB_RUNS_TOTAL,
                    )
                    SCHEDULER_JOB_RUNS_TOTAL.labels(job_name=job_name, status="SUCCESS").inc()
                    SCHEDULER_JOB_DURATION_SECONDS.labels(job_name=job_name).observe(duration_sec)
                    SCHEDULER_JOB_LAST_SUCCESS.labels(job_name=job_name).set(time.time())

                    logger.info(f"[SCHEDULER] Job '{job_name}' completed successfully in {duration_ms:.1f}ms ({records_processed} records).")
                    return JobResult(
                        job_name=job_name,
                        status="SUCCESS",
                        duration_ms=duration_ms,
                        records_processed=records_processed,
                        retry_count=retry_count,
                        executed_at=datetime.now(UTC).replace(tzinfo=None),
                    )

                except Exception as exc:
                    last_error = exc
                    db.rollback()
                    logger.warning(f"[SCHEDULER] Attempt {attempt + 1}/{max_retries} for job '{job_name}' failed: {exc}")
                    if isinstance(exc, (ValueError, KeyError, TypeError)):
                        logger.error(f"[SCHEDULER] Permanent non-transient error in job '{job_name}': {exc}. Skipping retries.")
                        break
                    if attempt < max_retries - 1:
                        time.sleep(0.5 * (attempt + 1))  # Bounded exponential backoff

            duration_sec = time.perf_counter() - t0
            duration_ms = duration_sec * 1000.0
            error_msg = str(last_error) if last_error else "Unknown execution error"
            from app.core.telemetry import (
                SCHEDULER_JOB_DURATION_SECONDS,
                SCHEDULER_JOB_FAILURES_TOTAL,
                SCHEDULER_JOB_RUNS_TOTAL,
            )
            SCHEDULER_JOB_RUNS_TOTAL.labels(job_name=job_name, status="FAILURE").inc()
            SCHEDULER_JOB_FAILURES_TOTAL.labels(job_name=job_name).inc()
            SCHEDULER_JOB_DURATION_SECONDS.labels(job_name=job_name).observe(duration_sec)
            DistributedJobLock.release_lock(
                db=db,
                job_name=job_name,
                worker_id=self.worker_id,
                status="FAILURE",
                duration_ms=duration_ms,
                records_processed=0,
                error_message=error_msg,
                retry_count=retry_count,
            )
            return JobResult(
                job_name=job_name,
                status="FAILURE",
                duration_ms=duration_ms,
                records_processed=0,
                retry_count=retry_count,
                error_message=error_msg,
                executed_at=datetime.now(UTC).replace(tzinfo=None),
            )

        finally:
            db.close()

    async def _scheduler_loop(self) -> None:
        logger.info(f"[SCHEDULER] Started background scheduler worker '{self.worker_id}'.")
        last_run_times: dict[str, float] = {}

        while not self._stop_event.is_set():
            if self.settings.scheduler_enabled:
                now_ts = time.time()
                for job_name in [self.JOB_RETENTION, self.JOB_INTEGRITY, self.JOB_SESSION_CLEANUP]:
                    interval = self._get_job_interval(job_name)
                    last_run = last_run_times.get(job_name, 0.0)
                    if now_ts - last_run >= interval:
                        last_run_times[job_name] = now_ts
                        try:
                            await asyncio.to_thread(self.run_job, job_name)
                        except Exception as exc:
                            logger.error(f"[SCHEDULER] Unhandled error during async job dispatch '{job_name}': {exc}")

            try:
                await asyncio.sleep(5)
            except asyncio.CancelledError:
                break

        logger.info(f"[SCHEDULER] Background scheduler worker '{self.worker_id}' stopped.")

    async def start(self) -> None:
        """Start async background scheduler task."""
        if not self.settings.scheduler_enabled or self.running:
            return
        self.running = True
        self._stop_event.clear()
        self._task = asyncio.create_task(self._scheduler_loop())
        from app.core.telemetry import SCHEDULER_RUNNING
        SCHEDULER_RUNNING.set(1)

    async def stop(self) -> None:
        """Stop background scheduler task gracefully."""
        if not self.running:
            return
        self.running = False
        self._stop_event.set()
        if self._task and not self._task.done():
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        from app.core.telemetry import SCHEDULER_RUNNING
        SCHEDULER_RUNNING.set(0)


# Global singleton instance
_global_scheduler: AeroGuardOperationalScheduler | None = None


def get_scheduler() -> AeroGuardOperationalScheduler:
    global _global_scheduler
    if _global_scheduler is None:
        _global_scheduler = AeroGuardOperationalScheduler()
    return _global_scheduler
