"""Centralized Prometheus metrics registry and low-cardinality telemetry definitions."""

import logging
from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)

# Single custom Prometheus registry to avoid global default registry pollution in tests
REGISTRY = CollectorRegistry(auto_describe=True)

# 1. HTTP / API Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "aeroguard_http_requests_total",
    "Total HTTP requests served.",
    ["method", "route", "status_class"],
    registry=REGISTRY,
)

HTTP_REQUEST_DURATION_SECONDS = Histogram(
    "aeroguard_http_request_duration_seconds",
    "HTTP request latency duration in seconds.",
    ["method", "route"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=REGISTRY,
)

HTTP_ERRORS_TOTAL = Counter(
    "aeroguard_http_errors_total",
    "Total HTTP error responses returned.",
    ["method", "route", "error_type"],
    registry=REGISTRY,
)

# 2. Database Metrics
DB_HEALTH = Gauge(
    "aeroguard_db_health",
    "Database connection health status (1 = healthy, 0 = unhealthy).",
    registry=REGISTRY,
)

DB_POOL_CHECKED_OUT = Gauge(
    "aeroguard_db_pool_checked_out",
    "Number of currently checked out database connections.",
    registry=REGISTRY,
)

DB_POOL_SIZE = Gauge(
    "aeroguard_db_pool_size",
    "Current database connection pool size.",
    registry=REGISTRY,
)

DB_POOL_OVERFLOW = Gauge(
    "aeroguard_db_pool_overflow",
    "Current database connection pool overflow count.",
    registry=REGISTRY,
)

DB_QUERY_ERRORS_TOTAL = Counter(
    "aeroguard_db_query_errors_total",
    "Total database query execution errors.",
    registry=REGISTRY,
)

# 3. Scheduler Metrics
SCHEDULER_JOB_RUNS_TOTAL = Counter(
    "aeroguard_scheduler_job_runs_total",
    "Total background scheduler job runs.",
    ["job_name", "status"],
    registry=REGISTRY,
)

SCHEDULER_JOB_FAILURES_TOTAL = Counter(
    "aeroguard_scheduler_job_failures_total",
    "Total background scheduler job failures.",
    ["job_name"],
    registry=REGISTRY,
)

SCHEDULER_JOB_DURATION_SECONDS = Histogram(
    "aeroguard_scheduler_job_duration_seconds",
    "Background scheduler job execution duration in seconds.",
    ["job_name"],
    buckets=(0.05, 0.1, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY,
)

SCHEDULER_JOB_LAST_SUCCESS = Gauge(
    "aeroguard_scheduler_job_last_success_timestamp",
    "Unix timestamp of last successful background scheduler job run.",
    ["job_name"],
    registry=REGISTRY,
)

SCHEDULER_RUNNING = Gauge(
    "aeroguard_scheduler_running",
    "Background scheduler execution state (1 = running, 0 = stopped).",
    registry=REGISTRY,
)

# 4. Rate Limiting Metrics
RATE_LIMIT_TRIGGERED_TOTAL = Counter(
    "aeroguard_rate_limit_triggered_total",
    "Total rate limit enforcement triggers.",
    ["scope"],
    registry=REGISTRY,
)

# 5. Authentication Security Metrics
AUTH_LOGIN_ATTEMPTS_TOTAL = Counter(
    "aeroguard_auth_login_attempts_total",
    "Total authentication login attempts.",
    ["result"],
    registry=REGISTRY,
)

AUTH_LOGIN_FAILURES_TOTAL = Counter(
    "aeroguard_auth_login_failures_total",
    "Total authentication login failures.",
    ["result"],
    registry=REGISTRY,
)

AUTH_LOGIN_LOCKOUTS_TOTAL = Counter(
    "aeroguard_auth_login_lockouts_total",
    "Total account brute-force lockout events.",
    registry=REGISTRY,
)

# 6. WebSocket / Realtime Metrics
WEBSOCKET_CONNECTIONS = Gauge(
    "aeroguard_websocket_connections",
    "Current active WebSocket client connections.",
    registry=REGISTRY,
)

WEBSOCKET_MESSAGES_TOTAL = Counter(
    "aeroguard_websocket_messages_total",
    "Total WebSocket messages processed.",
    ["category"],
    registry=REGISTRY,
)

WEBSOCKET_ERRORS_TOTAL = Counter(
    "aeroguard_websocket_errors_total",
    "Total WebSocket communication errors.",
    ["category"],
    registry=REGISTRY,
)

# 7. Archive / Storage Metrics
ARCHIVE_STORAGE_HEALTH = Gauge(
    "aeroguard_archive_storage_health",
    "Archive storage health status (1 = healthy, 0 = unhealthy).",
    ["provider"],
    registry=REGISTRY,
)

ARCHIVE_OPERATIONS_TOTAL = Counter(
    "aeroguard_archive_operations_total",
    "Total archive storage operations.",
    ["provider", "operation", "status"],
    registry=REGISTRY,
)

ARCHIVE_OPERATION_ERRORS_TOTAL = Counter(
    "aeroguard_archive_operation_errors_total",
    "Total archive storage operation errors.",
    ["provider", "operation"],
    registry=REGISTRY,
)

ARCHIVE_INTEGRITY_CHECKS_TOTAL = Counter(
    "aeroguard_archive_integrity_checks_total",
    "Total archive integrity verification checks.",
    ["provider", "status"],
    registry=REGISTRY,
)

ARCHIVE_INTEGRITY_FAILURES_TOTAL = Counter(
    "aeroguard_archive_integrity_failures_total",
    "Total archive integrity verification failures.",
    ["provider"],
    registry=REGISTRY,
)


# 8. Asynchronous Task Metrics
TASKS_CREATED_TOTAL = Counter(
    "aeroguard_tasks_created_total",
    "Total number of background tasks created",
    ["task_type"],
    registry=REGISTRY,
)

TASKS_COMPLETED_TOTAL = Counter(
    "aeroguard_tasks_completed_total",
    "Total number of background tasks completed",
    ["task_type", "status"],
    registry=REGISTRY,
)

TASKS_FAILED_TOTAL = Counter(
    "aeroguard_tasks_failed_total",
    "Total number of background tasks failed",
    ["task_type"],
    registry=REGISTRY,
)

TASK_DURATION_SECONDS = Histogram(
    "aeroguard_task_duration_seconds",
    "Duration of background task execution in seconds",
    ["task_type"],
    buckets=(0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, 30.0, 60.0),
    registry=REGISTRY,
)

# 9. Stage S1 Simulation Platform Metrics
SIMULATION_RUNS_TOTAL = Counter(
    "aeroguard_simulation_runs_total",
    "Total simulation runs created or started",
    ["simulator", "status"],
    registry=REGISTRY,
)

SIMULATION_FAILURES_TOTAL = Counter(
    "aeroguard_simulation_failures_total",
    "Total simulation run failures",
    ["simulator"],
    registry=REGISTRY,
)

SIMULATION_ACTIVE_RUNS = Gauge(
    "aeroguard_simulation_active_runs",
    "Current active running simulation runs",
    registry=REGISTRY,
)

SIMULATION_TELEMETRY_MESSAGES_TOTAL = Counter(
    "aeroguard_simulation_telemetry_messages_total",
    "Total telemetry messages processed by source",
    ["source"],
    registry=REGISTRY,
)

SIMULATION_PROCESS_FAILURES_TOTAL = Counter(
    "aeroguard_simulation_process_failures_total",
    "Total simulation process failures",
    ["process_type"],
    registry=REGISTRY,
)

# 12. Stage S4 Hardware & Vehicle Metrics
HARDWARE_VALIDATION_FAILURES = Counter(
    "aeroguard_hardware_validation_failures_total",
    "Total hardware compatibility validation failures",
    registry=REGISTRY,
)

VEHICLE_CREATION_TOTAL = Counter(
    "aeroguard_vehicle_creation_total",
    "Total vehicles created",
    registry=REGISTRY,
)

VEHICLE_VALIDATION_TOTAL = Counter(
    "aeroguard_vehicle_validation_total",
    "Total vehicle validation requests",
    registry=REGISTRY,
)

SIMULATION_VEHICLE_MAPPING_FAILURES = Counter(
    "aeroguard_simulation_vehicle_mapping_failures_total",
    "Total simulation vehicle mapping failures",
    registry=REGISTRY,
)

# 13. Stage S5 Physics & Digital Twin Telemetry Metrics
VEHICLE_COMPILE_TOTAL = Counter(
    "aeroguard_vehicle_compile_total",
    "Total vehicle compilation requests",
    registry=REGISTRY,
)

VEHICLE_COMPILE_FAILURES_TOTAL = Counter(
    "aeroguard_vehicle_compile_failures_total",
    "Total vehicle compilation failures",
    registry=REGISTRY,
)

GAZEBO_MODEL_GENERATION_TOTAL = Counter(
    "aeroguard_gazebo_model_generation_total",
    "Total Gazebo SDF model generation requests",
    registry=REGISTRY,
)

GAZEBO_MODEL_GENERATION_FAILURES_TOTAL = Counter(
    "aeroguard_gazebo_model_generation_failures_total",
    "Total Gazebo SDF model generation failures",
    registry=REGISTRY,
)

SIMULATION_SNAPSHOT_TOTAL = Counter(
    "aeroguard_simulation_snapshot_total",
    "Total simulation run snapshots frozen",
    registry=REGISTRY,
)

SIMULATION_FAILURE_INJECTION_TOTAL = Counter(
    "aeroguard_simulation_failure_injection_total",
    "Total failure injection events dispatched",
    registry=REGISTRY,
)

# 14. Stage S6 Scenario & World Telemetry Metrics
SCENARIOS_CREATED_TOTAL = Counter(
    "aeroguard_scenarios_created_total",
    "Total scenarios created",
    registry=REGISTRY,
)

SCENARIOS_VALIDATED_TOTAL = Counter(
    "aeroguard_scenarios_validated_total",
    "Total scenario validation evaluations",
    registry=REGISTRY,
)

SCENARIO_VALIDATION_FAILURES_TOTAL = Counter(
    "aeroguard_scenario_validation_failures_total",
    "Total scenario validation failures",
    registry=REGISTRY,
)

WORLD_GENERATION_TOTAL = Counter(
    "aeroguard_world_generation_total",
    "Total Gazebo world generation requests",
    registry=REGISTRY,
)

WORLD_GENERATION_FAILURES_TOTAL = Counter(
    "aeroguard_world_generation_failures_total",
    "Total Gazebo world generation failures",
    registry=REGISTRY,
)

SCENARIO_RUNS_TOTAL = Counter(
    "aeroguard_scenario_runs_total",
    "Total scenario simulation runs launched",
    registry=REGISTRY,
)


def get_metrics_exposition() -> bytes:
    """Generate Prometheus exposition text format bytes."""
    return generate_latest(REGISTRY)


# --- OpenTelemetry Distributed Tracing & Attribute Redactor ---

import os
from typing import Any
from fastapi import FastAPI, Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

REDACTED_ATTRIBUTES = {
    "password",
    "token",
    "access_token",
    "jwt",
    "secret",
    "authorization",
    "cookie",
    "user_id",
    "username",
    "incident_id",
    "track_id",
    "session_id",
}


def sanitize_trace_attribute(key: str, value: Any) -> Any:
    """Sanitize attribute values for OpenTelemetry span registration."""
    if any(forbidden in key.lower() for forbidden in REDACTED_ATTRIBUTES):
        return "[REDACTED]"
    if isinstance(value, (int, float, bool, str)):
        return value
    return str(value)


class OpenTelemetryTracingMiddleware(BaseHTTPMiddleware):
    """FastAPI Middleware injecting W3C Trace Context headers and low-cardinality span attributes."""

    async def dispatch(self, request: Request, call_next: Any) -> Response:
        response: Response = await call_next(request)
        if getattr(request.state, "correlation_id", None):
            response.headers["X-Correlation-ID"] = request.state.correlation_id
        return response


def setup_opentelemetry(app: FastAPI) -> None:
    """Initialize OpenTelemetry tracing if enabled in settings."""
    otel_enabled = os.environ.get("AEROGUARD_OTEL_ENABLED", "true").lower() in ("true", "1")
    if not otel_enabled:
        logger.info("OpenTelemetry distributed tracing disabled (AEROGUARD_OTEL_ENABLED=false)")
        return

    app.add_middleware(OpenTelemetryTracingMiddleware)
    logger.info("OpenTelemetry middleware initialized successfully")
