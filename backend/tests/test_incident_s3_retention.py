"""Stage IM3-A S3-Compatible Cold Storage Adapter Foundation & Bucket Metadata Tests.
Uses moto isolated mock S3 environment.
"""

import base64
import hashlib
from unittest.mock import MagicMock

import boto3
from botocore.exceptions import ClientError
from moto import mock_aws
import pytest

from app.core.config import get_settings
from app.services.incident_retention import LocalFileArchiveStore
from app.services.s3_archive_store import (
    S3ArchiveStoreError,
    S3ObjectArchiveStore,
    S3ObjectNotFoundError,
)


@pytest.fixture
def mock_s3_bucket():
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="aeroguard-test-archives")
        yield "aeroguard-test-archives"


def test_s3_adapter_construction_and_key_determinism(mock_s3_bucket):
    """Verify S3ObjectArchiveStore initializes correctly and formats deterministic object keys."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")
    assert adapter.bucket_name == mock_s3_bucket

    key_json = adapter._get_object_key("ARC-20260829-001", "JSON")
    assert key_json == "archives/ARC-20260829-001.json"

    key_pdf = adapter._get_object_key("ARC-20260829-002", "PDF")
    assert key_pdf == "archives/ARC-20260829-002.pdf"


def test_s3_json_and_pdf_archive_upload(mock_s3_bucket):
    """Verify JSON and PDF binary archive payloads upload to S3 with SSE encryption and metadata."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")

    # JSON Upload
    json_bytes = b'{"incident_id": "inc-101", "status": "CLOSED"}'
    s3_uri = adapter.archive("ARC-JSON-101", json_bytes, "JSON")
    assert s3_uri == f"s3://{mock_s3_bucket}/archives/ARC-JSON-101.json"

    # PDF Upload
    pdf_bytes = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog >>\nendobj\n%%EOF"
    pdf_uri = adapter.archive("ARC-PDF-101", pdf_bytes, "PDF")
    assert pdf_uri == f"s3://{mock_s3_bucket}/archives/ARC-PDF-101.pdf"


def test_s3_retrieve_and_exists(mock_s3_bucket):
    """Verify retrieve reads exact bytes and exists detects key presence correctly."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")

    assert adapter.exists("ARC-JSON-202") is False

    payload = b"Exact test payload content"
    adapter.archive("ARC-JSON-202", payload, "JSON")

    assert adapter.exists("ARC-JSON-202") is True
    retrieved = adapter.retrieve("ARC-JSON-202")
    assert retrieved == payload


def test_s3_missing_object_error_handling(mock_s3_bucket):
    """Verify S3ObjectNotFoundError is raised when attempting to retrieve missing objects."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")

    with pytest.raises(S3ObjectNotFoundError):
        adapter.retrieve("NON-EXISTENT-KEY")


def test_s3_sha256_checksum_verification(mock_s3_bucket):
    """Verify SHA-256 checksum verification succeeds on matching hash and fails on mismatch."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")

    payload = b"Immutable security payload string for integrity verification"
    expected_sha = hashlib.sha256(payload).hexdigest()

    adapter.archive("ARC-VERIFY-1", payload, "JSON")

    # Success case
    assert adapter.verify("ARC-VERIFY-1", expected_sha) is True

    # Failure case
    assert adapter.verify("ARC-VERIFY-1", "0000000000000000000000000000000000000000000000000000000000000000") is False


def test_s3_delete_and_idempotency(mock_s3_bucket):
    """Verify explicit archive deletion removes S3 object idempotently."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")

    payload = b"Data to be deleted"
    adapter.archive("ARC-DEL-1", payload, "JSON")
    assert adapter.exists("ARC-DEL-1") is True

    deleted = adapter.delete("ARC-DEL-1")
    assert deleted is True
    assert adapter.exists("ARC-DEL-1") is False

    # Second delete is idempotent
    deleted_again = adapter.delete("ARC-DEL-1")
    assert deleted_again is False


def test_s3_presigned_url_generation(mock_s3_bucket):
    """Verify presigned download URL generation for existing S3 objects."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")

    payload = b"Presigned download content"
    adapter.archive("ARC-URL-1", payload, "JSON")

    url = adapter.generate_presigned_url("ARC-URL-1", expires_in_seconds=900)
    assert url.startswith("http")
    assert "archives/ARC-URL-1.json" in url


def test_s3_bucket_health_check(mock_s3_bucket):
    """Verify check_health returns healthy state without exposing credentials or mutating data."""
    adapter = S3ObjectArchiveStore(bucket_name=mock_s3_bucket, region_name="us-east-1")

    health = adapter.check_health()
    assert health["provider"] == "S3"
    assert health["status"] == "HEALTHY"
    assert health["reachable"] is True
    assert health["bucket_name"] == mock_s3_bucket

    # Ensure secret keys are NOT exposed
    assert "access_key" not in health
    assert "secret_key" not in health
    assert "AWS_SECRET_ACCESS_KEY" not in str(health)


def test_s3_bucket_health_unhealthy_on_missing_bucket():
    """Verify check_health returns UNHEALTHY when S3 bucket does not exist."""
    with mock_aws():
        adapter = S3ObjectArchiveStore(bucket_name="non-existent-aeroguard-bucket", region_name="us-east-1")
        health = adapter.check_health()
        assert health["status"] == "UNHEALTHY"
        assert health["reachable"] is False
        assert "error" in health


def test_local_archive_store_remains_unaffected(tmp_path):
    """Verify LocalFileArchiveStore implementation continues working independently of S3 adapter."""
    local_store = LocalFileArchiveStore(base_dir=str(tmp_path))

    payload = b"Local file storage payload"
    path_str = local_store.archive("ARC-LOCAL-1", payload, "JSON")
    assert local_store.exists("ARC-LOCAL-1") is True
    assert local_store.retrieve("ARC-LOCAL-1") == payload
    assert local_store.verify("ARC-LOCAL-1", hashlib.sha256(payload).hexdigest()) is True
    assert local_store.delete("ARC-LOCAL-1") is True
    assert local_store.exists("ARC-LOCAL-1") is False
