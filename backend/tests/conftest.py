"""Shared backend test fixtures."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))


@pytest.fixture
def database():
    from app.database.base import Base
    from app.database.session import create_database_engine
    import app.models  # noqa: F401

    engine = create_database_engine("sqlite://", poolclass=StaticPool)
    Base.metadata.create_all(engine)
    session = sessionmaker(bind=engine, autoflush=False, autocommit=False)()
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(engine)
        engine.dispose()


@pytest.fixture
def client(database):
    from app.main import app
    from app.database.session import get_db

    def override_get_db():
        yield database

    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as test_client:
            yield test_client
    finally:
        app.dependency_overrides.clear()


@pytest.fixture
def rbac_user(database):
    from app.services.auth import create_user
    from app.services.rbac import seed_rbac

    seed_rbac(database)
    return create_user(database, "stage-d-user", "Stage D User", "stage-d@example.invalid", "stage-d-test-password")