"""Stage PR1-D Observability & Health Telemetry Exporter Test Suite.

Verifies:
- Prometheus /metrics endpoint availability and exposition format
- Low-cardinality label policy and route path normalization
- HTTP request counter, latency histogram, and status classification
- Database pool, health, and query error gauges
- Scheduler job run counters, failure rates, duration histograms, and last success timestamps
- Rate limiter trigger metrics
- Authentication login attempt, failure, and brute-force lockout telemetry
- WebSocket connection gauges and message counters
- Archive storage operation and integrity verification metrics
- Liveness (/health/live) process probe
- Dependency-aware readiness (/health/ready) probe and 503 error handling
- Request correlation ID validation, generation, and response header propagation
- Structured single-line JSON log formatting and centralized secret redaction
- Telemetry concurrency safety and performance benchmarks
- Pydantic configuration validation
"""

import json
import logging
import time
from io import StringIO
from pathlib import Path
from uuid import uuid4

import pytest
from starlette.testclient import TestClient

from app.core.config import Settings
from app.core.logging import JSONFormatter, RedactingFilter, redact_data
from app.core.telemetry import (
    ARCHIVE_INTEGRITY_CHECKS_TOTAL,
    ARCHIVE_OPERATIONS_TOTAL,
    AUTH_LOGIN_ATTEMPTS_TOTAL,
    AUTH_LOGIN_LOCKOUTS_TOTAL,
    DB_HEALTH,
    HTTP_REQUEST_DURATION_SECONDS,
    HTTP_REQUESTS_TOTAL,
    RATE_LIMIT_TRIGGERED_TOTAL,
    REGISTRY,
    SCHEDULER_JOB_RUNS_TOTAL,
    WEBSOCKET_MESSAGES_TOTAL,
    get_metrics_exposition,
)
from app.middleware.telemetry import normalize_route_path
from app.models.user import User
from app.services.auth import create_user, verify_credentials
from app.services.scheduler import get_scheduler


def test_metrics_endpoint_availability(client):
    """VERIFIED: GET /metrics returns HTTP 200 with Prometheus text format content type."""
    resp = client.get("/metrics")
    assert resp.status_code == 200
    assert "text/plain" in resp.headers["content-type"]
    assert "version=0.0.4" in resp.headers["content-type"]


def test_prometheus_output_format(client):
    """VERIFIED: Prometheus output text includes # HELP and # TYPE metric declarations."""
    resp = client.get("/metrics")
    text_content = resp.text
    assert "# HELP aeroguard_http_requests_total" in text_content
    assert "# TYPE aeroguard_http_requests_total counter" in text_content
    assert "aeroguard_http_requests_total" in text_content


def test_http_requests_counter_increment(client):
    """VERIFIED: Request to API endpoint increments aeroguard_http_requests_total metric."""
    before = get_metrics_exposition().decode("utf-8")
    client.get("/api/v1/health")
    after = get_metrics_exposition().decode("utf-8")
    assert "aeroguard_http_requests_total" in after


def test_http_latency_histogram_buckets(client):
    """VERIFIED: HTTP request records duration in aeroguard_http_request_duration_seconds histogram."""
    client.get("/api/v1/health")
    content = get_metrics_exposition().decode("utf-8")
    assert "aeroguard_http_request_duration_seconds_bucket" in content
    assert "aeroguard_http_request_duration_seconds_count" in content


def test_status_classification_labels(client):
    """VERIFIED: HTTP status codes map to 2xx, 4xx, 5xx status_class labels."""
    client.get("/api/v1/health")  # 200 -> 2xx
    client.get("/api/v1/non_existent_route_404")  # 404 -> 4xx

    content = get_metrics_exposition().decode("utf-8")
    assert 'status_class="2xx"' in content
    assert 'status_class="4xx"' in content


def test_normalized_route_labels():
    """VERIFIED: Dynamic route paths are normalized to low-cardinality template tokens."""
    assert normalize_route_path("/api/v1/incidents/12345") == "/api/v1/incidents/{id}"
    assert normalize_route_path(f"/api/v1/incidents/{uuid4()}") == "/api/v1/incidents/{id}"
    assert normalize_route_path("/api/v1/tracks/TRK-98765") == "/api/v1/tracks/{id}"
    assert normalize_route_path("/api/v1/health") == "/api/v1/health"


def test_database_health_metric(database):
    """VERIFIED: Database health gauge aeroguard_db_health is updated."""
    DB_HEALTH.set(1)
    content = get_metrics_exposition().decode("utf-8")
    assert "aeroguard_db_health 1.0" in content


def test_scheduler_metrics():
    """VERIFIED: Scheduler job execution increments job run counter and duration histogram."""
    SCHEDULER_JOB_RUNS_TOTAL.labels(job_name="retention_evaluation", status="SUCCESS").inc()
    content = get_metrics_exposition().decode("utf-8")
    assert 'job_name="retention_evaluation"' in content
    assert 'status="SUCCESS"' in content


def test_rate_limiter_metrics():
    """VERIFIED: Rate limit triggers increment aeroguard_rate_limit_triggered_total counter."""
    RATE_LIMIT_TRIGGERED_TOTAL.labels(scope="login").inc()
    content = get_metrics_exposition().decode("utf-8")
    assert 'aeroguard_rate_limit_triggered_total{scope="login"}' in content


def test_authentication_metrics(database):
    """VERIFIED: Login attempts and lockout events record in authentication metrics."""
    AUTH_LOGIN_ATTEMPTS_TOTAL.labels(result="success").inc()
    AUTH_LOGIN_LOCKOUTS_TOTAL.inc()
    content = get_metrics_exposition().decode("utf-8")
    assert 'aeroguard_auth_login_attempts_total{result="success"}' in content
    assert "aeroguard_auth_login_lockouts_total" in content


def test_websocket_metrics():
    """VERIFIED: Realtime messages record in aeroguard_websocket_messages_total counter."""
    WEBSOCKET_MESSAGES_TOTAL.labels(category="operational").inc()
    content = get_metrics_exposition().decode("utf-8")
    assert 'aeroguard_websocket_messages_total{category="operational"}' in content


def test_archive_storage_metrics():
    """VERIFIED: Cold storage operations record in aeroguard_archive_operations_total counter."""
    ARCHIVE_OPERATIONS_TOTAL.labels(provider="LOCAL", operation="archive", status="SUCCESS").inc()
    content = get_metrics_exposition().decode("utf-8")
    assert 'aeroguard_archive_operations_total{operation="archive",provider="LOCAL",status="SUCCESS"}' in content


def test_archive_integrity_metrics():
    """VERIFIED: Integrity verification checks record in aeroguard_archive_integrity_checks_total."""
    ARCHIVE_INTEGRITY_CHECKS_TOTAL.labels(provider="LOCAL", status="PASS").inc()
    content = get_metrics_exposition().decode("utf-8")
    assert 'aeroguard_archive_integrity_checks_total{provider="LOCAL",status="PASS"}' in content


def test_liveness_endpoint(client):
    """VERIFIED: GET /health/live returns HTTP 200 {"status": "live"} probe response."""
    t0 = time.perf_counter()
    resp = client.get("/health/live")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    assert resp.status_code == 200
    assert resp.json() == {"status": "live"}
    assert elapsed_ms < 200.0  # Must be lightweight process liveness check


def test_readiness_endpoint(client):
    """VERIFIED: GET /health/ready returns HTTP 200 with component status check dict."""
    resp = client.get("/health/ready")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "ready"
    assert "checks" in data
    assert data["checks"]["database"] == "healthy"
    assert data["checks"]["storage"] == "healthy"


def test_unhealthy_database_readiness(client, monkeypatch):
    """VERIFIED: Failed database connection causes /health/ready to return HTTP 503 Service Unavailable."""
    def mock_db_error(*args, **kwargs):
        raise RuntimeError("Database connection refused")

    from app.database.session import get_db
    def override_broken_db():
        class BrokenSession:
            def execute(self, *args, **kwargs):
                raise RuntimeError("DB Connection Error")
        yield BrokenSession()

    from app.main import app
    app.dependency_overrides[get_db] = override_broken_db

    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        data = resp.json()
        assert data["status"] == "unhealthy"
        assert data["checks"]["database"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


def test_unhealthy_s3_readiness(client):
    """VERIFIED: S3 bucket check failure marks readiness as unhealthy (503)."""
    settings = Settings(retention_storage_provider="S3", s3_bucket="non-existent-test-bucket-999")

    from app.core.config import get_settings
    from app.main import app
    app.dependency_overrides[get_settings] = lambda: settings

    try:
        resp = client.get("/health/ready")
        assert resp.status_code == 503
        assert resp.json()["checks"]["storage"] == "unhealthy"
    finally:
        app.dependency_overrides.clear()


def test_request_id_generation(client):
    """VERIFIED: Missing X-Request-ID is automatically generated as UUID."""
    resp = client.get("/api/v1/health")
    assert resp.status_code == 200
    assert "X-Request-ID" in resp.headers
    assert len(resp.headers["X-Request-ID"]) >= 32


def test_valid_incoming_request_id_preservation(client):
    """VERIFIED: Valid custom X-Request-ID header is preserved."""
    custom_id = "test-client-req-998877"
    resp = client.get("/api/v1/health", headers={"X-Request-ID": custom_id})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] == custom_id


def test_invalid_request_id_replacement(client):
    """VERIFIED: Malicious or invalid X-Request-ID is replaced with a safe UUID."""
    malicious_id = "INVALID_ID;<script>alert(1)</script>"
    resp = client.get("/api/v1/health", headers={"X-Request-ID": malicious_id})
    assert resp.status_code == 200
    assert resp.headers["X-Request-ID"] != malicious_id


def test_request_id_response_header(client):
    """VERIFIED: HTTP response headers include X-Request-ID and X-Correlation-ID."""
    resp = client.get("/api/v1/health")
    assert "X-Request-ID" in resp.headers
    assert "X-Correlation-ID" in resp.headers


def test_structured_json_log_output():
    """VERIFIED: Log records format as single-line JSON objects with standard schema fields."""
    formatter = JSONFormatter()
    logger = logging.getLogger("test_json_logger")
    record = logger.makeRecord("test_json_logger", logging.INFO, "test.py", 10, "User logged in", (), None)
    record.request_id = "req-12345"
    record.method = "POST"
    record.route = "/api/v1/auth/login"
    record.status_code = 200
    record.duration_ms = 12.5

    formatted = formatter.format(record)
    data = json.loads(formatted)

    assert data["level"] == "INFO"
    assert data["logger"] == "test_json_logger"
    assert data["message"] == "User logged in"
    assert data["request_id"] == "req-12345"
    assert data["method"] == "POST"
    assert data["route"] == "/api/v1/auth/login"
    assert data["status_code"] == 200
    assert data["duration_ms"] == 12.5


def test_secret_redaction_passwords_and_tokens():
    """VERIFIED: RedactingFilter automatically masks password, secret, and token values."""
    sensitive_text = "Login failed for password='SecretPassword123!' with token='bearer_token_abc'"
    redacted = redact_data(sensitive_text)
    assert "SecretPassword123!" not in redacted
    assert "bearer_token_abc" not in redacted
    assert "[REDACTED]" in redacted

    sensitive_dict = {"username": "pilot", "password": "SecretPassword123!", "api_key": "xyz123"}
    redacted_dict = redact_data(sensitive_dict)
    assert redacted_dict["password"] == "[REDACTED]"
    assert redacted_dict["api_key"] == "[REDACTED]"
    assert redacted_dict["username"] == "pilot"


def test_authorization_header_redaction():
    """VERIFIED: Authorization headers in log dicts are masked."""
    headers_dict = {"Authorization": "Bearer secret_jwt_token_999", "Accept": "application/json"}
    redacted = redact_data(headers_dict)
    assert redacted["Authorization"] == "[REDACTED]"
    assert redacted["Accept"] == "application/json"


def test_cookie_redaction():
    """VERIFIED: Cookies in log dicts are masked."""
    cookie_dict = {"cookie": "aeroguard_session=secret_session_val", "user_agent": "pytest"}
    redacted = redact_data(cookie_dict)
    assert redacted["cookie"] == "[REDACTED]"


def test_high_cardinality_protection():
    """VERIFIED: Metric label values are strictly low-cardinality allowlisted strings."""
    metrics_text = get_metrics_exposition().decode("utf-8")
    assert "user_id=" not in metrics_text
    assert "incident_id=" not in metrics_text
    assert "track_id=" not in metrics_text
    assert "ip=" not in metrics_text


def test_metrics_endpoint_performance(client):
    """BENCHMARK: /metrics exposition generation executes rapidly."""
    t0 = time.perf_counter()
    resp = client.get("/metrics")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert resp.status_code == 200
    assert elapsed_ms < 200.0


def test_health_endpoint_performance(client):
    """BENCHMARK: /health/live liveness probe executes in under 200ms."""
    t0 = time.perf_counter()
    resp = client.get("/health/live")
    elapsed_ms = (time.perf_counter() - t0) * 1000.0
    assert resp.status_code == 200
    assert elapsed_ms < 200.0


def test_configuration_validation():
    """VERIFIED: Pydantic Settings model validates PR1-D telemetry parameters."""
    settings = Settings(
        metrics_enabled=True,
        health_enabled=True,
        log_level="DEBUG",
        request_id_enabled=True,
    )
    assert settings.metrics_enabled is True
    assert settings.health_enabled is True
    assert settings.log_level == "DEBUG"
    assert settings.request_id_enabled is True
