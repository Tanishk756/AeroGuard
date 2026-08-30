"""Exhaustive RBAC matrix tests for incident management REST endpoints."""

import pytest
from sqlalchemy import select

from app.models.incident import IncidentSeverity, IncidentStatus
from app.models.role import Role
from app.models.user import User
from app.services.auth import create_user


def _create_user_with_role(database, username: str, role_name: str) -> User:
    """Helper to create a fresh user and assign a specific role."""
    user = create_user(database, username, username.title(), f"{username}@example.invalid", "test-password-123")
    role = database.scalar(select(Role).where(Role.name == role_name))
    if role:
        user.roles.append(role)
        database.commit()
    return user


def _login_as(client, username: str):
    from app.core.rate_limiter import reset_rate_limiter
    reset_rate_limiter()
    login = client.post("/api/v1/auth/login", json={"identifier": username, "password": "test-password-123"})
    assert login.status_code == 200


def test_unauthenticated_requests_receive_401(client):
    # Unauthenticated create
    assert client.post("/api/v1/incidents", json={"title": "Test"}).status_code == 401
    # Unauthenticated list
    assert client.get("/api/v1/incidents").status_code == 401
    # Unauthenticated detail
    assert client.get("/api/v1/incidents/some-id").status_code == 401
    # Unauthenticated timeline
    assert client.get("/api/v1/incidents/some-id/timeline").status_code == 401
    # Unauthenticated transitions
    assert client.post("/api/v1/incidents/some-id/acknowledge").status_code == 401
    assert client.post("/api/v1/incidents/some-id/assign", json={"assigned_to": "u1"}).status_code == 401
    assert client.post("/api/v1/incidents/some-id/triage", json={"severity": "HIGH"}).status_code == 401
    assert client.post("/api/v1/incidents/some-id/escalate", json={"reason": "r"}).status_code == 401
    assert client.post("/api/v1/incidents/some-id/de-escalate", json={"reason": "r"}).status_code == 401
    assert client.post("/api/v1/incidents/some-id/resolve", json={"resolution_summary": "s"}).status_code == 401
    assert client.post("/api/v1/incidents/some-id/close", json={"closure_notes": "n"}).status_code == 401
    assert client.post("/api/v1/incidents/some-id/notes", json={"message": "m"}).status_code == 401
    assert client.post("/api/v1/incidents/some-id/actions", json={"category": "PROCEDURE_REVIEW"}).status_code == 401


def test_rbac_incident_creation_permissions(client, database, rbac_user):
    # Viewer cannot create incidents (403)
    viewer = _create_user_with_role(database, "viewer-usr", "VIEWER")
    _login_as(client, "viewer-usr")
    assert client.post("/api/v1/incidents", json={"title": "Unauthorized Test"}).status_code == 403

    # Analyst cannot create incidents (403)
    analyst = _create_user_with_role(database, "analyst-usr", "ANALYST")
    _login_as(client, "analyst-usr")
    assert client.post("/api/v1/incidents", json={"title": "Unauthorized Test"}).status_code == 403

    # Operator can create incidents (201)
    operator = _create_user_with_role(database, "operator-usr", "OPERATOR")
    _login_as(client, "operator-usr")
    res_op = client.post("/api/v1/incidents", json={"title": "Operator Created Incident"})
    assert res_op.status_code == 201

    # Operations Admin can create incidents (201)
    ops_admin = _create_user_with_role(database, "opsadmin-usr", "OPERATIONS_ADMIN")
    _login_as(client, "opsadmin-usr")
    res_admin = client.post("/api/v1/incidents", json={"title": "Admin Created Incident"})
    assert res_admin.status_code == 201


def test_rbac_incident_reading_permissions(client, database, rbac_user):
    # System Admin (without incidents.read) gets 403
    sys_admin = _create_user_with_role(database, "sysadmin-usr", "SYSTEM_ADMIN")
    _login_as(client, "sysadmin-usr")
    assert client.get("/api/v1/incidents").status_code == 403

    # Setup an incident via operator
    operator = _create_user_with_role(database, "operator-reader", "OPERATOR")
    _login_as(client, "operator-reader")
    created = client.post("/api/v1/incidents", json={"title": "Readable Incident"}).json()
    inc_id = created["id"]

    # All operational / analysis roles have incidents.read
    for role_name in ["VIEWER", "RESEARCHER", "ANALYST", "OPERATOR", "OPERATIONS_ADMIN", "SUPER_ADMIN"]:
        usr = _create_user_with_role(database, f"usr-{role_name.lower()}", role_name)
        _login_as(client, f"usr-{role_name.lower()}")

        # List
        assert client.get("/api/v1/incidents").status_code == 200
        # Detail
        assert client.get(f"/api/v1/incidents/{inc_id}").status_code == 200
        # Timeline
        assert client.get(f"/api/v1/incidents/{inc_id}/timeline").status_code == 200


def test_rbac_incident_triage_and_acknowledgment(client, database, rbac_user):
    # Setup incident via Operations Admin
    _create_user_with_role(database, "setup-admin", "OPERATIONS_ADMIN")
    _login_as(client, "setup-admin")
    created = client.post("/api/v1/incidents", json={"title": "Triage Incident"}).json()
    inc_id = created["id"]

    # Viewer lacks incidents.triage (403)
    _create_user_with_role(database, "viewer-triage", "VIEWER")
    _login_as(client, "viewer-triage")
    assert client.post(f"/api/v1/incidents/{inc_id}/acknowledge").status_code == 403
    assert client.post(f"/api/v1/incidents/{inc_id}/triage", json={"severity": "HIGH"}).status_code == 403
    assert client.post(f"/api/v1/incidents/{inc_id}/escalate", json={"reason": "r"}).status_code == 403
    assert client.post(f"/api/v1/incidents/{inc_id}/de-escalate", json={"reason": "r"}).status_code == 403

    # Analyst HAS incidents.triage (200)
    _create_user_with_role(database, "analyst-triage", "ANALYST")
    _login_as(client, "analyst-triage")
    ack_res = client.post(f"/api/v1/incidents/{inc_id}/acknowledge", json={"message": "Analyst acknowledged"})
    assert ack_res.status_code == 200
    triage_res = client.post(f"/api/v1/incidents/{inc_id}/triage", json={"severity": "HIGH", "notes": "Analyst triage"})
    assert triage_res.status_code == 200
    esc_res = client.post(f"/api/v1/incidents/{inc_id}/escalate", json={"reason": "High priority swarm"})
    assert esc_res.status_code == 200
    de_esc_res = client.post(f"/api/v1/incidents/{inc_id}/de-escalate", json={"reason": "Track identified"})
    assert de_esc_res.status_code == 200


def test_rbac_incident_assignment(client, database, rbac_user):
    # Setup incident
    _create_user_with_role(database, "assign-setup-admin", "OPERATIONS_ADMIN")
    _login_as(client, "assign-setup-admin")
    created = client.post("/api/v1/incidents", json={"title": "Assignment Incident"}).json()
    inc_id = created["id"]

    target_analyst = _create_user_with_role(database, "analyst-target", "ANALYST")

    # Analyst lacks incidents.assign (403)
    _create_user_with_role(database, "analyst-assigner", "ANALYST")
    _login_as(client, "analyst-assigner")
    assert client.post(f"/api/v1/incidents/{inc_id}/assign", json={"assigned_to": target_analyst.id}).status_code == 403

    # Operator HAS incidents.assign (200)
    _create_user_with_role(database, "operator-assigner", "OPERATOR")
    _login_as(client, "operator-assigner")
    assign_res = client.post(f"/api/v1/incidents/{inc_id}/assign", json={"assigned_to": target_analyst.id})
    assert assign_res.status_code == 200
    assert assign_res.json()["assigned_to"] == target_analyst.id


def test_rbac_incident_resolution_and_closing(client, database, rbac_user):
    # Setup incident in TRIAGED state
    _create_user_with_role(database, "res-setup-admin", "OPERATIONS_ADMIN")
    _login_as(client, "res-setup-admin")
    created = client.post("/api/v1/incidents", json={"title": "Resolution Incident"}).json()
    inc_id = created["id"]
    client.post(f"/api/v1/incidents/{inc_id}/acknowledge")
    client.post(f"/api/v1/incidents/{inc_id}/triage")

    # Analyst lacks incidents.manage (403 on resolve)
    _create_user_with_role(database, "analyst-resolver", "ANALYST")
    _login_as(client, "analyst-resolver")
    assert client.post(f"/api/v1/incidents/{inc_id}/resolve", json={"resolution_summary": "Done"}).status_code == 403

    # Operator HAS incidents.manage (can resolve)
    _create_user_with_role(database, "operator-resolver", "OPERATOR")
    _login_as(client, "operator-resolver")
    res_resolve = client.post(f"/api/v1/incidents/{inc_id}/resolve", json={"resolution_summary": "Resolved by op"})
    assert res_resolve.status_code == 200
    assert res_resolve.json()["status"] == "RESOLVED"

    # Operator LACKS incidents.close (only OPERATIONS_ADMIN / SUPER_ADMIN can close)
    assert client.post(f"/api/v1/incidents/{inc_id}/close", json={"closure_notes": "Operator close"}).status_code == 403

    # Operations Admin HAS incidents.close (200)
    _login_as(client, "res-setup-admin")
    res_close = client.post(f"/api/v1/incidents/{inc_id}/close", json={"closure_notes": "Admin verified closure"})
    assert res_close.status_code == 200
    assert res_close.json()["status"] == "CLOSED"


def test_rbac_incident_notes_and_actions(client, database, rbac_user):
    # Setup incident
    _create_user_with_role(database, "notes-setup-admin", "OPERATIONS_ADMIN")
    _login_as(client, "notes-setup-admin")
    created = client.post("/api/v1/incidents", json={"title": "Notes & Actions Incident"}).json()
    inc_id = created["id"]

    # Viewer lacks incidents.manage (403)
    _create_user_with_role(database, "viewer-notes", "VIEWER")
    _login_as(client, "viewer-notes")
    assert client.post(f"/api/v1/incidents/{inc_id}/notes", json={"message": "Observation"}).status_code == 403
    assert client.post(f"/api/v1/incidents/{inc_id}/actions", json={"category": "PROCEDURE_REVIEW"}).status_code == 403

    # Operator HAS incidents.manage (201)
    _create_user_with_role(database, "operator-notes", "OPERATOR")
    _login_as(client, "operator-notes")
    note_res = client.post(f"/api/v1/incidents/{inc_id}/notes", json={"message": "Operator note"})
    assert note_res.status_code == 201
    action_res = client.post(
        f"/api/v1/incidents/{inc_id}/actions",
        json={"category": "PROCEDURE_REVIEW", "message": "Standard procedure reviewed"},
    )
    assert action_res.status_code == 201
