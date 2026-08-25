"""System information endpoint."""

import platform
import sys

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings

router = APIRouter()


@router.get("/system/info")
def system_info(settings: Settings = Depends(get_settings)):
    return {
        "application": settings.application_name,
        "version": settings.version,
        "environment": settings.environment,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "debug": settings.debug,
    }