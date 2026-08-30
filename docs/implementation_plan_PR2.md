# Stage PR2 Implementation Plan — Staging Deployment & Production Validation

## Overview
Stage PR2 takes AeroGuard from "deployment-prepared" to "empirically validated in a production-like environment." It establishes an end-to-end staging validation framework to verify multi-container Docker deployment, live PostgreSQL 16 database migrations, live Redis 7 rate-limiting, live MinIO S3 cold archiving, Nginx TLS proxying, failure recovery mechanisms, and automated GitHub Actions CI execution.

---

## Goals
1. Execute multi-container Docker image build and deployment on a Docker-enabled staging environment.
2. Validate PostgreSQL 16 database migrations (`0001` → `0016`) and connection pooling against a live PostgreSQL container.
3. Validate multi-worker rate limiting and key expiration against a live Redis 7 container.
4. Validate archive storage upload, SHA-256 integrity check, and presigned downloads against a live MinIO container.
5. Validate Nginx reverse proxying, SPA routing, WebSocket upgrade streaming (`/api/v1/ws`), and TLS termination.
6. Conduct controlled failure injection tests (database outage, Redis disconnection, storage failure, process crash).
7. Validate daily PostgreSQL backup (`pg_dump`) and restoration procedures.
8. Validate live execution of GitHub Actions CI pipeline (`.github/workflows/ci.yml`).

---

## Non-Goals
- Inventing new business logic, domain models, or API contracts.
- Modifying working application source code without verified empirical justification.
- Operating destructive operations on live production environments.

---

## Staging Architecture

AeroGuard Stage PR2 utilizes a dedicated Docker Compose staging environment (`docker-compose.prod.yml`):

```
                         +-----------------------+
                         |  STAGING LOAD BALANCER|
                         +-----------+-----------+
                                     |
                                     v HTTPS:443 / HTTP:80
                         +-----------+-----------+
                         |  NGINX REVERSE PROXY  |  (TLS Termination, SPA Static Files,
                         +-----------+-----------+   WebSocket Upgrade, Headers)
                                     |
                                     v HTTP:8000 (Private Network: aeroguard_net)
                         +-----------+-----------+
                         |  AEROGUARD BACKEND API |  (Python 3.12 FastAPI + Uvicorn)
                         +-----+-----+-----+-----+
                               |     |     |
            +------------------+     |     +------------------+
            |                        v                        |
            v               +--------+--------+               v
+-----------+-----------+   |   REDIS 7 CACHE |   +-----------+-----------+
|  POSTGRESQL 16 DB     |   |   (Rate Limiter)|   |  MINIO S3 STORAGE     |
|  (Alembic Migrations) |   +-----------------+   |  (Cold Archives)      |
+-----------------------+                         +-----------------------+
```

---

## Infrastructure Requirements

- **Staging Host**: Linux server (Ubuntu 24.04 LTS or Debian 12), 4 vCPU, 8 GB RAM, 50 GB NVMe SSD.
- **Runtime Dependencies**: Docker Engine 26+, Docker Compose v2.27+, Git 2.40+, Curl.
- **Network Access**: Port 80 (HTTP) and Port 443 (HTTPS) exposed for client testing.

---

## Container Validation Plan

1. Build backend image: `docker build -t aeroguard-backend:staging -f Dockerfile.backend .`
2. Build frontend image: `docker build -t aeroguard-frontend:staging -f Dockerfile.frontend .`
3. Inspect image sizes and non-root execution policy (`user: 10001:10001`).
4. Validate container health check probes (`/health/live` returns 200 OK).

---

## PostgreSQL Validation Plan

1. Start PostgreSQL 16 container: `docker compose -f docker-compose.prod.yml up -d postgres`.
2. Execute Alembic init migration worker: `docker compose -f docker-compose.prod.yml run --rm migration`.
3. Verify migration head revision: `alembic current` matches `0016_login_lockout_security.py`.
4. Verify connection pool parameters (`db_pool_size=10`, `db_max_overflow=20`, `db_pool_pre_ping=True`).
5. Execute application startup and verify table creation and relational constraints.

---

## Redis Validation Plan

1. Start Redis 7 container: `docker compose -f docker-compose.prod.yml up -d redis`.
2. Configure `AEROGUARD_RATE_LIMIT_STORAGE_URL=redis://redis:6379/0`.
3. Execute rapid authentication requests to trigger login rate limit (`5/minute`).
4. Verify HTTP 429 response, `Retry-After` header, and `RATE_LIMIT_TRIGGERED_TOTAL` counter increment.
5. Restart Redis container and verify rate limiter recovers cleanly.

---

## MinIO/S3 Validation Plan

1. Start MinIO container: `docker compose -f docker-compose.prod.yml up -d minio`.
2. Configure `AEROGUARD_RETENTION_STORAGE_PROVIDER=S3` and `AEROGUARD_S3_ENDPOINT=http://minio:9000`.
3. Create test incident, generate JSON/PDF export, and execute archival job.
4. Verify object presence in MinIO bucket `aeroguard-archives`.
5. Execute archive integrity check job and verify SHA-256 checksum match (`IntegrityStatus.HEALTHY`).

---

## Nginx/TLS Validation Plan

1. Mount staging TLS certificates into `/etc/nginx/certs/`.
2. Configure Nginx HTTPS 443 server block with HTTP 80 redirect.
3. Test SPA navigation, API routing (`/api/v1/`), WebSocket upgrade (`/api/v1/ws`), `/metrics`, and `/health/ready`.
4. Verify security headers (`X-Content-Type-Options`, `X-Frame-Options`, `Referrer-Policy`).

---

## Security Validation Plan

1. Verify no container runs as `root` user.
2. Verify PostgreSQL, Redis, and MinIO ports are restricted to internal `aeroguard_net` bridge network.
3. Verify environment variables contain no hardcoded secrets in image layers.
4. Verify single-line JSON logs redact passwords, bearer tokens, and credentials.

---

## End-to-End Test Plan

1. Deploy full stack: `docker compose -f docker-compose.prod.yml up -d`.
2. Verify `/health/ready` returns `200 OK` with structured component status.
3. Perform operator login, verify session cookie and CSRF token.
4. Stream operational telemetry over WebSocket (`/api/v1/ws`).
5. Trigger automated scheduler jobs (retention, integrity check, session cleanup).
6. Scrape Prometheus metrics (`/metrics`).

---

## Failure Injection Plan

- **DB Outage**: Stop `postgres` container -> Verify `/health/ready` returns 503 Service Unavailable -> Restart container -> Verify auto-recovery.
- **Redis Outage**: Stop `redis` container -> Verify rate limiter respects `fail_open` policy -> Restart container.
- **Storage Outage**: Stop `minio` container -> Verify archive verification reports `STORAGE_UNAVAILABLE`.
- **Backend Crash**: Kill `uvicorn` PID -> Verify Docker restart policy (`always`) restarts worker.

---

## Backup/Restore Validation

1. Execute database backup: `docker exec aeroguard-postgres pg_dump -U aeroguard_user aeroguard_prod > staging_backup.sql`.
2. Drop staging database and create fresh database instance.
3. Restore database: `psql -U aeroguard_user aeroguard_prod < staging_backup.sql`.
4. Run backend tests to verify 100% data integrity restoration.

---

## Observability Validation

1. Verify `/health/live` probe executes in < 10ms.
2. Verify `/health/ready` probe reports DB and Storage status.
3. Verify `/metrics` renders valid Prometheus text format.
4. Verify single-line JSON log formatting.

---

## CI Pipeline Validation

1. Push commit to test branch on GitHub repository.
2. Observe live GitHub Actions execution of `.github/workflows/ci.yml`.
3. Verify completion of `backend-test`, `frontend-test`, `tauri-test`, and `docker-build` jobs.

---

## Acceptance Criteria

1. Multi-container Docker stack builds and launches cleanly on staging host.
2. Live PostgreSQL 16 migrations execute cleanly without errors.
3. Live Redis 7 rate-limiting operates as expected.
4. Live MinIO S3 object storage handles archival and integrity checks.
5. Nginx proxies HTTP/HTTPS, API, and WebSocket streaming cleanly.
6. Controlled failure injection tests recover without data loss.
7. Database backup (`pg_dump`) and restore cycle succeeds.
8. GitHub Actions CI pipeline executes and passes cleanly on GitHub runners.

---

## Explicit Approval Gate

> [!IMPORTANT]
> **HARD STOP — PR2 implementation requires explicit user approval.**
