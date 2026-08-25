"""RBAC management and deterministic seed operations."""

from datetime import UTC, datetime
from uuid import uuid5, NAMESPACE_URL

from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.errors import AuthError
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User, UserStatus
from app.services.authorization import AuthorizationService

PERMISSIONS = [
    "users.read", "users.create", "users.update", "users.disable", "users.delete",
    "roles.read", "roles.create", "roles.update", "roles.delete", "roles.assign", "permissions.read",
    "sessions.read", "sessions.revoke", "system.read", "system.configure",
    "sensors.read", "sensors.configure", "scenarios.read", "scenarios.create", "scenarios.update",
    "scenarios.delete", "scenarios.run", "tracks.read", "alerts.read", "threats.read",
    "models.read", "models.deploy", "audit.read",
]

ROLE_PERMISSIONS = {
    "SUPER_ADMIN": PERMISSIONS,
    "SYSTEM_ADMIN": ["system.read", "system.configure", "users.read", "roles.read", "permissions.read", "sessions.read", "sessions.revoke"],
    "SECURITY_ADMIN": ["users.read", "users.create", "users.update", "users.disable", "roles.read", "roles.assign", "permissions.read", "sessions.read", "sessions.revoke"],
    "OPERATIONS_ADMIN": ["system.read", "users.read", "sessions.read", "sensors.read", "sensors.configure", "scenarios.read", "scenarios.create", "scenarios.update", "scenarios.delete", "scenarios.run", "tracks.read", "alerts.read", "threats.read"],
    "OPERATOR": ["system.read", "sensors.read", "scenarios.read", "scenarios.run", "tracks.read", "alerts.read", "threats.read"],
    "ANALYST": ["system.read", "scenarios.read", "tracks.read", "alerts.read", "threats.read", "models.read"],
    "RESEARCHER": ["system.read", "scenarios.read", "scenarios.create", "scenarios.update", "scenarios.run", "tracks.read", "models.read"],
    "VIEWER": ["system.read", "tracks.read", "alerts.read", "threats.read"],
}
RESERVED_ROLE_NAMES = frozenset(ROLE_PERMISSIONS)


def stable_id(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"aeroguard:{kind}:{key}"))


def seed_rbac(db: Session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    existing_roles = db.scalars(select(Role)).all()
    for role in existing_roles:
        if role.name.strip().upper() in RESERVED_ROLE_NAMES and (role.name != role.name.strip().upper() or not role.is_system):
            raise ValueError(f"Reserved role name collision: {role.name}")
    permissions = {permission.key: permission for permission in db.scalars(select(Permission)).all()}
    for key in PERMISSIONS:
        permission = permissions.get(key)
        if permission is None:
            resource, action = key.split(".", 1)
            permission = Permission(id=stable_id("permission", key), key=key, resource=resource, action=action, description=f"Allows {key}")
            db.add(permission)
            permissions[key] = permission
    roles = {role.name: role for role in db.scalars(select(Role)).all()}
    for name in ROLE_PERMISSIONS:
        role = roles.get(name)
        if role is None:
            role = Role(id=stable_id("role", name), name=name, description=f"AeroGuard {name} role", is_system=True, created_at=now, updated_at=now)
            db.add(role)
            roles[name] = role
    db.flush()
    for name, permission_keys in ROLE_PERMISSIONS.items():
        role = roles[name]
        role.permissions = [permissions[key] for key in permission_keys]
    db.flush()


def _normalize_role_name(name: str) -> str:
    return name.strip().upper()


def _begin_security_transaction(db: Session) -> None:
    db.rollback()
    if db.bind is not None and db.bind.dialect.name == "sqlite":
        db.connection().execute(text("BEGIN IMMEDIATE"))


def _actor_permissions(db: Session, actor: User) -> set[str]:
    if actor.status != UserStatus.ACTIVE:
        raise AuthError("AUTH_FORBIDDEN", "The actor is not active.", 403)
    return AuthorizationService(db).permission_keys(actor)


def _require_actor_authority(db: Session, actor: User, required_permission: str) -> set[str]:
    permissions = _actor_permissions(db, actor)
    if required_permission not in permissions:
        raise AuthError("AUTH_FORBIDDEN", "You do not have authority to perform this action.", 403)
    return permissions


def _require_role_within_authority(actor_permissions: set[str], role: Role) -> None:
    if not {permission.key for permission in role.permissions}.issubset(actor_permissions):
        raise AuthError("AUTH_FORBIDDEN", "The requested role exceeds the actor's authority.", 403)


def ensure_active_super_admin_remains(
    db: Session,
    removing_user_id: str | None = None,
    removing_role_id: str | None = None,
) -> None:
    statement = (
        select(func.count())
        .select_from(User)
        .join(User.roles)
        .where(Role.name == "SUPER_ADMIN", User.status == UserStatus.ACTIVE)
    )
    if removing_user_id is not None:
        statement = statement.where(User.id != removing_user_id)
    if removing_role_id is not None:
        statement = statement.where(Role.id != removing_role_id)
    if (db.scalar(statement) or 0) < 1:
        raise ValueError("The operation would leave no active SUPER_ADMIN")


def ensure_user_can_be_disabled_or_deleted(db: Session, user: User) -> None:
    if user.status == UserStatus.ACTIVE and any(role.name == "SUPER_ADMIN" for role in user.roles):
        ensure_active_super_admin_remains(db, removing_user_id=user.id)


def create_role(db: Session, name: str, description: str) -> Role:
    normalized_name = _normalize_role_name(name)
    if normalized_name in RESERVED_ROLE_NAMES:
        raise ValueError("System role names are reserved")
    role = Role(name=normalized_name, description=description.strip(), is_system=False)
    db.add(role)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Role name is already in use") from exc
    return role


def update_role(db: Session, role: Role, description: str) -> Role:
    if role.is_system:
        raise ValueError("System roles cannot be modified")
    role.description = description
    db.flush()
    return role


def delete_role(db: Session, role: Role) -> None:
    if role.is_system:
        raise ValueError("System roles cannot be deleted")
    db.delete(role)
    db.flush()


def assign_role(db: Session, actor: User, target: User, role: Role) -> None:
    _begin_security_transaction(db)
    actor = db.get(User, actor.id)
    target = db.get(User, target.id)
    role = db.get(Role, role.id)
    actor_permissions = _require_actor_authority(db, actor, "roles.assign")
    _require_role_within_authority(actor_permissions, role)
    if role in target.roles:
        raise ValueError("Role is already assigned")
    target.roles.append(role)
    db.flush()


def revoke_role(db: Session, actor: User, target: User, role: Role) -> None:
    _begin_security_transaction(db)
    actor = db.get(User, actor.id)
    target = db.get(User, target.id)
    role = db.get(Role, role.id)
    actor_permissions = _require_actor_authority(db, actor, "roles.assign")
    _require_role_within_authority(actor_permissions, role)
    if role not in target.roles:
        raise ValueError("Role is not assigned")
    if role.name == "SUPER_ADMIN" and target.status == UserStatus.ACTIVE:
        ensure_active_super_admin_remains(db, removing_user_id=target.id, removing_role_id=role.id)
    target.roles.remove(role)
    db.flush()


def assign_permission(db: Session, actor: User, role: Role, permission: Permission) -> None:
    _begin_security_transaction(db)
    actor = db.get(User, actor.id)
    role = db.get(Role, role.id)
    permission = db.get(Permission, permission.id)
    if role.is_system:
        raise ValueError("System roles cannot be modified")
    actor_permissions = _require_actor_authority(db, actor, "roles.update")
    if permission.key not in actor_permissions:
        raise AuthError("AUTH_FORBIDDEN", "The requested permission exceeds the actor's authority.", 403)
    if permission in role.permissions:
        raise ValueError("Permission is already assigned")
    role.permissions.append(permission)
    db.flush()


def revoke_permission(db: Session, actor: User, role: Role, permission: Permission) -> None:
    _begin_security_transaction(db)
    actor = db.get(User, actor.id)
    role = db.get(Role, role.id)
    permission = db.get(Permission, permission.id)
    if role.is_system:
        raise ValueError("System roles cannot be modified")
    _require_actor_authority(db, actor, "roles.update")
    if permission.key not in AuthorizationService(db).permission_keys(actor):
        raise AuthError("AUTH_FORBIDDEN", "The requested permission exceeds the actor's authority.", 403)
    if permission not in role.permissions:
        raise ValueError("Permission is not assigned")
    role.permissions.remove(permission)
    db.flush()


def bootstrap_super_admin(db: Session, username: str, confirmed: bool) -> User:
    if not confirmed:
        raise ValueError("Bootstrap confirmation is required")
    _begin_security_transaction(db)
    role = db.scalar(select(Role).where(Role.name == "SUPER_ADMIN", Role.is_system.is_(True)))
    user = db.scalar(select(User).where(User.username == username.strip().casefold()))
    if role is None or user is None or user.status != UserStatus.ACTIVE:
        raise ValueError("An existing active user is required")
    existing = db.scalar(select(User).join(User.roles).where(Role.name == "SUPER_ADMIN", User.status == UserStatus.ACTIVE))
    if existing is not None:
        raise ValueError("SUPER_ADMIN bootstrap has already been completed")
    user.roles.append(role)
    db.flush()
    return user