"""Production Health, Liveness, and Readiness endpoints."""

from pathlib import Path

from fastapi import APIRouter, Depends, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.telemetry import ARCHIVE_STORAGE_HEALTH, DB_HEALTH
from app.database.session import get_db

router = APIRouter()


@router.get("/health/live")
def liveness():
    """In-memory liveness probe verifying process is responsive.

    Must remain extremely cheap (< 5ms) and perform ZERO external dependency calls.
    """
    return {"status": "live"}


@router.get("/health/ready")
def readiness(
    response: Response,
    settings: Settings = Depends(get_settings),
    db: Session = Depends(get_db),
):
    """Dependency-aware readiness probe verifying database and storage provider availability."""
    db_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
        DB_HEALTH.set(1)
    except Exception:
        db_status = "unhealthy"
        DB_HEALTH.set(0)

    storage_provider = settings.retention_storage_provider
    storage_status = "healthy"

    if storage_provider == "LOCAL":
        try:
            from app.services.archive_store_factory import get_archive_store
            store = get_archive_store("LOCAL")
            ARCHIVE_STORAGE_HEALTH.labels(provider="LOCAL").set(1)
        except Exception:
            storage_status = "unhealthy"
            ARCHIVE_STORAGE_HEALTH.labels(provider="LOCAL").set(0)
    elif storage_provider == "S3":
        try:
            from app.services.archive_store_factory import get_archive_store
            store = get_archive_store("S3")
            store.s3_client.head_bucket(Bucket=store.bucket_name)
            ARCHIVE_STORAGE_HEALTH.labels(provider="S3").set(1)
        except Exception:
            storage_status = "unhealthy"
            ARCHIVE_STORAGE_HEALTH.labels(provider="S3").set(0)

    is_ready = db_status == "healthy" and storage_status == "healthy"

    if not is_ready:
        response.status_code = 503

    return {
        "status": "ready" if is_ready else "unhealthy",
        "checks": {
            "database": db_status,
            "storage": storage_status,
        },
    }


@router.get("/health")
def health(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)):
    """Legacy health endpoint preserved for backward compatibility."""
    database_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
        DB_HEALTH.set(1)
    except Exception:
        database_status = "unhealthy"
        DB_HEALTH.set(0)

    overall_status = "healthy" if database_status == "healthy" else "unhealthy"
    return {
        "status": overall_status,
        "application": settings.application_name,
        "version": settings.version,
        "database": database_status,
    }