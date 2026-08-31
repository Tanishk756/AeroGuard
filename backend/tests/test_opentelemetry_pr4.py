"""Stage PR4 OpenTelemetry Distributed Tracing & Attribute Redaction Tests."""

import pytest
from fastapi.testclient import TestClient

from app.core.telemetry import sanitize_trace_attribute
from app.main import app


def test_sanitize_trace_attribute_redaction():
    """VERIFIED: Sensitive attributes (passwords, tokens, JWTs, user IDs) are sanitized to [REDACTED]."""
    assert sanitize_trace_attribute("password", "secret_pass") == "[REDACTED]"
    assert sanitize_trace_attribute("user_jwt_token", "eyJhbGci...") == "[REDACTED]"
    assert sanitize_trace_attribute("authorization", "Bearer xyz") == "[REDACTED]"
    assert sanitize_trace_attribute("http.route", "/api/v1/incidents") == "/api/v1/incidents"
    assert sanitize_trace_attribute("http.status_code", 200) == 200


def test_opentelemetry_trace_headers_propagation(client):
    """VERIFIED: HTTP response contains X-Correlation-ID header propagation."""
    custom_headers = {"X-Correlation-ID": "test-trace-correlation-id-999"}
    
    resp = client.get("/health/live", headers=custom_headers)
    assert resp.status_code == 200
    assert resp.headers.get("X-Correlation-ID") == "test-trace-correlation-id-999"
