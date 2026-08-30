"""Stage IM3-C Presigned Download URL REST Endpoint & Security Tests."""

from datetime import UTC, datetime
from uuid import uuid4

import boto3
from moto import mock_aws
import pytest
from sqlalchemy import select

from app.models.incident import Incident, IncidentSeverity, IncidentSource, IncidentStatus
from app.models.incident_retention import IncidentArchive, IncidentArchivalState
from app.models.role import Role
from app.models.user import User


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
def mock_s3_env():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="aeroguard-archives")
        yield s3


def test_presigned_download_url_success_s3(client, database, rbac_user, mock_s3_env):
    """Verify presigned download URL generation for valid S3-backed incident archive."""
    user = _authenticate_as(client, database, rbac_user, "SUPER_ADMIN")
    now = datetime.now(UTC).replace(tzinfo=None)

    # Seed incident and archive
    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-S3-001",
        title="S3 Download Test Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.MEDIUM,
        source=IncidentSource.OPERATOR,
        archival_state=IncidentArchivalState.ARCHIVED,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-PDF-INC-S3-001",
        incident_id=inc.id,
        sha256_checksum="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
        file_size_bytes=1024,
        archive_format="PDF",
        storage_provider="S3",
        storage_location="s3://aeroguard-archives/archives/ARC-PDF-INC-S3-001.pdf",
        payload_data="JVBERi0xLjQK...",
        archived_at=now,
        archived_by=user.id,
    )
    database.add(archive)
    database.commit()

    # Upload object to moto mock S3
    mock_s3_env.put_object(
        Bucket="aeroguard-archives",
        Key="archives/ARC-PDF-INC-S3-001.pdf",
        Body=b"%PDF-1.4 test payload",
    )

    res = client.get(f"/api/v1/incidents/retention/archives/{archive.id}/download-url?expires_in_seconds=600")
    assert res.status_code == 200, res.text

    data = res.json()
    assert data["archive_id"] == archive.id
    assert data["archive_number"] == "ARC-PDF-INC-S3-001"
    assert data["storage_provider"] == "S3"
    assert data["expires_in_seconds"] == 600
    assert data["url"].startswith("http")
    assert "archives/ARC-PDF-INC-S3-001.pdf" in data["url"]

    # Ensure secret keys are NOT exposed
    assert "access_key" not in res.text.lower()
    assert "secret_key" not in res.text.lower()


def test_presigned_download_url_rejection_for_local_provider(client, database, rbac_user):
    """Verify 400 Bad Request when requesting presigned download URL for LOCAL storage provider."""
    user = _authenticate_as(client, database, rbac_user, "SUPER_ADMIN")
    now = datetime.now(UTC).replace(tzinfo=None)

    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-LOCAL-001",
        title="Local Download Test Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-LOCAL-001",
        incident_id=inc.id,
        sha256_checksum="a" * 64,
        file_size_bytes=512,
        archive_format="JSON",
        storage_provider="LOCAL",
        storage_location="data/archives/ARC-JSON-INC-LOCAL-001.json",
        payload_data='{"test": true}',
        archived_at=now,
        archived_by=user.id,
    )
    database.add(archive)
    database.commit()

    res = client.get(f"/api/v1/incidents/retention/archives/{archive.id}/download-url")
    assert res.status_code == 400
    msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "Presigned download URLs are only available for S3-backed archives" in msg


def test_presigned_download_url_missing_archive_404(client, database, rbac_user):
    """Verify 404 Not Found when archive ID does not exist."""
    _authenticate_as(client, database, rbac_user, "SUPER_ADMIN")
    fake_id = str(uuid4())
    res = client.get(f"/api/v1/incidents/retention/archives/{fake_id}/download-url")
    assert res.status_code == 404
    msg = res.json().get("error", {}).get("message") or res.json().get("detail", "")
    assert "Incident archive record not found" in msg


def test_presigned_download_url_expiration_bounds_validation(client, database, rbac_user, mock_s3_env):
    """Verify Query validation rejects expiration TTL < 60s or > 900s."""
    user = _authenticate_as(client, database, rbac_user, "SUPER_ADMIN")
    now = datetime.now(UTC).replace(tzinfo=None)

    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-S3-BOUNDS",
        title="Bounds Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
        created_at=now,
        updated_at=now,
    )
    database.add(inc)

    archive = IncidentArchive(
        id=str(uuid4()),
        archive_number="ARC-JSON-INC-S3-BOUNDS",
        incident_id=inc.id,
        sha256_checksum="b" * 64,
        file_size_bytes=256,
        archive_format="JSON",
        storage_provider="S3",
        payload_data="{}",
        archived_at=now,
        archived_by=user.id,
    )
    database.add(archive)
    database.commit()

    # < 60s TTL -> 422
    res_too_small = client.get(f"/api/v1/incidents/retention/archives/{archive.id}/download-url?expires_in_seconds=10")
    assert res_too_small.status_code == 422

    # > 900s TTL -> 422
    res_too_large = client.get(f"/api/v1/incidents/retention/archives/{archive.id}/download-url?expires_in_seconds=3600")
    assert res_too_large.status_code == 422


def test_presigned_download_url_unauthenticated(client):
    """Verify 401 Unauthenticated when requesting presigned download URL without session cookie."""
    client.cookies.clear()
    res = client.get(f"/api/v1/incidents/retention/archives/{uuid4()}/download-url")
    assert res.status_code == 401


def test_retention_storage_health_endpoint(client, database, rbac_user):
    """Verify GET /api/v1/incidents/retention/storage/health returns health status without secrets."""
    _authenticate_as(client, database, rbac_user, "SUPER_ADMIN")
    res = client.get("/api/v1/incidents/retention/storage/health")
    assert res.status_code == 200, res.text
    data = res.json()
    assert "provider" in data
    assert "status" in data
    assert "reachable" in data
    assert "access_key" not in res.text.lower()
    assert "secret_key" not in res.text.lower()
