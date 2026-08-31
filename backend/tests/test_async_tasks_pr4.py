"""Stage PR4 Asynchronous Task Processing & Background Worker Unit Tests."""

import time
import pytest
from fastapi.testclient import TestClient

from app.core.tasks import TaskQueueManager, TaskStatus, TaskRecord
from app.main import app


@pytest.fixture
def manager():
    return TaskQueueManager()


def test_task_lifecycle_success(manager):
    """VERIFIED: Task moves from QUEUED -> RUNNING -> SUCCEEDED upon completion."""
    record = manager.create_task("test_job", max_retries=2)
    assert record.status == TaskStatus.QUEUED
    assert record.task_type == "test_job"

    def worker_fn():
        time.sleep(0.05)
        return {"records_processed": 42}

    manager.execute_async(record.task_id, worker_fn)
    time.sleep(0.15)

    updated = manager.get_task(record.task_id)
    assert updated is not None
    assert updated.status == TaskStatus.SUCCEEDED
    assert updated.result_metadata == {"records_processed": 42}


def test_task_max_retries_exhaustion(manager):
    """VERIFIED: Task retries up to max_retries before transitioning to FAILED."""
    record = manager.create_task("failing_job", max_retries=1)

    def failing_fn():
        raise RuntimeError("Permanent failure test")

    manager.execute_async(record.task_id, failing_fn)
    time.sleep(0.2)

    updated = manager.get_task(record.task_id)
    assert updated is not None
    assert updated.status == TaskStatus.FAILED
    assert "Permanent failure test" in (updated.error_message or "")


def test_async_export_routes(client, database, rbac_user):
    """VERIFIED: POST /export/async returns HTTP 202 Accepted and GET /export/tasks/{task_id} status."""
    from sqlalchemy import select
    from app.models.role import Role
    role = database.scalar(select(Role).where(Role.name == "OPERATIONS_ADMIN"))
    if role and role not in rbac_user.roles:
        rbac_user.roles.append(role)
        database.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert login.status_code == 200
    
    # Request async export
    resp = client.post(
        "/api/v1/incidents/export/async",
        json={"format": "JSON", "limit": 10},
    )
    assert resp.status_code == 202
    data = resp.json()
    assert "task_id" in data
    assert data["status"] in ["QUEUED", "RUNNING", "SUCCEEDED"]
    task_id = data["task_id"]

    time.sleep(0.1)

    # Retrieve task status
    status_resp = client.get(f"/api/v1/incidents/export/tasks/{task_id}")
    assert status_resp.status_code == 200
    status_data = status_resp.json()
    assert status_data["task_id"] == task_id
    assert status_data["task_type"] == "incident_export"
