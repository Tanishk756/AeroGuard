"""Request telemetry and correlation ID middleware."""

import re
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings, get_settings
from app.core.telemetry import (
    HTTP_ERRORS_TOTAL,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
)

ID_REGEX = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def normalize_route_path(path: str) -> str:
    """Normalize raw HTTP request path into a low-cardinality route template string.

    Replaces dynamic UUIDs, integer IDs, hashes, and hex strings with template tokens.
    """
    if not path:
        return "/"

    # Standardize API prefix routes
    parts = path.strip("/").split("/")
    normalized_parts = []
    for part in parts:
        # Check if part is a UUID
        if re.fullmatch(r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}", part):
            normalized_parts.append("{id}")
        # Check if part is a hex hash or integer ID
        elif re.fullmatch(r"[0-9a-fA-F]{16,64}", part) or part.isdigit():
            normalized_parts.append("{id}")
        # Check if part starts with common prefixes like TRK-, INC-, ALT-
        elif re.match(r"^(TRK|INC|ALT|GEO|SCN|USR|ROL)-[A-Za-z0-9._:-]+$", part, re.IGNORECASE):
            normalized_parts.append("{id}")
        else:
            normalized_parts.append(part)

    return "/" + "/".join(normalized_parts)


class TelemetryMiddleware(BaseHTTPMiddleware):
    """ASGI Middleware handling request correlation ID validation/generation and low-cardinality HTTP metrics."""

    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        start_time = time.perf_counter()

        # 1. Process Request ID / Correlation ID
        incoming_req_id = request.headers.get("X-Request-ID")
        incoming_corr_id = request.headers.get("X-Correlation-ID")

        # Extract or validate request ID
        req_id = incoming_req_id if (incoming_req_id and ID_REGEX.fullmatch(incoming_req_id)) else str(uuid4())

        # Extract or validate correlation ID, preserving backward compatibility
        if incoming_corr_id and ID_REGEX.fullmatch(incoming_corr_id):
            corr_id = incoming_corr_id
        else:
            corr_id = req_id

        # Bind IDs to request state
        request.state.request_id = req_id
        request.state.correlation_id = corr_id

        norm_route = normalize_route_path(request.url.path)
        method = request.method

        try:
            response = await call_next(request)
            status_code = response.status_code
        except Exception as exc:
            duration = time.perf_counter() - start_time
            status_class = "5xx"
            if self.settings.metrics_enabled:
                HTTP_REQUESTS_TOTAL.labels(method=method, route=norm_route, status_class=status_class).inc()
                HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=norm_route).observe(duration)
                HTTP_ERRORS_TOTAL.labels(method=method, route=norm_route, error_type=exc.__class__.__name__).inc()
            raise exc

        duration = time.perf_counter() - start_time
        status_class = f"{status_code // 100}xx"

        if self.settings.metrics_enabled:
            HTTP_REQUESTS_TOTAL.labels(method=method, route=norm_route, status_class=status_class).inc()
            HTTP_REQUEST_DURATION_SECONDS.labels(method=method, route=norm_route).observe(duration)
            if status_code >= 400:
                HTTP_ERRORS_TOTAL.labels(method=method, route=norm_route, error_type=f"HTTP_{status_code}").inc()

        # Attach response headers
        response.headers["X-Request-ID"] = req_id
        response.headers["X-Correlation-ID"] = corr_id

        return response
