"""Audit query API tests."""

from sqlalchemy import select

from app.models.audit import AuditEvent
from app.models.role import Role
from app.services.audit import AuditService


def test_audit_api_requires_permission_and_supports_filters_and_cursor(client, database, rbac_user):
    client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    assert client.get("/api/v1/audit/events").status_code == 403
    role = database.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    rbac_user.roles.append(role)
    database.commit()
    for index in range(3):
        AuditService(database).record_event("SECURITY_POLICY_VIOLATION", "test", "FAILURE", metadata={"index": index})
    database.commit()
    response = client.get("/api/v1/audit/events", params={"event_type": "SECURITY_POLICY_VIOLATION", "limit": 2})
    assert response.status_code == 200
    body = response.json()
    assert len(body["items"]) == 2
    assert body["next_cursor"]
    next_page = client.get("/api/v1/audit/events", params={"event_type": "SECURITY_POLICY_VIOLATION", "cursor": body["next_cursor"], "limit": 2})
    assert next_page.status_code == 200
    assert len(next_page.json()["items"]) == 1


def test_correlation_id_is_validated_and_actor_is_server_context(client, database, rbac_user):
    login = client.post("/api/v1/auth/login", headers={"X-Correlation-ID": "bad value"}, json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    assert login.headers["X-Correlation-ID"] != "bad value"
    assert client.get("/api/v1/audit/events", headers={"X-Correlation-ID": "other-user-id"}).status_code == 403
    denied = database.scalars(select(AuditEvent).where(AuditEvent.event_type == "AUTHORIZATION_DENIED")).all()
    assert denied and denied[-1].actor_user_id == rbac_user.id


def test_failed_audit_writer_preserves_authentication_errors(client, monkeypatch):
    def fail(*args, **kwargs):
        raise RuntimeError("writer failed")

    monkeypatch.setattr("app.api.v1.routes.auth.AuditService.record_event", fail)
    response = client.post("/api/v1/auth/login", json={"identifier": "unknown", "password": "wrong"})
    assert response.status_code == 401


def test_failed_audit_writer_preserves_authorization_error(client, database, rbac_user, monkeypatch):
    client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})

    def fail(*args, **kwargs):
        raise RuntimeError("writer failed")

    monkeypatch.setattr("app.dependencies.AuditService.record_event", fail)
    response = client.get("/api/v1/audit/events")
    assert response.status_code == 403
    assert response.json()["error"]["code"] == "AUTH_FORBIDDEN"
