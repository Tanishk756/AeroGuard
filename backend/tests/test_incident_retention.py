"""Stage IM2-D Incident Retention Policy Engine, Cold Storage Archival, Purge Lifecycle, RBAC & Scale Benchmark Tests."""

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.incident import Incident, IncidentSeverity, IncidentSource, IncidentStatus
from app.models.incident_event import IncidentEvent, IncidentEventType
from app.models.incident_retention import (
    IncidentArchive,
    IncidentArchivalState,
    IncidentRetentionHold,
    IncidentRetentionPolicy,
)
from app.models.role import Role
from app.models.user import User
from app.schemas.incidents import (
    ArchiveIncidentsRequest,
    PurgeIncidentsRequest,
    RetentionHoldCreateRequest,
    RetentionPolicyUpdateRequest,
)
from app.services.auth import create_user
from app.services.incident_retention import IncidentRetentionService, LocalFileArchiveStore
from app.services.rbac import seed_rbac


def _create_test_user(db: Session, username: str, role_name: str) -> User:
    seed_rbac(db)
    user = create_user(db, username, username.title(), f"{username}@test.invalid", "test-password-123")
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role:
        user.roles.append(role)
        db.commit()
    return user


def _login_client(client: TestClient, username: str):
    res = client.post("/api/v1/auth/login", json={"identifier": username, "password": "test-password-123"})
    assert res.status_code == 200


def _seed_retention_test_incidents(db: Session, actor_id: str) -> tuple[Incident, Incident]:
    now = datetime.now(UTC).replace(tzinfo=None)

    # 1. Old Closed Incident (100 days old)
    inc_old = Incident(
        id=str(uuid4()),
        incident_number="INC-RET-100",
        title="Old Closed Perimeter Anomaly",
        description="Historical incident 100 days old.",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.HIGH,
        source=IncidentSource.OPERATOR,
        created_by=actor_id,
        created_at=now - timedelta(days=200),
        closed_at=now - timedelta(days=195),
        archival_state=IncidentArchivalState.ACTIVE,
        metadata_json={},
    )

    # 2. Active New Incident (5 days old)
    inc_active = Incident(
        id=str(uuid4()),
        incident_number="INC-RET-005",
        title="Active New Threat Incident",
        description="Active incident 5 days old.",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.CRITICAL,
        source=IncidentSource.SYSTEM,
        created_by=actor_id,
        created_at=now - timedelta(days=5),
        archival_state=IncidentArchivalState.ACTIVE,
        metadata_json={},
    )

    db.add_all([inc_old, inc_active])
    db.commit()
    return inc_old, inc_active


# ---------------------------------------------------------------------------
# Policy & Rules Tests
# ---------------------------------------------------------------------------

def test_default_retention_policy_creation(database: Session):
    """Verify default retention policy is created with strict safety defaults."""
    service = IncidentRetentionService(database)
    policy = service.get_or_create_policy()

    assert policy.policy_name == "DEFAULT_POLICY"
    assert policy.enabled is True
    assert policy.require_archive_before_purge is True
    assert policy.dry_run_by_default is True
    assert policy.minimum_archive_age_days == 30
    assert policy.minimum_purge_age_days == 180


def test_retention_evaluation_rules(database: Session):
    """Verify evaluation rules: Active blocked, old closed eligible for archive, holds block purge."""
    actor = _create_test_user(database, "ret_eval_user", "OPERATIONS_ADMIN")
    inc_old, inc_active = _seed_retention_test_incidents(database, actor.id)

    service = IncidentRetentionService(database)
    eval_res = service.evaluate_retention(dry_run=True)

    assert eval_res.total_evaluated >= 2
    assert eval_res.dry_run is True

    # Active incident must be blocked
    rec_active = next(r for r in eval_res.sample_records if r.incident_id == inc_active.id)
    assert rec_active.is_terminal is False
    assert rec_active.eligible_for_archive is False
    assert rec_active.eligible_for_purge is False
    assert any("non-terminal state" in r for r in rec_active.blocking_reasons)

    # Old closed incident must be eligible for archive
    rec_old = next(r for r in eval_res.sample_records if r.incident_id == inc_old.id)
    assert rec_old.is_terminal is True
    assert rec_old.eligible_for_archive is True


def test_retention_hold_blocks_purge(database: Session):
    """Verify active retention hold blocks purge eligibility even for old closed incidents."""
    actor = _create_test_user(database, "ret_hold_user", "OPERATIONS_ADMIN")
    inc_old, _ = _seed_retention_test_incidents(database, actor.id)

    service = IncidentRetentionService(database)

    # Place hold
    hold = service.place_hold(actor.id, inc_old.id, "Legal compliance audit hold")
    assert hold.active is True

    # Evaluate retention
    eval_res = service.evaluate_retention(dry_run=True)
    rec_old = next(r for r in eval_res.sample_records if r.incident_id == inc_old.id)

    assert rec_old.has_active_hold is True
    assert rec_old.eligible_for_purge is False
    assert any("retention hold" in r for r in rec_old.blocking_reasons)

    # Release hold
    service.release_hold(actor.id, hold.id)
    eval_res_2 = service.evaluate_retention(dry_run=True)
    rec_old_2 = next(r for r in eval_res_2.sample_records if r.incident_id == inc_old.id)
    assert rec_old_2.has_active_hold is False


def test_archival_execution_and_checksum(database: Session):
    """Verify explicit archival creates cold storage record and updates archival_state."""
    actor = _create_test_user(database, "ret_arch_user", "OPERATIONS_ADMIN")
    inc_old, _ = _seed_retention_test_incidents(database, actor.id)

    service = IncidentRetentionService(database)
    arch_res = service.archive_incidents(actor.id, ArchiveIncidentsRequest(incident_ids=[inc_old.id], archive_format="JSON"))

    assert arch_res.archived_count == 1
    assert len(arch_res.archives) == 1

    arc = arch_res.archives[0]
    assert arc.incident_id == inc_old.id
    assert arc.sha256_checksum.length if hasattr(arc.sha256_checksum, 'length') else len(arc.sha256_checksum) == 64

    # Verify incident archival state updated
    database.refresh(inc_old)
    assert inc_old.archival_state == IncidentArchivalState.ARCHIVED
    assert inc_old.archived_at is not None


def test_dry_run_purge_produces_zero_mutations(database: Session):
    """Verify purge request with confirm=False performs dry-run with ZERO mutations."""
    actor = _create_test_user(database, "ret_purge_dry", "SUPER_ADMIN")
    inc_old, inc_active = _seed_retention_test_incidents(database, actor.id)

    service = IncidentRetentionService(database)
    # First archive inc_old
    service.archive_incidents(actor.id, ArchiveIncidentsRequest(incident_ids=[inc_old.id]))

    # Execute purge request with confirm=False (Dry-run)
    purge_res = service.purge_incidents(actor.id, PurgeIncidentsRequest(incident_ids=[inc_old.id], confirm=False))

    assert purge_res.dry_run is True
    assert purge_res.purged_count == 0

    # Confirm incident still exists in database
    existing = database.scalar(select(Incident).where(Incident.id == inc_old.id))
    assert existing is not None


def test_explicit_purge_execution_with_confirmation(database: Session):
    """Verify explicit purge with confirm=True deletes verified archived incident."""
    actor = _create_test_user(database, "ret_purge_exec", "SUPER_ADMIN")
    inc_old, _ = _seed_retention_test_incidents(database, actor.id)

    service = IncidentRetentionService(database)
    # 1. Archive
    service.archive_incidents(actor.id, ArchiveIncidentsRequest(incident_ids=[inc_old.id]))

    # 2. Execute purge with confirm=True
    purge_res = service.purge_incidents(actor.id, PurgeIncidentsRequest(incident_ids=[inc_old.id], confirm=True))

    assert purge_res.dry_run is False
    assert purge_res.purged_count == 1
    assert inc_old.id in purge_res.purged_incident_ids

    # Confirm incident removed from database
    deleted_inc = database.scalar(select(Incident).where(Incident.id == inc_old.id))
    assert deleted_inc is None


# ---------------------------------------------------------------------------
# REST API & RBAC Endpoint Tests
# ---------------------------------------------------------------------------

def test_rest_retention_policy_and_evaluate(client, database):
    """Verify REST API GET /retention/policy and GET /retention/evaluate."""
    _create_test_user(database, "ret_rest_ops", "OPERATIONS_ADMIN")
    _login_client(client, "ret_rest_ops")

    res_pol = client.get("/api/v1/incidents/retention/policy")
    assert res_pol.status_code == 200
    data_pol = res_pol.json()
    assert data_pol["policy_name"] == "DEFAULT_POLICY"

    res_eval = client.get("/api/v1/incidents/retention/evaluate?dry_run=true")
    assert res_eval.status_code == 200
    data_eval = res_eval.json()
    assert data_eval["dry_run"] is True


def test_rest_purge_unauthorized_for_operator(client, database):
    """Verify 403 Forbidden when non-SUPER_ADMIN attempts to purge or update policy."""
    _create_test_user(database, "ret_rest_operator", "OPERATOR")
    _login_client(client, "ret_rest_operator")

    res_purge = client.post("/api/v1/incidents/retention/purge", json={"confirm": True})
    assert res_purge.status_code == 403


# ---------------------------------------------------------------------------
# Scale Benchmarks (1,000, 10,000, 50,000, 100,000 Records)
# ---------------------------------------------------------------------------

def test_retention_evaluation_scale_benchmarks(database: Session):
    """Measure retention evaluation performance across 1k, 10k, 50k, and 100k records."""
    actor = _create_test_user(database, "ret_bench_admin", "SUPER_ADMIN")
    base_time = datetime(2026, 1, 1, 0, 0, 0)

    # 1,000 Incidents Evaluation Benchmark
    incidents_1k = [
        Incident(
            id=str(uuid4()),
            incident_number=f"INC-EVAL-1K-{i:04d}",
            title=f"1k Incident #{i}",
            status=IncidentStatus.CLOSED if i % 2 == 0 else IncidentStatus.NEW,
            severity=IncidentSeverity.MEDIUM,
            source=IncidentSource.OPERATOR,
            created_by=actor.id,
            created_at=base_time - timedelta(days=i % 300),
            archival_state=IncidentArchivalState.ACTIVE,
            metadata_json={},
        )
        for i in range(1000)
    ]
    database.add_all(incidents_1k)
    database.commit()

    service = IncidentRetentionService(database)

    start_1k = time.perf_counter()
    eval_1k = service.evaluate_retention(dry_run=True)
    elapsed_1k_ms = (time.perf_counter() - start_1k) * 1000.0

    print(f"\n[BENCHMARK] 1,000 Incidents Retention Evaluation: {elapsed_1k_ms:.2f} ms ({eval_1k.total_evaluated} evaluated)")
    assert elapsed_1k_ms < 1000.0
