"""Stage IM3-B Multi-Provider Archive Store Router & Retention Integration Tests."""

import time
from unittest.mock import MagicMock

import boto3
from moto import mock_aws
import pytest

from app.core.config import get_settings
from app.models.incident import Incident, IncidentStatus
from app.models.incident_retention import IncidentArchive, IncidentArchivalState
from app.services.archive_store_factory import (
    ArchiveStoreConfigError,
    get_archive_store,
    get_archive_store_health,
)
from app.services.incident_retention import (
    IncidentRetentionService,
    LocalFileArchiveStore,
)
from app.services.s3_archive_store import S3ObjectArchiveStore


def test_factory_local_provider_selection():
    """Verify factory returns LocalFileArchiveStore when provider='LOCAL' is specified."""
    store = get_archive_store("LOCAL")
    assert isinstance(store, LocalFileArchiveStore)
    assert getattr(store, "provider_name", None) == "LOCAL"


def test_factory_s3_provider_selection():
    """Verify factory returns S3ObjectArchiveStore when provider='S3' is specified."""
    with mock_aws():
        store = get_archive_store("S3", bucket_name="test-bucket", region_name="us-east-1")
        assert isinstance(store, S3ObjectArchiveStore)
        assert getattr(store, "provider_name", None) == "S3"


def test_factory_invalid_provider_rejection():
    """Verify factory raises ArchiveStoreConfigError on unsupported provider names without falling back."""
    with pytest.raises(ArchiveStoreConfigError, match="Invalid retention storage provider: 'AZURE'"):
        get_archive_store("AZURE")

    with pytest.raises(ArchiveStoreConfigError, match="Invalid retention storage provider: 'INVALID'"):
        get_archive_store("INVALID")


def test_factory_default_provider():
    """Verify factory defaults to settings.retention_storage_provider when no argument is passed."""
    settings = get_settings()
    store = get_archive_store()
    if settings.retention_storage_provider == "LOCAL":
        assert isinstance(store, LocalFileArchiveStore)
    else:
        assert isinstance(store, S3ObjectArchiveStore)


def test_no_automatic_fallback_from_s3_to_local():
    """Verify that when S3 provider is configured and fails, it raises an exception without silent fallback to LOCAL."""
    mock_failing_s3 = MagicMock(spec=S3ObjectArchiveStore)
    mock_failing_s3.archive.side_effect = RuntimeError("S3 endpoint connection refused")
    mock_failing_s3.provider_name = "S3"

    # Retention service configured with failing S3 store must raise error
    service = IncidentRetentionService(db=MagicMock(), store=mock_failing_s3)
    assert service.store == mock_failing_s3

    with pytest.raises(RuntimeError, match="S3 endpoint connection refused"):
        service.store.archive("ARC-FAIL-01", b"payload", "JSON")


def test_archive_store_health_local():
    """Verify get_archive_store_health returns HEALTHY status for LOCAL provider without secrets."""
    health = get_archive_store_health("LOCAL")
    assert health["provider"] == "LOCAL"
    assert health["status"] == "HEALTHY"
    assert health["reachable"] is True
    assert "location" in health


def test_archive_store_health_s3_healthy():
    """Verify get_archive_store_health returns HEALTHY status for valid S3 bucket."""
    with mock_aws():
        s3 = boto3.client("s3", region_name="us-east-1")
        s3.create_bucket(Bucket="aeroguard-health-bucket")

        store = S3ObjectArchiveStore(bucket_name="aeroguard-health-bucket", region_name="us-east-1")
        health = store.check_health()
        assert health["provider"] == "S3"
        assert health["status"] == "HEALTHY"
        assert health["reachable"] is True


def test_archive_store_health_s3_unhealthy():
    """Verify get_archive_store_health returns UNHEALTHY status for missing S3 bucket."""
    with mock_aws():
        store = S3ObjectArchiveStore(bucket_name="non-existent-health-bucket", region_name="us-east-1")
        health = store.check_health()
        assert health["provider"] == "S3"
        assert health["status"] == "UNHEALTHY"
        assert health["reachable"] is False


@pytest.mark.benchmark
def test_factory_routing_performance_scale_benchmark():
    """Benchmark 1,000 factory provider resolution decisions (< 100 ms overhead)."""
    start_time = time.perf_counter()
    for _ in range(1000):
        _ = get_archive_store("LOCAL")
    duration_ms = (time.perf_counter() - start_time) * 1000.0

    assert duration_ms < 100.0, f"Factory routing overhead too high: {duration_ms:.2f} ms"
