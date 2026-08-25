"""Version 1 API router composition."""

from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.system import router as system_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.rbac import router as rbac_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(system_router, tags=["system"])
router.include_router(auth_router, tags=["auth"])
router.include_router(rbac_router, tags=["rbac"])