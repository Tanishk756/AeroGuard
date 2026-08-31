"""FastAPI application entry point."""

import logging
import re

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.v1.router import router as api_router
from app.core.config import get_settings
from app.core.errors import (
    AuthError,
    auth_exception_handler,
    http_exception_handler,
    new_correlation_id,
    unhandled_exception_handler,
    validation_exception_handler,
)
from contextlib import asynccontextmanager

from app.core.logging import configure_logging
from app.services.scheduler import get_scheduler

settings = get_settings()
configure_logging(settings.log_level)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    scheduler = get_scheduler()
    if settings.scheduler_enabled:
        await scheduler.start()
    yield
    if settings.scheduler_enabled:
        await scheduler.stop()


app = FastAPI(title=settings.application_name, version=settings.version, debug=settings.debug, lifespan=lifespan)
app.add_exception_handler(Exception, unhandled_exception_handler)
app.add_exception_handler(AuthError, auth_exception_handler)
app.add_exception_handler(HTTPException, http_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    supplied = request.headers.get("X-Correlation-ID")
    correlation_id = supplied if supplied and re.fullmatch(r"[A-Za-z0-9._:-]{1,64}", supplied) else new_correlation_id()
    request.state.correlation_id = correlation_id
    response = await call_next(request)
    response.headers["X-Correlation-ID"] = correlation_id
    return response


@app.middleware("http")
async def csrf_origin_middleware(request: Request, call_next):
    if settings.csrf_protection_enabled and request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        origin = request.headers.get("origin")
        if origin and origin not in settings.allowed_origins:
            correlation_id = getattr(request.state, "correlation_id", new_correlation_id())
            return JSONResponse(
                status_code=403,
                content={
                    "error": {
                        "code": "csrf_origin_rejected",
                        "message": "Request origin is not allowed.",
                        "correlation_id": correlation_id,
                    }
                },
                headers={"X-Correlation-ID": correlation_id},
            )
    return await call_next(request)


from app.middleware.csrf import CSRFMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.core.telemetry import setup_opentelemetry
from app.middleware.telemetry import TelemetryMiddleware

app.add_middleware(TelemetryMiddleware)
setup_opentelemetry(app)
app.add_middleware(CSRFMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "X-Correlation-ID", "X-Request-ID", "X-CSRF-Token", "Authorization"],
)


from app.api.v1.routes.health import router as health_router
from app.api.v1.routes.metrics import router as metrics_router

app.include_router(health_router)
app.include_router(metrics_router)
app.include_router(api_router, prefix=settings.api_prefix)