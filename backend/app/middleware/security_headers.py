"""Defensive HTTP security headers middleware."""

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from app.core.config import Settings, get_settings


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """ASGI middleware applying defensive HTTP security response headers."""

    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)

        if not self.settings.security_headers_enabled:
            return response

        headers = response.headers
        headers["X-Content-Type-Options"] = "nosniff"
        headers["X-Frame-Options"] = "DENY"
        headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Tailored Content-Security-Policy supporting Operator UI, Tauri Desktop, & WebSockets
        csp_policy = (
            "default-src 'self'; "
            "script-src 'self' 'unsafe-inline' 'unsafe-eval'; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: blob: tauri: asset:; "
            "font-src 'self' data:; "
            "connect-src 'self' ws: wss: tauri: http: https:; "
            "frame-ancestors 'none'; "
            "object-src 'none';"
        )
        headers["Content-Security-Policy"] = csp_policy

        # Only set HSTS when HTTPS / secure cookies are enabled in deployment environment
        if self.settings.session_cookie_secure:
            headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"

        return response
