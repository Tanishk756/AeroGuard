# Implementation Plan — Stage PR1-D: Observability & Health Telemetry Exporter

## Executive Summary
Stage PR1-D establishes production-grade observability, health telemetry, request correlation tracking, and structured JSON logging for the AeroGuard defensive situational awareness platform.

This plan details the design, metrics catalog, label cardinality rules, health endpoints, structured logging architecture, secret redaction controls, and verification strategy required to make AeroGuard operationally diagnosable without altering existing business logic or compromising security.

---

## User Review Required

> [!IMPORTANT]
> **Phase 0 Discovery Findings & Baseline State**:
> - Baseline Commit: `52b9e00` on `master` branch (`master == origin/master`, working tree clean).
> - Previous Stage PR1-C (API security, rate limiting, login lockout, CSRF protection) is fully verified with 100% backend/frontend test pass rate.
> - The codebase currently lacks a Prometheus exposition endpoint, structured JSON log formatter, readiness/liveness separation, and database/scheduler metrics.
> - **Dependency Selection**: We will introduce `prometheus-client` for standard Prometheus metrics formatting and scraping compatibility.

---

## 1. Observability Architecture & Gaps Analysis

### Current State
- `backend/app/core/logging.py`: Basic `logging.basicConfig` plain-text log formatter.
- `backend/app/api/v1/routes/health.py`: Single `/health` route returning DB status string.
- `backend/app/main.py`: `correlation_id_middleware` handling `X-Correlation-ID` header.

### Production Gaps
1. **No Prometheus Metrics Exposition**: Lacks standard `/metrics` endpoint for Prometheus scraping.
2. **No Component Telemetry**: Lacks quantitative metrics for HTTP latencies, DB pool state, background scheduler job runs, rate-limit triggers, auth lockouts, WebSocket connections, and S3 archive operations.
3. **Unseparated Health Check Semantics**: Lacks lightweight `/health/live` (liveness) and dependency-aware `/health/ready` (readiness) endpoints.
4. **Unstructured Logs & Secret Risk**: Plain text logging lacks standardized JSON fields (`request_id`, `duration_ms`, `method`, `route`) and automated secret redaction for sensitive header/payload fields.

---

## 2. Proposed Changes & File Modifications

### Component 1: Telemetry Core & Prometheus Metrics Subsystem

#### `[NEW]` [telemetry.py](file:///C:/AeroGuard/backend/app/core/telemetry.py)
Implements low-cardinality Prometheus metrics registry using `prometheus_client`:
- **HTTP Metrics**:
  - `aeroguard_http_requests_total` (`Counter`, labels: `method`, `route`, `status_class`)
  - `aeroguard_http_request_duration_seconds` (`Histogram`, labels: `method`, `route`)
  - `aeroguard_http_errors_total` (`Counter`, labels: `method`, `route`, `error_type`)
- **Database Metrics**:
  - `aeroguard_db_health` (`Gauge`, 1 = healthy, 0 = unhealthy)
  - `aeroguard_db_pool_checked_out` (`Gauge`)
  - `aeroguard_db_pool_size` (`Gauge`)
  - `aeroguard_db_pool_overflow` (`Gauge`)
  - `aeroguard_db_query_errors_total` (`Counter`)
- **Scheduler Metrics**:
  - `aeroguard_scheduler_job_runs_total` (`Counter`, labels: `job_name`, `status`)
  - `aeroguard_scheduler_job_failures_total` (`Counter`, labels: `job_name`)
  - `aeroguard_scheduler_job_duration_seconds` (`Histogram`, labels: `job_name`)
  - `aeroguard_scheduler_job_last_success_timestamp` (`Gauge`, labels: `job_name`)
  - `aeroguard_scheduler_running` (`Gauge`, 1 = running, 0 = stopped)
- **Rate Limiting Metrics**:
  - `aeroguard_rate_limit_triggered_total` (`Counter`, labels: `scope`)
- **Authentication Security Metrics**:
  - `aeroguard_auth_login_attempts_total` (`Counter`, labels: `result`)
  - `aeroguard_auth_login_failures_total` (`Counter`, labels: `result`)
  - `aeroguard_auth_login_lockouts_total` (`Counter`)
- **WebSocket & Realtime Metrics**:
  - `aeroguard_websocket_connections` (`Gauge`)
  - `aeroguard_websocket_messages_total` (`Counter`, labels: `category`)
  - `aeroguard_websocket_errors_total` (`Counter`, labels: `category`)
- **Archive & S3 Metrics**:
  - `aeroguard_archive_storage_health` (`Gauge`, labels: `provider`)
  - `aeroguard_archive_operations_total` (`Counter`, labels: `provider`, `operation`, `status`)
  - `aeroguard_archive_operation_errors_total` (`Counter`, labels: `provider`, `operation`)
  - `aeroguard_archive_integrity_checks_total` (`Counter`, labels: `provider`, `status`)
  - `aeroguard_archive_integrity_failures_total` (`Counter`, labels: `provider`)

#### `[NEW]` [metrics.py](file:///C:/AeroGuard/backend/app/api/v1/routes/metrics.py)
Exposes `GET /metrics` endpoint serving Prometheus exposition text format.

---

### Component 2: Request Telemetry Middleware & Correlation IDs

#### `[NEW]` [middleware/telemetry.py](file:///C:/AeroGuard/backend/app/middleware/telemetry.py)
ASGI middleware capturing HTTP request duration and status classification:
- Intercepts and validates `X-Request-ID` and `X-Correlation-ID` headers against strict regex `[A-Za-z0-9._:-]{1,64}`. Generates cryptographically safe UUID if missing/invalid.
- Normalizes route paths (e.g., `/api/v1/incidents/{incident_id}` instead of `/api/v1/incidents/12345`) to strictly enforce low-cardinality label policy.
- Records HTTP request counter, latency histogram, and status class (`2xx`, `4xx`, `5xx`).
- Propagates `X-Request-ID` and `X-Correlation-ID` headers on responses.

---

### Component 3: Health & Readiness Subsystem

#### `[MODIFY]` [health.py](file:///C:/AeroGuard/backend/app/api/v1/routes/health.py)
- **`GET /health/live`**: Fast process liveness check (< 5ms). Returns `HTTP 200` with `{"status": "live"}` without external dependency calls.
- **`GET /health/ready`**: Dependency readiness check. Evaluates DB connection (`SELECT 1`) and storage provider (`LOCAL` path or `S3` bucket check). Returns `HTTP 200` with structured component status if healthy, or `HTTP 503` if degraded.
- **`GET /health`**: Preserved for backward compatibility.

---

### Component 4: Structured JSON Logging & Secret Redaction

#### `[MODIFY]` [logging.py](file:///C:/AeroGuard/backend/app/core/logging.py)
- Implements `JSONFormatter` emitting single-line JSON log events containing `timestamp`, `level`, `logger`, `message`, `request_id`, `method`, `route`, `status_code`, `duration_ms`.
- Implements `RedactingFilter` automatically masking patterns matching passwords, bearer tokens, cookies, session secrets, API keys, and S3 credentials.

---

### Component 5: Component Telemetry Integration

#### `[MODIFY]` [config.py](file:///C:/AeroGuard/backend/app/core/config.py)
Adds Pydantic validation settings:
- `metrics_enabled: bool = True` (`AEROGUARD_METRICS_ENABLED`)
- `health_enabled: bool = True` (`AEROGUARD_HEALTH_ENABLED`)
- `log_level: str = "INFO"` (`AEROGUARD_LOG_LEVEL`)
- `request_id_enabled: bool = True` (`AEROGUARD_REQUEST_ID_ENABLED`)

#### `[MODIFY]` [scheduler.py](file:///C:/AeroGuard/backend/app/services/scheduler.py)
Instruments background job executions with job-level metrics (`retention_evaluation`, `archive_integrity_verification`, `expired_session_cleanup`).

#### `[MODIFY]` [rate_limiter.py](file:///C:/AeroGuard/backend/app/core/rate_limiter.py)
Instruments rate limit triggers with `aeroguard_rate_limit_triggered_total` counter.

#### `[MODIFY]` [auth.py](file:///C:/AeroGuard/backend/app/services/auth.py) & [routes/auth.py](file:///C:/AeroGuard/backend/app/api/v1/routes/auth.py)
Instruments login attempts, failures, and account lockouts.

#### `[MODIFY]` [main.py](file:///C:/AeroGuard/backend/app/main.py)
Mounts `TelemetryMiddleware` and includes `/metrics` router.

---

## 3. High-Cardinality Protection & Security Rules

### Low-Cardinality Label Policy
- **HTTP**: `method`, `route` (normalized template), `status_class`.
- **Scheduler**: `job_name` (strictly allowlisted: `retention_evaluation`, `archive_integrity_verification`, `expired_session_cleanup`), `status`.
- **Rate Limit**: `scope` (`login`, `auth`, `default`, `health`).
- **Auth**: `result` (`success`, `invalid_credentials`, `locked`, `rate_limited`).
- **Archive**: `provider` (`LOCAL`, `S3`), `operation` (`archive`, `retrieve`, `verify`, `delete`, `presigned_url`).
- **STRICT PROHIBITION**: Zero user IDs, usernames, IP addresses, incident IDs, track IDs, session tokens, or raw request payloads in metric labels.

---

## 4. Verification Plan

### Automated Test Suite
Created `backend/tests/test_observability_pr1d.py` covering:
1. `GET /metrics` availability and Prometheus text format.
2. HTTP request counters, latency histograms, and status classification.
3. Normalized route label formatting.
4. Database health gauges & pool state metrics.
5. Scheduler job run counters & duration histograms.
6. Rate limiter trigger metrics.
7. Authentication login attempt, failure & lockout metrics.
8. WebSocket connection & message counters.
9. Archive operation & integrity metrics.
10. `GET /health/live` process check.
11. `GET /health/ready` dependency check (DB + S3).
12. Unhealthy database readiness failure (`HTTP 503`).
13. Request ID generation, validation, and header propagation.
14. Structured JSON logging output formatting.
15. Secret redaction (passwords, bearer tokens, cookies, S3 keys).
16. Concurrent request metrics safety.
17. Performance benchmarking (metrics increment < 0.05ms, `/health/live` < 10ms).

### Full Suite Regression
- Full backend pytest suite (`pytest backend/tests tests`).
- Frontend test suite (`npm --prefix apps/operator test`).
- Frontend typecheck and build (`npm --prefix apps/operator run typecheck`, `npm --prefix apps/operator run build`).
- Desktop Tauri check & test (`cargo check`, `cargo test`).
- `git diff --check` and secret credentials scan.
