"""System information endpoint."""

import platform
import sys

from fastapi import APIRouter, Depends

from app.core.config import Settings, get_settings
from app.dependencies import require_permission
from app.models.user import User

router = APIRouter()


@router.get("/system/info")
def system_info(settings: Settings = Depends(get_settings), user: User = Depends(require_permission("system.read"))):
    return {
        "application": settings.application_name,
        "version": settings.version,
        "environment": settings.environment,
        "python_version": platform.python_version(),
        "platform": platform.platform(),
        "debug": settings.debug,
    }