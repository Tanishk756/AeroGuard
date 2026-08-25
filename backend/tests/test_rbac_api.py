"""RBAC management API security tests."""

from sqlalchemy import select

from app.models.role import Role
from app.models.user import User


def test_management_api_requires_permission_and_supports_role_crud(client, database, rbac_user):
    client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    assert client.get("/api/v1/roles").status_code == 403
    super_admin = database.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    rbac_user.roles.append(super_admin)
    database.commit()

    created = client.post("/api/v1/roles", json={"name": "API_TEST_ROLE", "description": "API test"})
    assert created.status_code == 201
    role_id = created.json()["id"]
    assert client.get(f"/api/v1/roles/{role_id}").status_code == 200
    assert client.patch(f"/api/v1/roles/{role_id}", json={"description": "Updated"}).status_code == 200
    assert client.delete(f"/api/v1/roles/{role_id}").status_code == 204
    assert client.get("/api/v1/permissions").status_code == 200


def test_user_role_assignment_and_revocation_api(client, database, rbac_user):
    client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    super_admin = database.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    rbac_user.roles.append(super_admin)
    target = User(username="api-target", display_name="API Target", email="api-target@example.invalid", password_hash="not-used", status="ACTIVE")
    viewer = database.scalar(select(Role).where(Role.name == "VIEWER"))
    database.add(target)
    database.commit()
    response = client.post(f"/api/v1/users/{target.id}/roles/{viewer.id}")
    assert response.status_code == 200
    assert client.delete(f"/api/v1/users/{target.id}/roles/{viewer.id}").status_code == 204


def test_role_permission_mutation_api_is_restricted_to_custom_roles(client, database, rbac_user):
    client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    super_admin = database.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    rbac_user.roles.append(super_admin)
    database.commit()
    role = client.post("/api/v1/roles", json={"name": "PERMISSION_API_ROLE", "description": "Permission API role"}).json()
    permission = client.get("/api/v1/permissions").json()[0]
    assert client.post(f"/api/v1/roles/{role['id']}/permissions/{permission['id']}").status_code == 204
    assert client.delete(f"/api/v1/roles/{role['id']}/permissions/{permission['id']}").status_code == 204
    system_role = database.scalar(select(Role).where(Role.name == "VIEWER"))
    assert client.post(f"/api/v1/roles/{system_role.id}/permissions/{permission['id']}").status_code == 409