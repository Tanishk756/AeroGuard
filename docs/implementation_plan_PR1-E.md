# Stage PR1-E Implementation Plan — Production Containerization, CI/CD & Deployment Artifacts

## Overview
Stage PR1-E closes the remaining production readiness gaps by introducing multi-stage Docker container builds for backend and frontend services, reverse proxy configurations (Nginx/Caddy), automated GitHub Actions CI/CD workflows, production Docker Compose manifests, PostgreSQL and Redis driver dependencies, and environment configuration templates.

---

## Goals
1. Production multi-stage Docker containers for Backend FastAPI and Frontend Operator UI with non-root security execution.
2. Production Nginx reverse proxy configuration handling HTTP/HTTPS TLS termination, static asset delivery, API routing, and WebSocket proxying (`ws://` / `wss://`).
3. Automated GitHub Actions CI workflow (`.github/workflows/ci.yml`) validating backend pytest, frontend typecheck/tests, Tauri cargo check, and Docker container compilation.
4. Docker Compose production orchestration template (`docker-compose.prod.yml`) linking Backend, Frontend Nginx, PostgreSQL 16, Redis 7, and MinIO storage.
5. Update `backend/requirements.txt` with production database (`psycopg2-binary`) and Redis rate limiting (`redis`) drivers.
6. Comprehensive `.env.example` deployment configuration template.

---

## Non-Goals
- Inventing new application features, UI components, or security models.
- Modifying core domain logic in backend, frontend, or Tauri desktop.
- Live deployment to external cloud infrastructure or Kubernetes clusters during this stage.

---

## Proposed Repository Changes

### Dependencies & Configuration
#### [MODIFY] [requirements.txt](file:///C:/AeroGuard/backend/requirements.txt)
Add `psycopg2-binary==2.9.10` and `redis==5.2.1` to enable production PostgreSQL engine connection and multi-worker Redis rate-limiting.

#### [NEW] [.env.example](file:///C:/AeroGuard/.env.example)
Production-ready environment variables template detailing database URLs, security keys, CORS origins, storage credentials, and log levels.

---

### Containerization & Web Server Architecture
#### [NEW] [Dockerfile.backend](file:///C:/AeroGuard/Dockerfile.backend)
Multi-stage Python 3.12 slim Dockerfile running as non-root user `aeroguard:10001` with Uvicorn server, healthcheck probes, and Alembic entrypoint.

#### [NEW] [Dockerfile.frontend](file:///C:/AeroGuard/Dockerfile.frontend)
Multi-stage Node 22 Alpine build compiling `@aeroguard/operator` static assets into Nginx Alpine container image.

#### [NEW] [.dockerignore](file:///C:/AeroGuard/.dockerignore)
Optimized Docker build context exclusion list ignoring `.venv`, `.git`, `node_modules`, `src-tauri/target`, `tests`, and temporary files.

#### [NEW] [nginx.conf](file:///C:/AeroGuard/nginx/nginx.conf)
Production Nginx configuration file handling SPA routing, static caching, API proxying (`/api/v1`), WebSocket upgrades (`/api/v1/ws`), Prometheus metrics (`/metrics`), health probes (`/health/*`), and security response headers.

---

### Orchestration
#### [NEW] [docker-compose.yml](file:///C:/AeroGuard/docker-compose.yml)
Local development Docker Compose setup supporting Backend, Frontend, SQLite/PostgreSQL, and MinIO.

#### [NEW] [docker-compose.prod.yml](file:///C:/AeroGuard/docker-compose.prod.yml)
Production Docker Compose orchestration manifest managing Nginx, Backend API, PostgreSQL 16, Redis 7, and MinIO container services.

---

### CI/CD Workflows
#### [NEW] [ci.yml](file:///C:/AeroGuard/.github/workflows/ci.yml)
GitHub Actions workflow executing on push/PR to `master`:
- **Backend Job**: Python 3.12 setup, dependency installation, pytest suite, `git diff --check`.
- **Frontend Job**: Node 22 setup, `npm ci`, unit tests, `tsc --noEmit` typecheck, `vite build`.
- **Desktop Job**: Rust toolchain setup, `cargo check`, `cargo test`.
- **Docker Job**: Build validation for `Dockerfile.backend` and `Dockerfile.frontend`.

---

### Documentation
#### [NEW] [PR1-E_CHECKPOINT_REPORT.md](file:///C:/AeroGuard/docs/PR1-E_CHECKPOINT_REPORT.md)
Final Stage PR1-E Checkpoint Report documenting container builds, CI results, and deployment guidelines.

---

## Container Architecture

- **Backend Container**: Base `python:3.12-slim`, non-root user `aeroguard` (UID `10001`), exposing port `8000`. Includes health check probe calling `curl -f http://localhost:8000/health/live`.
- **Frontend Container**: Base `nginx:1.27-alpine`, non-root user `nginx`, exposing port `80`/`443`.
- **Security Context**: `read_only` root filesystem where applicable, `drop_capabilities: [ALL]`, `no_new_privileges: true`.

---

## CI Pipeline Design

```
+-------------------------------------------------------------------+
|                     GITHUB ACTIONS TRIGGER                        |
|                     (Push / PR to master)                         |
+----------+------------------+------------------+------------------+
           |                  |                  |
           v                  v                  v
+----------+-------+  +-------+----------+  +----+-------------+
|   BACKEND JOB    |  |   FRONTEND JOB   |  |   DESKTOP JOB    |
| - Python 3.12    |  | - Node.js 22     |  | - Rust 1.80+     |
| - pip install    |  | - npm ci         |  | - cargo check    |
| - pytest suite   |  | - unit tests     |  | - cargo test     |
| - git diff check |  | - typecheck      |  +------------------+
+----------+-------+  | - vite build     |
           |          +-------+----------+
           |                  |
           +--------+---------+
                    |
                    v
          +---------+--------+
          |   DOCKER BUILD   |
          | - Build Backend  |
          | - Build Frontend |
          +------------------+
```

---

## Database Migration Strategy

Database migrations are executed as an automated container entrypoint step before launching Uvicorn worker processes:
```bash
docker run --rm --network aeroguard_net --env-file .env.prod aeroguard-backend alembic upgrade head
```
This ensures database schema is up-to-date at revision `0016` prior to API traffic routing.

---

## Security Hardening

1. Containers execute as unprivileged non-root users (`UID 10001`).
2. Production environment validator enforces `session_cookie_secure=True` and non-empty `allowed_origins`.
3. Secret keys (`AEROGUARD_SECRET_KEY`, `AEROGUARD_DATABASE_URL`, `AEROGUARD_S3_SECRET_KEY`) managed via environment files (`.env`) or secret vault managers.
4. Nginx reverse proxy enforces HSTS, CSP, X-Frame-Options, X-Content-Type-Options, and Referrer-Policy headers.

---

## Rollback Strategy

1. **Application Code Rollback**: Revert Docker image tag (`docker compose pull backend:v0.0.9`) and redeploy services.
2. **Database Rollback**: Revert single schema revisions via `alembic downgrade -1` ONLY after verifying script safety.

---

## Verification Matrix

| Step | Verification Command | Target Result |
| :--- | :--- | :--- |
| **Backend Pytest** | `& .venv\Scripts\python -m pytest backend/tests tests` | 710 Passed, 0 Failures |
| **Frontend Tests** | `npm --prefix apps/operator test` | 349 Passed, 0 Failures |
| **Frontend Typecheck**| `npm --prefix apps/operator run typecheck` | 0 Errors |
| **Frontend Build** | `npm --prefix apps/operator run build` | Clean `dist/` output |
| **Cargo Check** | `cargo check --manifest-path src-tauri/Cargo.toml` | 0 Errors |
| **Docker Build** | `docker build -t aeroguard-backend -f Dockerfile.backend .` | Build Success |
| **Docker Build** | `docker build -t aeroguard-frontend -f Dockerfile.frontend .` | Build Success |
| **Git Hygiene** | `git diff --check` | 0 Formatting Errors |

---

## Explicit User Approval Gate

> [!IMPORTANT]
> **HARD STOP — PR1-E implementation requires explicit user approval.**
