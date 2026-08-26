"""Version 1 API router composition."""

from fastapi import APIRouter

from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.system import router as system_router
from app.api.v1.routes.auth import router as auth_router
from app.api.v1.routes.rbac import router as rbac_router
from app.api.v1.routes.audit import router as audit_router
from app.api.v1.routes.sensors import router as sensors_router
from app.api.v1.routes.detections import router as detections_router
from app.api.v1.routes.tracks import router as tracks_router

router = APIRouter()
router.include_router(health_router, tags=["health"])
router.include_router(system_router, tags=["system"])
router.include_router(auth_router, tags=["auth"])
router.include_router(rbac_router, tags=["rbac"])
router.include_router(audit_router, tags=["audit"])
router.include_router(sensors_router, tags=["sensors"])
router.include_router(detections_router, tags=["detections"])
router.include_router(tracks_router, tags=["tracks"])