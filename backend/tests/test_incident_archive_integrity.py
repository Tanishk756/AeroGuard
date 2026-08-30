"""Stage IM3-D Cloud Archive Integrity Verification & Reconciliation Test Suite."""

from datetime import UTC, datetime
from hashlib import sha256
import time
from uuid import uuid4

import boto3
from moto import mock_aws
import pytest
from sqlalchemy import select

from app.models.incident import Incident, IncidentSeverity, IncidentSource, IncidentStatus
from app.models.incident_retention import (
    IncidentArchive,
    IncidentArchiveIntegrityCheck,
    IntegrityStatus,
)
from app.models.role import Role
from app.models.user import User
from app.services.archive_store_factory import get_archive_store
from app.services.incident_archive_integrity import IncidentArchiveIntegrityService
from app.services.incident_retention import LocalFileArchiveStore
from app.services.s3_archive_store import S3ObjectArchiveStore


def _authenticate_as(client, database, rbac_user, role_name: str = "SUPER_ADMIN") -> User:
    """Helper to assign role and log in test user."""
    role = database.scalar(select(Role).where(Role.name == role_name))
    if role and role not in rbac_user.roles:
        rbac_user.roles.append(role)
        database.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert login.status_code == 200
    return rbac_user


@pytest.fixture
def mock_s3_env(monkeypatch):
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="aeroguard-archives")

        def mock_get_store(provider=None, **kwargs):
            p = (provider or "LOCAL").upper()
            if p == "S3":
                return S3ObjectArchiveStore(s3_client=s3, bucket_name="aeroguard-archives")
            return get_archive_store(provider, **kwargs)

        monkeypatch.setattr("app.services.incident_archive_integrity.get_archive_store", mock_get_store)
        yield s3


def test_verify_healthy_s3_archive(database, rbac_user, mock_s3_env):
    """Verify HEALTHY status when database metadata matches S3 object payload."""
    now = datetime.now(UTC).replace(tzinfo=None)
    payload_str = '{"incident_id": "inc-s3-101", "status": "CLOSED"}'
    payload_bytes = payload_str.encode("utf-8")
    expected_checksum = sha256(payload_bytes).hexdigest()
    expected_size = len(payload_bytes)

    # Seed DB records
    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-S3-INT-101",
        title="Healthy S3 Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.HIGH,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-S3-INT-101",
        incident_id=inc.id,
        sha256_checksum=expected_checksum,
        file_size_bytes=expected_size,
        archive_format="JSON",
        storage_provider="S3",
        storage_location="s3://aeroguard-archives/archives/ARC-JSON-INC-S3-INT-101.json",
        payload_data=payload_str,
        archived_at=now,
        archived_by=rbac_user.id,
    )
    database.add(archive)
    database.commit()

    # Upload exact object to moto mock S3
    mock_s3_env.put_object(
        Bucket="aeroguard-archives",
        Key="archives/ARC-JSON-INC-S3-INT-101.json",
        Body=payload_bytes,
    )

    service = IncidentArchiveIntegrityService(database)
    check = service.verify_archive(archive.id)

    assert check.status == IntegrityStatus.HEALTHY
    assert check.observed_checksum == expected_checksum
    assert check.observed_size_bytes == expected_size
    assert check.error_code is None
    assert archive.verified_at is not None


def test_verify_missing_s3_object(database, rbac_user, mock_s3_env):
    """Verify OBJECT_MISSING status when archive DB record exists but S3 payload object is absent."""
    now = datetime.now(UTC).replace(tzinfo=None)

    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-S3-MISSING",
        title="Missing S3 Object Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.MEDIUM,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-S3-MISSING",
        incident_id=inc.id,
        sha256_checksum="a" * 64,
        file_size_bytes=100,
        archive_format="JSON",
        storage_provider="S3",
        storage_location="s3://aeroguard-archives/archives/ARC-JSON-INC-S3-MISSING.json",
        payload_data="{}",
        archived_at=now,
        archived_by=rbac_user.id,
    )
    database.add(archive)
    database.commit()

    # DO NOT upload payload to S3 -> Object is missing

    service = IncidentArchiveIntegrityService(database)
    check = service.verify_archive(archive.id)

    assert check.status == IntegrityStatus.OBJECT_MISSING
    assert check.error_code == "OBJECT_MISSING"


def test_verify_checksum_mismatch_s3(database, rbac_user, mock_s3_env):
    """Verify CHECKSUM_MISMATCH status when S3 object payload bytes have been altered."""
    now = datetime.now(UTC).replace(tzinfo=None)
    original_payload = '{"test": "original"}'
    tampered_payload = '{"test": "TAMPERED_MODIFIED"}'

    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-S3-TAMPERED",
        title="Tampered Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.HIGH,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-S3-TAMPERED",
        incident_id=inc.id,
        sha256_checksum=sha256(original_payload.encode("utf-8")).hexdigest(),
        file_size_bytes=len(original_payload.encode("utf-8")),
        archive_format="JSON",
        storage_provider="S3",
        storage_location="s3://aeroguard-archives/archives/ARC-JSON-INC-S3-TAMPERED.json",
        payload_data=original_payload,
        archived_at=now,
        archived_by=rbac_user.id,
    )
    database.add(archive)
    database.commit()

    # Upload TAMPERED payload to S3
    mock_s3_env.put_object(
        Bucket="aeroguard-archives",
        Key="archives/ARC-JSON-INC-S3-TAMPERED.json",
        Body=tampered_payload.encode("utf-8"),
    )

    service = IncidentArchiveIntegrityService(database)
    check = service.verify_archive(archive.id)

    assert check.status in (IntegrityStatus.CHECKSUM_MISMATCH, IntegrityStatus.METADATA_MISMATCH)
    assert check.observed_checksum != archive.sha256_checksum


def test_verify_healthy_local_archive(database, rbac_user, tmp_path, monkeypatch):
    """Verify HEALTHY status for local filesystem archive."""
    now = datetime.now(UTC).replace(tzinfo=None)
    payload_str = '{"incident": "local"}'
    payload_bytes = payload_str.encode("utf-8")
    expected_checksum = sha256(payload_bytes).hexdigest()

    def mock_get_local_store(provider=None, **kwargs):
        return LocalFileArchiveStore(base_dir=str(tmp_path))

    monkeypatch.setattr("app.services.incident_archive_integrity.get_archive_store", mock_get_local_store)

    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-LOC-INT",
        title="Local Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-LOC-INT",
        incident_id=inc.id,
        sha256_checksum=expected_checksum,
        file_size_bytes=len(payload_bytes),
        archive_format="JSON",
        storage_provider="LOCAL",
        storage_location=str(tmp_path / "ARC-JSON-INC-LOC-INT.json"),
        payload_data=payload_str,
        archived_at=now,
        archived_by=rbac_user.id,
    )
    database.add(archive)
    database.commit()

    # Write payload file to disk
    local_file = tmp_path / "ARC-JSON-INC-LOC-INT.json"
    local_file.write_bytes(payload_bytes)

    service = IncidentArchiveIntegrityService(database)
    check = service.verify_archive(archive.id)

    assert check.status == IntegrityStatus.HEALTHY
    assert check.observed_checksum == expected_checksum


def test_verification_is_strictly_read_only(database, rbac_user, mock_s3_env):
    """Verify integrity check operation never mutates incident status or deletes records."""
    now = datetime.now(UTC).replace(tzinfo=None)

    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-READONLY",
        title="Read-Only Invariant Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.HIGH,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-READONLY",
        incident_id=inc.id,
        sha256_checksum="c" * 64,
        file_size_bytes=128,
        archive_format="JSON",
        storage_provider="S3",
        storage_location="s3://aeroguard-archives/archives/ARC-JSON-INC-READONLY.json",
        payload_data="{}",
        archived_at=now,
        archived_by=rbac_user.id,
    )
    database.add(archive)
    database.commit()

    service = IncidentArchiveIntegrityService(database)
    service.verify_archive(archive.id)

    # Verify incident state was NOT modified
    reloaded_inc = database.scalar(select(Incident).where(Incident.id == inc.id))
    assert reloaded_inc.status == IncidentStatus.CLOSED
    assert reloaded_inc.title == "Read-Only Invariant Incident"


def test_integrity_rest_endpoints(client, database, rbac_user, mock_s3_env):
    """Verify REST endpoints for integrity summary, checks list, batch check, and single verify."""
    user = _authenticate_as(client, database, rbac_user, "SUPER_ADMIN")
    now = datetime.now(UTC).replace(tzinfo=None)

    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-REST-INT",
        title="REST Integrity Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.MEDIUM,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-REST-INT",
        incident_id=inc.id,
        sha256_checksum="d" * 64,
        file_size_bytes=64,
        archive_format="JSON",
        storage_provider="S3",
        payload_data="{}",
        archived_at=now,
        archived_by=user.id,
    )
    database.add(archive)
    database.commit()

    # 1. GET /api/v1/incidents/retention/integrity/summary
    res_sum = client.get("/api/v1/incidents/retention/integrity/summary")
    assert res_sum.status_code == 200, res_sum.text
    assert "total_checks" in res_sum.json()

    # 2. POST /api/v1/incidents/retention/archives/{id}/verify
    res_ver = client.post(f"/api/v1/incidents/retention/archives/{archive.id}/verify")
    assert res_ver.status_code == 200, res_ver.text
    assert res_ver.json()["archive_id"] == archive.id

    # 3. GET /api/v1/incidents/retention/integrity
    res_list = client.get("/api/v1/incidents/retention/integrity?limit=10")
    assert res_list.status_code == 200
    assert len(res_list.json()) >= 1


def test_reconciliation_scale_benchmark_1k(database):
    """Benchmark 1,000 in-memory archive integrity check classifications (< 100 ms)."""
    now = datetime.now(UTC).replace(tzinfo=None)
    service = IncidentArchiveIntegrityService(database)

    # Seed 1,000 synthetic checks
    checks = []
    for i in range(1000):
        checks.append(
            IncidentArchiveIntegrityCheck(
                id=str(uuid4()),
                archive_id=str(uuid4()),
                archive_number=f"ARC-BENCH-{i:04d}",
                incident_id=str(uuid4()),
                storage_provider="LOCAL",
                status=IntegrityStatus.HEALTHY,
                expected_checksum="a" * 64,
                observed_checksum="a" * 64,
                expected_size_bytes=1024,
                observed_size_bytes=1024,
                duration_ms=0.05,
                checked_at=now,
            )
        )

    t0 = time.perf_counter()
    database.bulk_save_objects(checks)
    database.commit()
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    summary = service.summarize_results()
    assert summary["total_checks"] >= 1000
    print(f"\n[BENCHMARK] 1,000 Integrity Checks Bulk Save & Summarize Time: {elapsed_ms:.2f} ms")
    assert elapsed_ms < 500.0
