"""Health endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db

router = APIRouter()


@router.get("/health")
def health(settings: Settings = Depends(get_settings), db: Session = Depends(get_db)):
    database_status = "healthy"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        database_status = "unhealthy"

    overall_status = "healthy" if database_status == "healthy" else "unhealthy"
    return {
        "status": overall_status,
        "application": settings.application_name,
        "version": settings.version,
        "database": database_status,
    }