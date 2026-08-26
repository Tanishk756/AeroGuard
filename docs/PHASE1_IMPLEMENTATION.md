# Stage B Backend Foundation

Stage B establishes the application core independently of Tauri:

```text
React/Vite frontend -> FastAPI backend -> SQLAlchemy -> SQLite
                                      \-> Alembic migrations
```

## Delivered

- FastAPI application under `backend/app` with versioned router organization.
- `GET /api/v1/health`, including a real database `SELECT 1` connectivity check.
- `GET /api/v1/system/info`, reporting runtime and configured application values.
- Typed Pydantic settings loaded from `AEROGUARD_*` environment variables, with safe development defaults.
- SQLAlchemy engine/session setup for SQLite and an Alembic baseline migration with no application tables.
- Structured API errors with an error code, message, and correlation ID. Unexpected errors do not expose stack traces.
- Basic application logging that does not include credentials or secret values.
- Pytest coverage for startup, both routes, database connectivity, and configuration validation.

Stage C adds secure authentication in a separate migration and does not change
the Stage B baseline. It uses Argon2id password hashes and opaque random
server-side sessions stored as SHA-256 hashes, with login, logout, and current
user routes under `/api/v1`.

Stage D adds deterministic RBAC vocabulary and role-permission assignments in
`0003_rbac.py`, live permission dependencies, protected system information, and
the RBAC management API foundation. Stage E adds local append-only audit
events, transaction-aware security event recording, and the read-only audit API.
Stage F1 then adds operational persistence, Stage F2 adds sensor
abstraction and validated single-detection ingestion without tracking logic,
Stage F3 delivers detection association, deterministic track lifecycle
management, and read-only track query endpoints, Stage F4 delivers
multi-sensor kinematic fusion, track quality scoring, 2D/3D geofencing,
deterministic operational threat prioritization, alert generation/deduplication,
and read-only intelligence query APIs, Stage F5 delivers the scenario
management and deterministic simulation engine driving synthetic multi-sensor
observations into the live operational pipeline, Stage F6 delivers
the historical operations, unified timeline aggregation, descriptive SQL analytics,
and deterministic virtual-clock replay and comparison subsystem, Stage UI1
delivers the Operator Console frontend foundation, Stage UI2 delivers the
Operational Map & Mission Workspace, and Stage UI3 delivers Mission Operations & Interaction.

## Windows commands

From `C:\AeroGuard`:

```powershell
.\.venv\Scripts\python.exe -m pip install -r .\backend\requirements.txt
.\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir .\backend --reload
```

The development API is then available at:

- `http://127.0.0.1:8000/api/v1/health`
- `http://127.0.0.1:8000/api/v1/system/info`

## Deferred scope

Authentication, RBAC, audit logging, sensors, simulation, AI, frontend
integration, and later application tables are outside Stage B. Tauri and native
integration, and later application tables are outside Stage B. Tauri and native
packaging are also temporarily deferred because Windows Application Control is
blocking `cargo.exe`. No Windows security policy or Rust installation changes
are part of this stage.