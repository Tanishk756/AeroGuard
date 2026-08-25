"""Database connectivity tests."""

from sqlalchemy import text

from app.database.session import SessionLocal


def test_database_connectivity():
    with SessionLocal() as session:
        assert session.execute(text("SELECT 1")).scalar_one() == 1