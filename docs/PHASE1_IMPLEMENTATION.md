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
packaging are also temporarily deferred because Windows Application Control is
blocking `cargo.exe`. No Windows security policy or Rust installation changes
are part of this stage.