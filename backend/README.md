# AeroGuard Backend

Stage B provides the Windows-compatible FastAPI application foundation. It uses
typed environment configuration, SQLAlchemy with SQLite, Alembic migration
infrastructure, structured errors, correlation IDs, and health/system routes.

From the repository root, use the project-local interpreter:

```powershell
.\.venv\Scripts\python.exe -m alembic -c .\backend\alembic.ini upgrade head
.\.venv\Scripts\python.exe -m uvicorn app.main:app --app-dir .\backend --reload
```

The API is available at `/api/v1/health` and `/api/v1/system/info`.
