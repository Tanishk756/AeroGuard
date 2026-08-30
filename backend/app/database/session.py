"""SQLAlchemy engine and session dependencies with dialect-aware connection pooling."""

from collections.abc import Generator
import logging
from typing import Any

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import Settings, get_settings
from app.models.audit import AuditEvent

logger = logging.getLogger(__name__)


class DatabaseConfigError(ValueError):
    """Raised when an invalid database configuration or URL scheme is supplied."""


@event.listens_for(Session, "before_flush")
def protect_audit_events(session, flush_context, instances):
    if any(isinstance(instance, AuditEvent) for instance in session.dirty | session.deleted):
        raise ValueError("Audit events are append-only")


def create_database_engine(database_url: str, settings: Settings | None = None, **engine_options) -> Any:
    """Create a dialect-aware SQLAlchemy Engine.

    Fails explicitly on invalid configuration or unsupported URL schemes.
    Does NOT silently alter pool settings or fall back between dialects.
    """
    settings = settings or get_settings()
    clean_url = database_url.strip()

    if not clean_url:
        raise DatabaseConfigError("Database URL must not be empty.")

    is_sqlite = clean_url.startswith(("sqlite://", "sqlite+pysqlite://"))
    is_postgres = clean_url.startswith(("postgresql://", "postgresql+psycopg2://", "postgres://"))

    if not (is_sqlite or is_postgres):
        # Sanitize URL for logging to prevent credential leakage
        scheme_prefix = clean_url.split(":")[0] if ":" in clean_url else "unknown"
        raise DatabaseConfigError(
            f"Unsupported database scheme '{scheme_prefix}'. AeroGuard supports 'sqlite' and 'postgresql' dialects."
        )

    final_options: dict[str, Any] = dict(engine_options)

    if is_sqlite:
        connect_args = final_options.pop("connect_args", {})
        connect_args.setdefault("check_same_thread", False)
        connect_args.setdefault("timeout", int(settings.db_pool_timeout))

        final_options["connect_args"] = connect_args
        final_options.setdefault("pool_pre_ping", settings.db_pool_pre_ping)

        engine_inst = create_engine(clean_url, **final_options)

        @event.listens_for(engine_inst, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

        return engine_inst

    else:
        # PostgreSQL Production Dialect Configuration
        final_options.setdefault("pool_size", settings.db_pool_size)
        final_options.setdefault("max_overflow", settings.db_max_overflow)
        final_options.setdefault("pool_timeout", settings.db_pool_timeout)
        final_options.setdefault("pool_recycle", settings.db_pool_recycle)
        final_options.setdefault("pool_pre_ping", settings.db_pool_pre_ping)

        return create_engine(clean_url, **final_options)


engine = create_database_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()