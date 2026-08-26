"""SQLAlchemy engine and session dependencies."""

from collections.abc import Generator

from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.models.audit import AuditEvent


@event.listens_for(Session, "before_flush")
def protect_audit_events(session, flush_context, instances):
    if any(isinstance(instance, AuditEvent) for instance in session.dirty | session.deleted):
        raise ValueError("Audit events are append-only")


def create_database_engine(database_url: str, **engine_options):
    connect_args = {"check_same_thread": False, "timeout": 30} if database_url.startswith("sqlite") else {}
    database_engine = create_engine(database_url, connect_args=connect_args, pool_pre_ping=True, **engine_options)
    if database_url.startswith("sqlite"):
        @event.listens_for(database_engine, "connect")
        def enable_sqlite_foreign_keys(dbapi_connection, connection_record):
            cursor = dbapi_connection.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()
    return database_engine


engine = create_database_engine(get_settings().database_url)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def get_db() -> Generator[Session, None, None]:
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()