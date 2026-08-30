"""Prometheus metrics exposition endpoint."""

from fastapi import APIRouter, Depends, Response

from app.core.config import Settings, get_settings
from app.core.telemetry import get_metrics_exposition

router = APIRouter()


@router.get("/metrics", response_class=Response)
def get_metrics(settings: Settings = Depends(get_settings)):
    """Expose Prometheus format operational metrics."""
    if not settings.metrics_enabled:
        return Response(content="# Metrics disabled\n", media_type="text/plain; version=0.0.4; charset=utf-8", status_code=200)

    content = get_metrics_exposition()
    return Response(content=content, media_type="text/plain; version=0.0.4; charset=utf-8", status_code=200)
