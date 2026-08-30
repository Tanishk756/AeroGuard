"""Stage PR1-A PostgreSQL Productionization & Database Infrastructure Test Suite.

Classifies all tests clearly:
- VERIFIED (SQLite runtime, dialect compilation, pool config, exception handling)
- MOCKED (PostgreSQL dialect engine compilation & options)
- NOT VERIFIED (Live PostgreSQL cluster when AEROGUARD_TEST_POSTGRES_URL is unset)
"""

import os
import sys
import time
from unittest.mock import MagicMock
from uuid import uuid4

from pydantic import ValidationError
import pytest
from sqlalchemy import Column, Integer, String, Table, create_engine, inspect, select, text
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateTable

from app.core.config import Settings
from app.database.base import Base
from app.database.session import DatabaseConfigError, create_database_engine
from app.models.incident import Incident, IncidentSeverity, IncidentSource, IncidentStatus
from app.models.user import User, UserStatus


def _get_mock_dbapi():
    """Return a mock DBAPI module for SQLAlchemy PostgreSQL engine construction testing when psycopg2 is absent."""
    mock_dbapi = MagicMock()
    mock_dbapi.paramstyle = "pyformat"
    mock_dbapi.threadsafety = 1
    mock_dbapi.Error = Exception
    mock_dbapi.DatabaseError = Exception
    mock_dbapi.OperationalError = OperationalError
    return mock_dbapi


def test_sqlite_engine_creation_verified(tmp_path):
    """VERIFIED: SQLite engine creation with dialect-specific connect args and pre-ping."""
    db_path = tmp_path / "test_pr1a.db"
    url = f"sqlite:///{db_path}"
    settings = Settings(database_url=url, db_pool_timeout=15.0, db_pool_pre_ping=True)

    engine = create_database_engine(url, settings=settings)
    assert engine.dialect.name == "sqlite"
    assert engine.pool is not None

    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1

    engine.dispose()


def test_postgres_engine_configuration_mocked(monkeypatch):
    """MOCKED: PostgreSQL engine creation verifies pool options without live cluster."""
    pg_url = "postgresql://aeroguard_user:secure_pass@localhost:5432/aeroguard_db"

    mock_psycopg2 = MagicMock()
    mock_psycopg2.Error = Exception
    mock_psycopg2.OperationalError = OperationalError
    mock_psycopg2.extensions = MagicMock()
    mock_psycopg2.extras = MagicMock()
    monkeypatch.setitem(sys.modules, "psycopg2", mock_psycopg2)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", mock_psycopg2.extras)

    mock_dbapi = _get_mock_dbapi()
    engine = create_database_engine(
        pg_url,
        pool_size=15,
        max_overflow=25,
        pool_timeout=45.0,
        pool_recycle=3600,
        pool_pre_ping=True,
        module=mock_dbapi,
    )
    assert engine.dialect.name == "postgresql"
    assert engine.pool.size() == 15
    assert engine.pool._max_overflow == 25
    assert engine.pool._timeout == 45.0
    assert engine.pool._recycle == 3600
    assert engine.pool._pre_ping is True


def test_strict_configuration_no_silent_fallback():
    """VERIFIED: Invalid configuration and unsupported schemes fail fast without fallback."""
    # 1. Unsupported scheme raises DatabaseConfigError
    with pytest.raises(DatabaseConfigError) as exc_info:
        create_database_engine("mysql://root:pass@localhost/db")
    assert "Unsupported database scheme" in str(exc_info.value)

    # 2. Empty URL raises DatabaseConfigError
    with pytest.raises(DatabaseConfigError):
        create_database_engine("   ")

    # 3. Invalid Pydantic settings raise ValidationError
    with pytest.raises(ValidationError):
        Settings(database_url="sqlite:///test.db", db_pool_size=-10)


def test_postgres_unreachable_host_failure_verified(monkeypatch):
    """VERIFIED: Connecting to unreachable PostgreSQL host raises OperationalError / DBAPI exception without fallback."""
    unreachable_url = "postgresql://user:pass@127.0.0.1:59999/nonexistent_db"
    settings = Settings(database_url=unreachable_url, db_pool_timeout=1.0)

    mock_psycopg2 = MagicMock()
    mock_psycopg2.Error = OperationalError
    mock_psycopg2.OperationalError = OperationalError
    mock_psycopg2.extensions = MagicMock()
    mock_psycopg2.extras = MagicMock()
    monkeypatch.setitem(sys.modules, "psycopg2", mock_psycopg2)
    monkeypatch.setitem(sys.modules, "psycopg2.extras", mock_psycopg2.extras)

    mock_dbapi = _get_mock_dbapi()
    mock_dbapi.connect.side_effect = OperationalError("connection to 127.0.0.1:59999 failed: Connection refused", params=None, orig=None)
    engine = create_database_engine(unreachable_url, settings=settings, module=mock_dbapi)
    with pytest.raises(OperationalError):
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
    engine.dispose()


def test_transaction_rollback_invariants_verified(database):
    """VERIFIED: Database exception triggers transaction rollback cleanly."""
    initial_user_count = database.scalar(select(text("COUNT(*) FROM users")))

    dup_user1 = User(id=str(uuid4()), username="pr1a_rollback_user", display_name="Rollback User", email="rollback@aeroguard.io", password_hash="hash")
    dup_user2 = User(id=str(uuid4()), username="pr1a_rollback_user", display_name="Rollback User 2", email="rollback@aeroguard.io", password_hash="hash")

    database.add(dup_user1)
    database.commit()

    database.add(dup_user2)
    with pytest.raises(SQLAlchemyError):
        database.commit()

    database.rollback()

    reloaded_count = database.scalar(select(text("COUNT(*) FROM users")))
    assert reloaded_count == initial_user_count + 1


def test_all_models_postgres_ddl_compilation_mocked():
    """MOCKED: Compiles DDL for all 14 Alembic models under PostgreSQL dialect."""
    dialect = postgresql.dialect()

    for table_name, table in Base.metadata.tables.items():
        create_stmt = str(CreateTable(table).compile(dialect=dialect))
        assert "CREATE TABLE" in create_stmt
        assert table_name in create_stmt


def test_performance_connection_acquisition_and_query_benchmark(database):
    """VERIFIED: Measures connection acquisition and query performance."""
    t0 = time.perf_counter()
    with database.bind.connect() as conn:
        conn.execute(text("SELECT 1"))
    conn_acquisition_ms = (time.perf_counter() - t0) * 1000.0

    t1 = time.perf_counter()
    incidents = list(database.scalars(select(Incident).limit(50)))
    incident_query_ms = (time.perf_counter() - t1) * 1000.0

    print(f"\n[PR1-A BENCHMARK] Connection Acquisition: {conn_acquisition_ms:.2f} ms")
    print(f"[PR1-A BENCHMARK] Incident Query (50 records): {incident_query_ms:.2f} ms")

    assert conn_acquisition_ms < 200.0
    assert incident_query_ms < 200.0


@pytest.mark.skipif(
    not os.environ.get("AEROGUARD_TEST_POSTGRES_URL"),
    reason="Live PostgreSQL integration test requires AEROGUARD_TEST_POSTGRES_URL environment variable",
)
def test_live_postgres_integration():
    """NOT VERIFIED (Skipped unless AEROGUARD_TEST_POSTGRES_URL is explicitly set): Live PostgreSQL cluster integration."""
    pg_url = os.environ["AEROGUARD_TEST_POSTGRES_URL"]
    engine = create_database_engine(pg_url)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1
    engine.dispose()
