"""Multi-provider archive store router and factory (IM3-B)."""

import logging
from pathlib import Path
from typing import Any

from app.core.config import get_settings
from app.services.incident_retention import IncidentArchiveStore, LocalFileArchiveStore
from app.services.s3_archive_store import S3ObjectArchiveStore

logger = logging.getLogger(__name__)


class ArchiveStoreConfigError(ValueError):
    """Raised when an invalid storage provider configuration is supplied."""


def get_archive_store(provider: str | None = None, **kwargs) -> IncidentArchiveStore:
    """Resolve and instantiate the configured IncidentArchiveStore provider.
    Supported providers: 'LOCAL', 'S3'.
    Fails fast on unsupported providers; no silent fallbacks.
    """
    settings = get_settings()
    target_provider = (provider or settings.retention_storage_provider).strip().upper()

    if target_provider == "LOCAL":
        base_dir = kwargs.get("base_dir", "data/archives")
        return LocalFileArchiveStore(base_dir=base_dir)

    elif target_provider == "S3":
        return S3ObjectArchiveStore(
            bucket_name=kwargs.get("bucket_name"),
            endpoint_url=kwargs.get("endpoint_url"),
            region_name=kwargs.get("region_name"),
            access_key_id=kwargs.get("access_key_id"),
            secret_access_key=kwargs.get("secret_access_key"),
            sse_algorithm=kwargs.get("sse_algorithm"),
            sse_kms_key_id=kwargs.get("sse_kms_key_id"),
            s3_client=kwargs.get("s3_client"),
        )

    else:
        logger.error(f"Unsupported retention storage provider requested: '{target_provider}'")
        raise ArchiveStoreConfigError(
            f"Invalid retention storage provider: '{target_provider}'. "
            "Supported providers are 'LOCAL' and 'S3'."
        )


def get_archive_store_health(provider: str | None = None) -> dict[str, Any]:
    """Inspect and report non-destructive storage provider health status.
    Never exposes credentials or secret keys.
    """
    settings = get_settings()
    target_provider = (provider or settings.retention_storage_provider).strip().upper()

    if target_provider == "LOCAL":
        base_dir = Path("data/archives")
        try:
            base_dir.mkdir(parents=True, exist_ok=True)
            return {
                "provider": "LOCAL",
                "status": "HEALTHY",
                "reachable": True,
                "location": str(base_dir.absolute()),
            }
        except Exception as exc:
            return {
                "provider": "LOCAL",
                "status": "UNHEALTHY",
                "reachable": False,
                "location": str(base_dir),
                "error": str(exc),
            }

    elif target_provider == "S3":
        store = get_archive_store("S3")
        if isinstance(store, S3ObjectArchiveStore):
            return store.check_health()
        return {"provider": "S3", "status": "UNHEALTHY", "reachable": False, "error": "Invalid store instance"}

    else:
        return {
            "provider": target_provider,
            "status": "UNHEALTHY",
            "reachable": False,
            "error": f"Invalid retention storage provider: '{target_provider}'",
        }
