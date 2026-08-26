"""Tests for Analytics REST API endpoints."""

from datetime import datetime, timedelta

from fastapi.testclient import TestClient
from sqlalchemy.orm import Session


from sqlalchemy import select

from app.models.role import Role
from app.models.user import User


def assign_role(database, user, role_name: str):
    role = database.scalar(select(Role).where(Role.name == role_name))
    if role not in user.roles:
        user.roles.append(role)
        database.commit()


def test_analytics_api_endpoints(client: TestClient, database: Session, rbac_user: User):
    # Unauthenticated
    res = client.get("/api/v1/analytics/summary?window_start=2026-08-26T10:00:00Z&window_end=2026-08-26T11:00:00Z")
    assert res.status_code == 401

    assign_role(database, rbac_user, "OPERATIONS_ADMIN")
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )

    # 1. Summary
    res = client.get(
        "/api/v1/analytics/summary?window_start=2026-08-26T10:00:00Z&window_end=2026-08-26T11:00:00Z"
    )
    assert res.status_code == 200
    data = res.json()
    assert "detections" in data
    assert "tracks" in data
    assert "alerts" in data
    assert "threats" in data

    # 2. Detections metrics
    res = client.get("/api/v1/analytics/detections")
    assert res.status_code == 200
    assert "total_detections" in res.json()

    # 3. Tracks metrics
    res = client.get("/api/v1/analytics/tracks")
    assert res.status_code == 200
    assert "total_tracks" in res.json()

    # 4. Alerts metrics
    res = client.get("/api/v1/analytics/alerts")
    assert res.status_code == 200
    assert "total_alerts" in res.json()

    # 5. Threats metrics
    res = client.get("/api/v1/analytics/threats")
    assert res.status_code == 200
    assert "total_assessed" in res.json()

    # 6. Invalid time range (start > end)
    res_bad = client.get(
        "/api/v1/analytics/summary?window_start=2026-08-26T12:00:00Z&window_end=2026-08-26T11:00:00Z"
    )
    assert res_bad.status_code == 400
