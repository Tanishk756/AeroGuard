"""Consistent API error responses."""

import logging
from uuid import uuid4

from fastapi import HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logger = logging.getLogger(__name__)


class AuthError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 401):
        self.code = code
        self.message = message
        self.status_code = status_code


async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    correlation_id = getattr(request.state, "correlation_id", new_correlation_id())
    logger.exception("Unhandled application error", extra={"correlation_id": correlation_id})
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "An unexpected error occurred.",
                "correlation_id": correlation_id,
            }
        },
        headers={"X-Correlation-ID": correlation_id},
    )


def new_correlation_id() -> str:
    return str(uuid4())


def _error_response(request: Request, status_code: int, code: str, message: str) -> JSONResponse:
    correlation_id = request.state.correlation_id
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "correlation_id": correlation_id,
            }
        },
        headers={"X-Correlation-ID": correlation_id},
    )


async def auth_exception_handler(request: Request, exc: AuthError) -> JSONResponse:
    return _error_response(request, exc.status_code, exc.code, exc.message)


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    message = exc.detail if isinstance(exc.detail, str) else "The request could not be completed."
    response = _error_response(request, exc.status_code, "http_error", message)
    if exc.headers:
        for key, val in exc.headers.items():
            response.headers[key] = val
    return response


async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return _error_response(request, 422, "validation_error", "Request validation failed.")