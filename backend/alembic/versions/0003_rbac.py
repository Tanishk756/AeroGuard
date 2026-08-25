"""Create and seed RBAC tables.

Revision ID: 0003_rbac
Revises: 0002_authentication_sessions
"""

from datetime import UTC, datetime
from typing import Sequence, Union
from uuid import uuid5, NAMESPACE_URL

import sqlalchemy as sa
from alembic import op

revision: str = "0003_rbac"
down_revision: Union[str, None] = "0002_authentication_sessions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

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


def stable_id(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"aeroguard:{kind}:{key}"))


def upgrade() -> None:
    bind = op.get_bind()
    op.create_table("roles", sa.Column("id", sa.String(36), primary_key=True), sa.Column("name", sa.String(64), nullable=False, unique=True), sa.Column("description", sa.String(300), nullable=False), sa.Column("is_system", sa.Boolean, nullable=False), sa.Column("created_at", sa.DateTime, nullable=False), sa.Column("updated_at", sa.DateTime, nullable=False))
    op.create_index("ix_roles_name", "roles", ["name"])
    op.create_index("ix_roles_is_system", "roles", ["is_system"])
    op.create_table("permissions", sa.Column("id", sa.String(36), primary_key=True), sa.Column("key", sa.String(100), nullable=False, unique=True), sa.Column("resource", sa.String(50), nullable=False), sa.Column("action", sa.String(50), nullable=False), sa.Column("description", sa.String(300), nullable=False), sa.Column("created_at", sa.DateTime, nullable=False))
    op.create_index("ix_permissions_key", "permissions", ["key"])
    op.create_index("ix_permissions_resource", "permissions", ["resource"])
    op.create_table("user_roles", sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), primary_key=True), sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True))
    op.create_index("ix_user_roles_role_id", "user_roles", ["role_id"])
    op.create_table("role_permissions", sa.Column("role_id", sa.String(36), sa.ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True), sa.Column("permission_id", sa.String(36), sa.ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True))
    op.create_index("ix_role_permissions_permission_id", "role_permissions", ["permission_id"])
    now = datetime.now(UTC).replace(tzinfo=None)
    permission_rows = [{"id": stable_id("permission", key), "key": key, "resource": key.split(".")[0], "action": key.split(".")[1], "description": f"Allows {key}", "created_at": now} for key in PERMISSIONS]
    role_rows = [{"id": stable_id("role", name), "name": name, "description": f"AeroGuard {name} role", "is_system": True, "created_at": now, "updated_at": now} for name in ROLE_PERMISSIONS]
    op.bulk_insert(sa.table("permissions", sa.column("id", sa.String), sa.column("key", sa.String), sa.column("resource", sa.String), sa.column("action", sa.String), sa.column("description", sa.String), sa.column("created_at", sa.DateTime)), permission_rows)
    op.bulk_insert(sa.table("roles", sa.column("id", sa.String), sa.column("name", sa.String), sa.column("description", sa.String), sa.column("is_system", sa.Boolean), sa.column("created_at", sa.DateTime), sa.column("updated_at", sa.DateTime)), role_rows)
    role_permission_rows = [{"role_id": stable_id("role", role), "permission_id": stable_id("permission", permission)} for role, permissions in ROLE_PERMISSIONS.items() for permission in permissions]
    op.bulk_insert(sa.table("role_permissions", sa.column("role_id", sa.String), sa.column("permission_id", sa.String)), role_permission_rows)


def downgrade() -> None:
    op.drop_table("role_permissions")
    op.drop_table("user_roles")
    op.drop_table("permissions")
    op.drop_table("roles")