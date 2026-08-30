"""Double-submit cookie CSRF protection middleware."""

import hmac
import logging
import secrets

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.config import Settings, get_settings

logger = logging.getLogger(__name__)


def generate_csrf_token() -> str:
    """Generate a cryptographically secure random 256-bit hexadecimal CSRF token."""
    return secrets.token_hex(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    """CSRF Protection Middleware using double-submit cookie & constant-time header comparison.

    Enforces X-CSRF-Token header validation on state-modifying HTTP methods (POST, PUT, PATCH, DELETE)
    when authenticated via cookies.
    """

    SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}

    def __init__(self, app, settings: Settings | None = None):
        super().__init__(app)
        self.settings = settings or get_settings()

    async def dispatch(self, request: Request, call_next) -> Response:
        if not self.settings.csrf_protection_enabled:
            return await call_next(request)

        csrf_cookie_name = self.settings.csrf_cookie_name
        csrf_cookie_val = request.cookies.get(csrf_cookie_name)

        # 1. State-Modifying Request Validation
        if request.method not in self.SAFE_METHODS:
            # Check if request uses pure Authorization: Bearer header authentication without session cookie
            auth_header = request.headers.get("Authorization")
            has_session_cookie = self.settings.session_cookie_name in request.cookies

            # Bearer token auth sent via Authorization header without cookie session bypasses browser CSRF
            is_bearer_only = auth_header and auth_header.startswith("Bearer ") and not has_session_cookie

            if not is_bearer_only and has_session_cookie and csrf_cookie_val:
                csrf_header_val = request.headers.get("X-CSRF-Token")

                if not csrf_header_val:
                    logger.warning(f"[CSRF] State-changing {request.method} {request.url.path} rejected: Missing X-CSRF-Token header")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF protection error: Missing X-CSRF-Token header", "error_code": "CSRF_MISSING_HEADER"},
                    )

                if not hmac.compare_digest(csrf_cookie_val, csrf_header_val):
                    logger.warning(f"[CSRF] State-changing {request.method} {request.url.path} rejected: Token mismatch")
                    return JSONResponse(
                        status_code=403,
                        content={"detail": "CSRF protection error: Token mismatch", "error_code": "CSRF_INVALID_TOKEN"},
                    )

        response = await call_next(request)

        # 2. Set/Refresh CSRF Cookie if missing or empty
        if not csrf_cookie_val:
            new_csrf_token = generate_csrf_token()
            response.set_cookie(
                key=csrf_cookie_name,
                value=new_csrf_token,
                httponly=False,  # Must be readable by client JavaScript to attach X-CSRF-Token header
                secure=self.settings.session_cookie_secure,
                samesite=self.settings.session_cookie_samesite,
                path=self.settings.session_cookie_path,
                domain=self.settings.session_cookie_domain,
            )

        return response
