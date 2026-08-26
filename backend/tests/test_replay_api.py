"""Tests for Replay REST API endpoints."""

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


def test_replay_api_endpoints(client: TestClient, database: Session, rbac_user: User):
    # Unauthenticated
    res = client.post(
        "/api/v1/replay/query",
        json={
            "start_time": "2026-08-26T10:00:00Z",
            "end_time": "2026-08-26T10:05:00Z",
            "step_interval_seconds": 1.0,
            "filters": {},
        },
    )
    assert res.status_code == 401

    assign_role(database, rbac_user, "OPERATIONS_ADMIN")
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )

    # 1. Replay Query
    res = client.post(
        "/api/v1/replay/query",
        json={
            "start_time": "2026-08-26T10:00:00Z",
            "end_time": "2026-08-26T10:05:00Z",
            "step_interval_seconds": 1.0,
            "filters": {},
        },
    )
    assert res.status_code == 200
    data = res.json()
    assert "replay_time" in data
    assert "step_index" in data
    assert "active_tracks" in data
    assert "recent_detections" in data

    # 2. Replay Step
    res_step = client.post(
        "/api/v1/replay/step",
        json={
            "start_time": "2026-08-26T10:00:00Z",
            "current_time": "2026-08-26T10:00:00Z",
            "end_time": "2026-08-26T10:05:00Z",
            "step_interval_seconds": 5.0,
            "steps": 2,
            "filters": {},
        },
    )
    assert res_step.status_code == 200
    step_data = res_step.json()
    assert step_data["step_index"] == 2

    # 3. Replay Compare
    req_body = {
        "start_time": "2026-08-26T10:00:00Z",
        "end_time": "2026-08-26T10:05:00Z",
        "step_interval_seconds": 1.0,
        "filters": {},
    }
    res_comp = client.post(
        "/api/v1/replay/compare",
        json={"request_1": req_body, "request_2": req_body},
    )
    assert res_comp.status_code == 200
    comp_data = res_comp.json()
    assert comp_data["identical"]

    # 4. Invalid time range
    res_bad = client.post(
        "/api/v1/replay/query",
        json={
            "start_time": "2026-08-26T12:00:00Z",
            "end_time": "2026-08-26T10:00:00Z",
            "step_interval_seconds": 1.0,
            "filters": {},
        },
    )
    assert res_bad.status_code == 400
