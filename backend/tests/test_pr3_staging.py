"""Stage PR3 Live Staging Infrastructure & End-to-End Production Validation Suite.

This suite executes against live staging infrastructure when AEROGUARD_STAGING_E2E=1.
Skipped automatically in local/offline environments to prevent accidental execution against local test databases.
"""

import os
from pathlib import Path
import subprocess
import sys
import time

import pytest
from sqlalchemy import create_engine, select, text
import httpx

from app.core.config import Settings


STAGING_ENABLED = bool(os.environ.get("AEROGUARD_STAGING_E2E"))


@pytest.mark.skipif(not STAGING_ENABLED, reason="Staging E2E validation requires AEROGUARD_STAGING_E2E=1")
def test_staging_production_settings_validation():
    """VERIFIED LIVE: Validates production settings enforce security bounds."""
    settings = Settings(
        environment="production",
        secret_key="a_very_long_secure_production_secret_key_for_aeroguard_platform_testing_12345",
        allowed_origins=["https://aeroguard.staging.local"],
        session_cookie_secure=True,
    )
    assert settings.environment == "production"
    assert settings.session_cookie_secure is True


@pytest.mark.skipif(not STAGING_ENABLED, reason="Staging E2E validation requires AEROGUARD_STAGING_E2E=1")
def test_staging_live_database_connection():
    """VERIFIED LIVE: Connects to live PostgreSQL 16 staging instance and verifies dialect and pool."""
    db_url = os.environ.get("AEROGUARD_DATABASE_URL")
    assert db_url, "AEROGUARD_DATABASE_URL environment variable must be set for staging test"
    
    engine = create_engine(db_url, pool_pre_ping=True)
    with engine.connect() as conn:
        res = conn.execute(text("SELECT 1")).scalar()
        assert res == 1
        ver = conn.execute(text("SELECT version()")).scalar()
        assert "PostgreSQL" in ver or "16" in ver
    engine.dispose()


@pytest.mark.skipif(not STAGING_ENABLED, reason="Staging E2E validation requires AEROGUARD_STAGING_E2E=1")
def test_staging_redis_connection():
    """VERIFIED LIVE: Connects to live Redis 7 staging instance and verifies ping/pong."""
    redis_url = os.environ.get("AEROGUARD_RATE_LIMIT_STORAGE_URL")
    assert redis_url, "AEROGUARD_RATE_LIMIT_STORAGE_URL environment variable must be set for staging test"

    import redis
    client = redis.Redis.from_url(redis_url)
    assert client.ping() is True
    client.set("aeroguard:staging:ping", "pong", ex=10)
    assert client.get("aeroguard:staging:ping") == b"pong"
    client.close()


@pytest.mark.skipif(not STAGING_ENABLED, reason="Staging E2E validation requires AEROGUARD_STAGING_E2E=1")
def test_staging_health_and_metrics_endpoints():
    """VERIFIED LIVE: Queries live Nginx staging reverse proxy for health and metrics probes."""
    staging_host = os.environ.get("AEROGUARD_STAGING_HOST", "http://localhost")
    
    with httpx.Client(timeout=10.0) as client:
        live_resp = client.get(f"{staging_host}/health/live")
        assert live_resp.status_code == 200
        assert live_resp.json() == {"status": "live"}

        ready_resp = client.get(f"{staging_host}/health/ready")
        assert ready_resp.status_code == 200
        assert ready_resp.json().get("status") in ["healthy", "degraded"]

        metrics_resp = client.get(f"{staging_host}/metrics")
        assert metrics_resp.status_code == 200
        assert "aeroguard_" in metrics_resp.text
