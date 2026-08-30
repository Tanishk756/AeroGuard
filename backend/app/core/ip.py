"""Safe client IP extraction helper with trusted-proxy verification."""

from fastapi import Request

from app.core.config import Settings, get_settings


def get_client_ip(request: Request, settings: Settings | None = None) -> str:
    """Extract client IP address safely, distinguishing direct connections from trusted reverse proxies.

    Prevents IP spoofing via untrusted X-Forwarded-For or X-Real-IP headers.
    """
    if settings is None:
        settings = get_settings()

    direct_host = request.client.host if request.client else "127.0.0.1"

    # Only inspect forwarded headers if direct connecting host is an explicitly configured trusted proxy
    if settings.trusted_proxies and direct_host in settings.trusted_proxies:
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # First entry in X-Forwarded-For chain is the client IP
            client_ip = forwarded_for.split(",")[0].strip()
            if client_ip:
                return client_ip

        real_ip = request.headers.get("X-Real-IP")
        if real_ip and real_ip.strip():
            return real_ip.strip()

    return direct_host
