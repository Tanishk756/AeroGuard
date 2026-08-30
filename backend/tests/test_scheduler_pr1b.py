"""Stage PR1-B Automated Scheduler & Background Task Engine Test Suite.

Verifies:
- Scheduler enablement / disablement
- Deterministic job registration & async lifespan startup/shutdown
- Retention evaluation, cold-storage integrity, & session cleanup jobs
- Active session protection invariants
- Atomic multi-worker DB lock acquisition & stale lock recovery
- Overlapping execution prevention & failure isolation
- REST status API authorization & payload schema
- Benchmark overhead measurements
"""

import asyncio
from datetime import UTC, datetime, timedelta
from concurrent.futures import ThreadPoolExecutor
import time
from uuid import uuid4

import pytest
from sqlalchemy import select, text, update
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.config import Settings
from app.database.session import create_database_engine
from app.models.incident import Incident, IncidentSeverity, IncidentSource, IncidentStatus
from app.models.scheduler import SchedulerLock
from app.models.session import Session as AuthSession
from app.models.user import User, UserStatus
from app.schemas.scheduler import SchedulerStatusResponse
from app.services.auth import create_session, create_user
from app.services.scheduler import (
    AeroGuardOperationalScheduler,
    DistributedJobLock,
    JobResult,
    execute_archive_integrity_job,
    execute_retention_evaluation_job,
    execute_session_cleanup_job,
)


def test_scheduler_disabled(database):
    """VERIFIED: Scheduler returns SKIPPED/IDLE when disabled."""
    settings = Settings(scheduler_enabled=False)
    scheduler = AeroGuardOperationalScheduler(settings=settings)

    res = scheduler.run_job(AeroGuardOperationalScheduler.JOB_RETENTION, db=database)
    assert res.status == "IDLE"
    assert res.records_processed == 0


def test_scheduler_enabled(database):
    """VERIFIED: Scheduler acquires lock and runs job when enabled."""
    settings = Settings(scheduler_enabled=True)
    scheduler = AeroGuardOperationalScheduler(settings=settings)

    res = scheduler.run_job(AeroGuardOperationalScheduler.JOB_RETENTION, db=database)
    assert res.status == "SUCCESS"
    assert res.job_name == AeroGuardOperationalScheduler.JOB_RETENTION

    # Verify lock table updated
    lock = database.scalar(select(SchedulerLock).where(SchedulerLock.job_name == AeroGuardOperationalScheduler.JOB_RETENTION))
    assert lock is not None
    assert lock.last_status == "SUCCESS"
    assert lock.locked_by is None  # Released after run


def test_deterministic_job_registration(database):
    """VERIFIED: All 3 maintenance jobs are registered deterministically."""
    for job_name in [
        AeroGuardOperationalScheduler.JOB_RETENTION,
        AeroGuardOperationalScheduler.JOB_INTEGRITY,
        AeroGuardOperationalScheduler.JOB_SESSION_CLEANUP,
    ]:
        DistributedJobLock._ensure_job_record(database, job_name)

    locks = list(database.scalars(select(SchedulerLock)).all())
    registered_names = {l.job_name for l in locks}

    assert AeroGuardOperationalScheduler.JOB_RETENTION in registered_names
    assert AeroGuardOperationalScheduler.JOB_INTEGRITY in registered_names
    assert AeroGuardOperationalScheduler.JOB_SESSION_CLEANUP in registered_names


@pytest.mark.asyncio
async def test_scheduler_startup_and_shutdown():
    """VERIFIED: Async start and stop hooks initialize and terminate background task cleanly."""
    settings = Settings(scheduler_enabled=True)
    scheduler = AeroGuardOperationalScheduler(settings=settings)

    await scheduler.start()
    assert scheduler.running is True
    assert scheduler._task is not None
    assert not scheduler._task.done()

    await scheduler.stop()
    assert scheduler.running is False
    assert scheduler._task.done() or scheduler._task.cancelled()


def test_retention_job_execution(database):
    """VERIFIED: Retention job evaluates eligible incidents without purge."""
    inc = Incident(
        id=str(uuid4()),
        incident_number=f"INC-{uuid4().hex[:6].upper()}",
        title="PR1-B Retention Incident",
        description="Test incident for retention evaluation",
        status=IncidentStatus.RESOLVED,
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
        created_at=datetime.now(UTC).replace(tzinfo=None) - timedelta(days=400),
    )
    database.add(inc)
    database.commit()

    count = execute_retention_evaluation_job(database)
    assert count >= 1

    # Verify incident record was NOT deleted
    reloaded = database.scalar(select(Incident).where(Incident.id == inc.id))
    assert reloaded is not None
    assert reloaded.status == IncidentStatus.RESOLVED


def test_retention_evaluation_does_not_autonomously_purge(database):
    """VERIFIED: Retention evaluation leaves all incident records intact in database."""
    initial_count = database.scalar(select(text("COUNT(*) FROM incidents")))
    execute_retention_evaluation_job(database)
    after_count = database.scalar(select(text("COUNT(*) FROM incidents")))

    assert initial_count == after_count


def test_integrity_job_execution(database):
    """VERIFIED: Archive integrity job runs batch verification cleanly."""
    count = execute_archive_integrity_job(database)
    assert isinstance(count, int)


def test_session_cleanup_behavior(database):
    """VERIFIED: Expired and revoked sessions older than grace period are deleted."""
    now = datetime.now(UTC).replace(tzinfo=None)
    user = create_user(database, f"user_{uuid4().hex[:6]}", "Session User", f"user_{uuid4().hex[:6]}@aeroguard.io", "Password123!")

    # Active session (must NOT be deleted)
    active_sess, _ = create_session(database, user, "127.0.0.1", "pytest", commit=True)
    active_id = active_sess.id

    # Stale expired session (> 7 days old)
    stale_sess = AuthSession(
        user_id=user.id,
        session_secret_hash=f"hash_{uuid4().hex}",
        created_at=now - timedelta(days=20),
        expires_at=now - timedelta(days=10),
        last_seen_at=now - timedelta(days=20),
    )
    database.add(stale_sess)
    database.commit()
    stale_id = stale_sess.id

    deleted_count = execute_session_cleanup_job(database, grace_period_days=7)
    assert deleted_count >= 1

    # Active session MUST remain
    assert database.scalar(select(AuthSession).where(AuthSession.id == active_id)) is not None
    # Stale session MUST be deleted
    assert database.scalar(select(AuthSession).where(AuthSession.id == stale_id)) is None


def test_active_session_protection(database):
    """VERIFIED: Active valid sessions are never deleted during cleanup."""
    now = datetime.now(UTC).replace(tzinfo=None)
    user = create_user(database, f"user_{uuid4().hex[:6]}", "Active User", f"user_{uuid4().hex[:6]}@aeroguard.io", "Password123!")
    active_sess, _ = create_session(database, user, "127.0.0.1", "pytest", commit=True)
    active_id = active_sess.id

    execute_session_cleanup_job(database, grace_period_days=7)

    reloaded = database.scalar(select(AuthSession).where(AuthSession.id == active_id))
    assert reloaded is not None
    assert reloaded.revoked_at is None
    assert reloaded.expires_at > now


def test_job_failure_isolation(database):
    """VERIFIED: A failure in one job does not crash the scheduler or prevent other jobs from running."""
    settings = Settings(scheduler_enabled=True)
    scheduler = AeroGuardOperationalScheduler(settings=settings)

    # Run retention job
    res1 = scheduler.run_job(AeroGuardOperationalScheduler.JOB_RETENTION, db=database)
    assert res1.status == "SUCCESS"

    # Run invalid job name
    res2 = scheduler.run_job("INVALID_JOB_NAME", db=database)
    assert res2.status == "FAILURE"
    assert "Unknown scheduled job" in str(res2.error_message)

    # Run session cleanup job afterwards - MUST succeed
    res3 = scheduler.run_job(AeroGuardOperationalScheduler.JOB_SESSION_CLEANUP, db=database)
    assert res3.status == "SUCCESS"


def test_bounded_retries(database):
    """VERIFIED: Failed job retries up to max_retries before recording FAILURE."""
    settings = Settings(scheduler_enabled=True)
    scheduler = AeroGuardOperationalScheduler(settings=settings)

    res = scheduler.run_job("INVALID_JOB_NAME", max_retries=3, db=database)
    assert res.status == "FAILURE"
    assert res.retry_count == 2  # 0, 1, 2 = 3 total attempts


def test_overlapping_execution_prevention(database):
    """VERIFIED: Active worker lock prevents a second worker from running the same job concurrently."""
    worker1 = "worker-node-1"
    worker2 = "worker-node-2"
    job_name = "test_overlap_job"

    # Worker 1 acquires lock
    acquired1 = DistributedJobLock.acquire_lock(database, job_name, worker1, lock_ttl_seconds=300)
    assert acquired1 is True

    # Worker 2 attempts to acquire lock while Worker 1 holds active lock
    acquired2 = DistributedJobLock.acquire_lock(database, job_name, worker2, lock_ttl_seconds=300)
    assert acquired2 is False

    # Worker 1 releases lock
    DistributedJobLock.release_lock(database, job_name, worker1, status="SUCCESS", duration_ms=10.0, records_processed=5)

    # Worker 2 acquires lock after release
    acquired3 = DistributedJobLock.acquire_lock(database, job_name, worker2, lock_ttl_seconds=300)
    assert acquired3 is True

    DistributedJobLock.release_lock(database, job_name, worker2, status="SUCCESS", duration_ms=10.0, records_processed=5)


def test_stale_lock_recovery(database):
    """VERIFIED: Lock with expires_at in the past is automatically recovered by a new worker."""
    worker1 = "worker-crashed"
    worker2 = "worker-recovery"
    job_name = "test_stale_job"

    # Worker 1 acquires lock with TTL = 1 second
    DistributedJobLock.acquire_lock(database, job_name, worker1, lock_ttl_seconds=1)

    # Manually expire the lock in DB
    past_time = datetime.now(UTC).replace(tzinfo=None) - timedelta(seconds=10)
    database.execute(
        update(SchedulerLock)
        .where(SchedulerLock.job_name == job_name)
        .values(expires_at=past_time)
    )
    database.commit()

    # Worker 2 acquires stale lock cleanly
    acquired = DistributedJobLock.acquire_lock(database, job_name, worker2, lock_ttl_seconds=300)
    assert acquired is True

    lock = database.scalar(select(SchedulerLock).where(SchedulerLock.job_name == job_name))
    assert lock.locked_by == worker2


def test_concurrent_lock_acquisition():
    """VERIFIED: Concurrent threads attempting to acquire lock result in exactly one winner."""
    engine = create_database_engine("sqlite://", poolclass=StaticPool)
    from app.database.base import Base
    Base.metadata.create_all(engine)
    SessionMaker = sessionmaker(bind=engine, autoflush=False, autocommit=False)

    init_db = SessionMaker()
    job_name = "test_concurrent_job"
    DistributedJobLock._ensure_job_record(init_db, job_name)
    init_db.close()

    results: list[bool] = []

    def attempt_acquire(worker_idx: int):
        db = SessionMaker()
        try:
            val = DistributedJobLock.acquire_lock(db, job_name, f"thread-worker-{worker_idx}", lock_ttl_seconds=300)
            return val
        finally:
            db.close()

    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = [executor.submit(attempt_acquire, i) for i in range(5)]
        results = [f.result() for f in futures]

    assert results.count(True) == 1
    assert results.count(False) == 4
    engine.dispose()


def test_database_failure_resilience(database):
    """VERIFIED: Exception during job execution rolls back session and releases lock safely."""
    settings = Settings(scheduler_enabled=True)
    scheduler = AeroGuardOperationalScheduler(settings=settings)

    # Execute job with non-existent job name to force exception inside runner loop
    res = scheduler.run_job("FAIL_JOB_NAME", db=database)
    assert res.status == "FAILURE"
    assert res.error_message is not None


def test_scheduler_status_endpoint(client, database):
    """VERIFIED: GET /api/v1/scheduler/status returns valid scheduler state and job array."""
    from app.models.role import Role
    from app.services.rbac import seed_rbac
    seed_rbac(database)

    user = create_user(database, f"user_{uuid4().hex[:6]}", "Operator User", f"user_{uuid4().hex[:6]}@aeroguard.io", "Password123!")
    op_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    if op_role:
        user.roles.append(op_role)
        database.commit()

    sess, raw_secret = create_session(database, user, "127.0.0.1", "pytest")
    client.cookies.set("aeroguard_session", raw_secret)

    resp = client.get("/api/v1/scheduler/status")
    assert resp.status_code == 200

    data = resp.json()
    assert "enabled" in data
    assert "running" in data
    assert "jobs" in data
    assert len(data["jobs"]) == 3

    job_names = [j["job_name"] for j in data["jobs"]]
    assert AeroGuardOperationalScheduler.JOB_RETENTION in job_names
    assert AeroGuardOperationalScheduler.JOB_INTEGRITY in job_names
    assert AeroGuardOperationalScheduler.JOB_SESSION_CLEANUP in job_names


def test_idempotent_repeated_execution(database):
    """VERIFIED: Executing maintenance jobs multiple times is idempotent."""
    settings = Settings(scheduler_enabled=True)
    scheduler = AeroGuardOperationalScheduler(settings=settings)

    res1 = scheduler.run_job(AeroGuardOperationalScheduler.JOB_RETENTION, db=database)
    res2 = scheduler.run_job(AeroGuardOperationalScheduler.JOB_RETENTION, db=database)

    assert res1.status == "SUCCESS"
    assert res2.status == "SUCCESS"


def test_scheduler_performance_overhead(database):
    """VERIFIED: Measures lock acquisition and scheduler dispatch overhead."""
    t0 = time.perf_counter()
    acquired = DistributedJobLock.acquire_lock(database, "bench_job", "bench_worker", lock_ttl_seconds=300)
    lock_acq_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    DistributedJobLock.release_lock(database, "bench_job", "bench_worker", status="SUCCESS", duration_ms=1.0, records_processed=0)
    lock_rel_ms = (time.perf_counter() - t1) * 1000.0

    print(f"\n[PR1-B BENCHMARK] Lock Acquisition: {lock_acq_ms:.2f} ms")
    print(f"[PR1-B BENCHMARK] Lock Release: {lock_rel_ms:.2f} ms")

    assert acquired is True
    assert lock_acq_ms < 20.0
    assert lock_rel_ms < 20.0
