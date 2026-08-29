"""RBAC model, service, dependency, and API tests."""

from datetime import UTC, datetime
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.dependencies import require_all_permissions, require_any_permission, require_permission
from app.models.permission import Permission
from app.models.role import Role, role_permissions, user_roles
from app.models.user import User, UserStatus
from app.services.authorization import AuthorizationService
from app.services.rbac import (
    PERMISSIONS,
    ROLE_PERMISSIONS,
    assign_role,
    bootstrap_super_admin,
    create_role,
    revoke_role,
    revoke_permission,
    seed_rbac,
)


def test_seed_is_exact_and_idempotent(database):
    seed_rbac(database)
    seed_rbac(database)

    assert database.query(Role).count() == len(ROLE_PERMISSIONS)
    assert database.query(Permission).count() == len(PERMISSIONS)
    assert set(database.scalars(select(Role.name)).all()) == set(ROLE_PERMISSIONS)
    assert all(role.is_system for role in database.scalars(select(Role)).all())


def test_seed_rejects_corrupted_reserved_role(database):
    seed_rbac(database)
    database.execute(text("UPDATE roles SET is_system = 0 WHERE name = 'VIEWER'"))
    database.commit()
    with pytest.raises(ValueError, match="Reserved role name collision"):
        seed_rbac(database)


def test_seeded_role_permission_mappings_are_exact(database):
    seed_rbac(database)
    for role_name, expected_permissions in ROLE_PERMISSIONS.items():
        role = database.scalar(select(Role).where(Role.name == role_name))
        assert {permission.key for permission in role.permissions} == set(expected_permissions)


def test_duplicate_assignments_are_rejected(database, rbac_user):
    role = create_role(database, "CUSTOM_ROLE", "Custom role")
    permission = database.scalar(select(Permission).where(Permission.key == "tracks.read"))
    rbac_user.roles.append(role)
    role.permissions.append(permission)
    database.commit()

    with pytest.raises(IntegrityError):
        database.execute(user_roles.insert().values(user_id=rbac_user.id, role_id=role.id))
        database.commit()
    database.rollback()
    with pytest.raises(IntegrityError):
        database.execute(role_permissions.insert().values(role_id=role.id, permission_id=permission.id))
        database.commit()
    database.rollback()


def test_permission_dependency_combinators(database, rbac_user):
    role = database.scalar(select(Role).where(Role.name == "VIEWER"))
    rbac_user.roles.append(role)
    database.commit()
    service = AuthorizationService(database)
    assert service.has_permission(rbac_user, "tracks.read")
    assert not service.has_permission(rbac_user, "system.configure")
    assert require_permission("tracks.read")(rbac_user, database) is rbac_user
    assert require_any_permission("system.configure", "tracks.read")(rbac_user, database) is rbac_user
    assert require_all_permissions("tracks.read", "alerts.read")(rbac_user, database) is rbac_user


def test_permission_dependencies_reject_unauthorized_user(database, rbac_user):
    from app.core.errors import AuthError

    with pytest.raises(AuthError) as error:
        require_permission("system.configure")(rbac_user, database)
    assert error.value.code == "AUTH_FORBIDDEN"
    with pytest.raises(AuthError):
        require_any_permission("system.configure", "models.deploy")(rbac_user, database)


def test_role_assignment_requires_subset_of_actor_authority(database, rbac_user):
    viewer = database.scalar(select(Role).where(Role.name == "VIEWER"))
    admin = database.scalar(select(Role).where(Role.name == "SYSTEM_ADMIN"))
    rbac_user.roles.append(viewer)
    target = User(username="target", display_name="Target", email="target@example.invalid", password_hash="not-used", status=UserStatus.ACTIVE)
    database.add(target)
    database.commit()

    with pytest.raises(Exception) as error:
        assign_role(database, rbac_user, target, admin)
    assert getattr(error.value, "code", None) == "AUTH_FORBIDDEN"


def test_role_revocation_requires_actor_authority(database, rbac_user):
    viewer = database.scalar(select(Role).where(Role.name == "VIEWER"))
    target = User(username="target-revoke", display_name="Target", email="target-revoke@example.invalid", password_hash="not-used", status=UserStatus.ACTIVE)
    target.roles.append(viewer)
    database.add(target)
    database.commit()

    with pytest.raises(Exception) as error:
        revoke_role(database, rbac_user, target, viewer)
    assert getattr(error.value, "code", None) == "AUTH_FORBIDDEN"


def test_permission_revocation_requires_actor_authority(database, rbac_user):
    role = create_role(database, "CUSTOM_REVOKE", "Custom role")
    permission = database.scalar(select(Permission).where(Permission.key == "tracks.read"))
    role.permissions.append(permission)
    database.commit()

    with pytest.raises(Exception) as error:
        revoke_permission(database, rbac_user, role, permission)
    assert getattr(error.value, "code", None) == "AUTH_FORBIDDEN"


@pytest.mark.parametrize("reserved_name", sorted({"SUPER_ADMIN", "SYSTEM_ADMIN", "SECURITY_ADMIN", "OPERATIONS_ADMIN", "OPERATOR", "ANALYST", "RESEARCHER", "VIEWER"}))
def test_reserved_system_role_names_are_rejected(database, reserved_name):
    with pytest.raises(ValueError):
        create_role(database, f"  {reserved_name.lower()}  ", "Invalid custom role")


def test_system_roles_cannot_be_modified_or_deleted(database, rbac_user):
    role = database.scalar(select(Role).where(Role.name == "VIEWER"))
    from app.services.rbac import delete_role, update_role

    with pytest.raises(ValueError):
        update_role(database, role, "changed")
    with pytest.raises(ValueError):
        delete_role(database, role)
    role.is_system = False
    with pytest.raises(ValueError):
        database.commit()
    database.rollback()


def test_bootstrap_requires_existing_active_user_and_is_one_time(database, rbac_user):
    assert not database.scalar(select(User).join(User.roles).where(Role.name == "SUPER_ADMIN"))
    bootstrapped = bootstrap_super_admin(database, rbac_user.username, True)
    database.commit()
    assert bootstrapped.id == rbac_user.id
    with pytest.raises(ValueError):
        bootstrap_super_admin(database, rbac_user.username, True)
    with pytest.raises(ValueError):
        bootstrap_super_admin(database, "missing", True)


def test_final_super_admin_role_is_protected(database, rbac_user):
    role = database.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    rbac_user.roles.append(role)
    database.commit()

    with pytest.raises(ValueError):
        revoke_role(database, rbac_user, rbac_user, role)


def test_bootstrap_is_single_winner_under_sqlite_lock(tmp_path):
    from app.database.base import Base
    from app.database.session import create_database_engine
    from app.services.auth import create_user

    database_path = tmp_path / "bootstrap.db"
    engine = create_database_engine(f"sqlite:///{database_path}")
    Base.metadata.create_all(engine)
    with Session(engine) as setup:
        seed_rbac(setup)
        create_user(setup, "bootstrap-one", "Bootstrap One", "one@example.invalid", "bootstrap-one-password")
        create_user(setup, "bootstrap-two", "Bootstrap Two", "two@example.invalid", "bootstrap-two-password")
    engine.dispose()

    def attempt(username):
        worker_engine = create_database_engine(f"sqlite:///{database_path}")
        try:
            with Session(worker_engine) as db:
                user = bootstrap_super_admin(db, username, True)
                db.commit()
                return user.username
        except ValueError:
            return None
        finally:
            worker_engine.dispose()

    with ThreadPoolExecutor(max_workers=2) as executor:
        results = list(executor.map(attempt, ["bootstrap-one", "bootstrap-two"]))
    assert sum(result is not None for result in results) == 1


def test_sqlite_foreign_keys_are_enforced(database):
    with pytest.raises(IntegrityError):
        database.execute(text("INSERT INTO user_roles (user_id, role_id) VALUES ('missing', 'missing')"))
        database.commit()
    database.rollback()


def test_protected_system_info_and_public_health(client, database, rbac_user):
    assert client.get("/api/v1/health").status_code == 200
    assert client.get("/api/v1/system/info").status_code == 401
    login = client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    assert login.status_code == 200
    assert client.get("/api/v1/system/info").status_code == 403

    operator = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    rbac_user.roles.append(operator)
    database.commit()
    assert client.get("/api/v1/system/info").status_code == 200


def test_rbac_management_api_requires_and_enforces_permissions(client, database, rbac_user):
    login = client.post("/api/v1/auth/login", json={"identifier": rbac_user.username, "password": "stage-d-test-password"})
    assert login.status_code == 200
    assert client.get("/api/v1/roles").status_code == 403
    assert client.get("/api/v1/permissions").status_code == 403

    super_admin = database.scalar(select(Role).where(Role.name == "SUPER_ADMIN"))
    rbac_user.roles.append(super_admin)
    database.commit()
    assert client.get("/api/v1/roles").status_code == 200
    assert len(client.get("/api/v1/permissions").json()) == len(PERMISSIONS)
    created = client.post("/api/v1/roles", json={"name": "TEST_ROLE", "description": "Test role"})
    assert created.status_code == 201
    role_id = created.json()["id"]
    assert client.get(f"/api/v1/roles/{role_id}").status_code == 200
    assert client.patch(f"/api/v1/roles/{role_id}", json={"description": "Updated test role"}).status_code == 200
    assert client.delete(f"/api/v1/roles/{role_id}").status_code == 204