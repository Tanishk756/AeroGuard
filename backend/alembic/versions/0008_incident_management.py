"""Create Stage IM1 incident management tables and seed incident RBAC permissions.

Revision ID: 0008_incident_management
Revises: 0007_intelligence_history
"""

from datetime import UTC, datetime
from typing import Sequence, Union
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "0008_incident_management"
down_revision: Union[str, None] = "0007_intelligence_history"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

INCIDENT_PERMISSIONS = [
    "incidents.read",
    "incidents.create",
    "incidents.triage",
    "incidents.assign",
    "incidents.manage",
    "incidents.close",
]

ROLE_INCIDENT_PERMISSIONS = {
    "SUPER_ADMIN": INCIDENT_PERMISSIONS,
    "OPERATIONS_ADMIN": INCIDENT_PERMISSIONS,
    "OPERATOR": [
        "incidents.read",
        "incidents.create",
        "incidents.triage",
        "incidents.assign",
        "incidents.manage",
    ],
    "ANALYST": [
        "incidents.read",
        "incidents.triage",
    ],
    "RESEARCHER": [
        "incidents.read",
    ],
    "VIEWER": [
        "incidents.read",
    ],
}


def stable_id(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"aeroguard:{kind}:{key}"))


def upgrade() -> None:
    # 1. incidents table
    op.create_table(
        "incidents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_number", sa.String(32), nullable=False, unique=True),
        sa.Column("title", sa.String(256), nullable=False),
        sa.Column("description", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="NEW"),
        sa.Column("severity", sa.String(32), nullable=False, server_default="MEDIUM"),
        sa.Column("source", sa.String(32), nullable=False, server_default="OPERATOR"),
        sa.Column("primary_track_id", sa.String(36), sa.ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("primary_group_id", sa.String(64), nullable=True),
        sa.Column("originating_alert_id", sa.String(36), sa.ForeignKey("alerts.id", ondelete="SET NULL"), nullable=True),
        sa.Column("originating_intelligence_event_id", sa.String(64), nullable=True),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("acknowledged_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("assigned_to", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("resolved_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("closed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("acknowledged_at", sa.DateTime, nullable=True),
        sa.Column("assigned_at", sa.DateTime, nullable=True),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
        sa.Column("closed_at", sa.DateTime, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False),
    )
    op.create_index("ix_incidents_status", "incidents", ["status"])
    op.create_index("ix_incidents_severity", "incidents", ["severity"])
    op.create_index("ix_incidents_created_at", "incidents", ["created_at"])
    op.create_index("ix_incidents_assigned_to", "incidents", ["assigned_to"])
    op.create_index("ix_incidents_primary_track_id", "incidents", ["primary_track_id"])
    op.create_index("ix_incidents_primary_group_id", "incidents", ["primary_group_id"])
    op.create_index("ix_incidents_incident_number", "incidents", ["incident_number"], unique=True)

    # 2. incident_events table
    op.create_table(
        "incident_events",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("event_type", sa.String(32), nullable=False),
        sa.Column("actor_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("previous_status", sa.String(32), nullable=True),
        sa.Column("new_status", sa.String(32), nullable=True),
        sa.Column("message", sa.String(1024), nullable=True),
        sa.Column("category", sa.String(64), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
    )
    op.create_index("ix_incident_events_incident_timestamp", "incident_events", ["incident_id", "timestamp"])
    op.create_index("ix_incident_events_actor_timestamp", "incident_events", ["actor_user_id", "timestamp"])
    op.create_index("ix_incident_events_event_type", "incident_events", ["event_type"])

    # 3. Seed incident RBAC permissions and role associations
    now = datetime.now(UTC).replace(tzinfo=None)
    permission_rows = [
        {
            "id": stable_id("permission", key),
            "key": key,
            "resource": key.split(".")[0],
            "action": key.split(".")[1],
            "description": f"Allows {key}",
            "created_at": now,
        }
        for key in INCIDENT_PERMISSIONS
    ]
    op.bulk_insert(
        sa.table(
            "permissions",
            sa.column("id", sa.String),
            sa.column("key", sa.String),
            sa.column("resource", sa.String),
            sa.column("action", sa.String),
            sa.column("description", sa.String),
            sa.column("created_at", sa.DateTime),
        ),
        permission_rows,
    )

    role_permission_rows = [
        {
            "role_id": stable_id("role", role_name),
            "permission_id": stable_id("permission", perm_key),
        }
        for role_name, perms in ROLE_INCIDENT_PERMISSIONS.items()
        for perm_key in perms
    ]
    op.bulk_insert(
        sa.table(
            "role_permissions",
            sa.column("role_id", sa.String),
            sa.column("permission_id", sa.String),
        ),
        role_permission_rows,
    )


def downgrade() -> None:
    # 1. Remove seeded permissions from role_permissions
    perm_ids = [stable_id("permission", key) for key in INCIDENT_PERMISSIONS]
    conn = op.get_bind()
    role_perms_table = sa.table("role_permissions", sa.column("permission_id", sa.String))
    conn.execute(
        role_perms_table.delete().where(role_perms_table.c.permission_id.in_(perm_ids))
    )

    # 2. Remove seeded permissions from permissions
    perms_table = sa.table("permissions", sa.column("id", sa.String))
    conn.execute(
        perms_table.delete().where(perms_table.c.id.in_(perm_ids))
    )

    # 3. Drop incident_events table
    op.drop_index("ix_incident_events_event_type", table_name="incident_events")
    op.drop_index("ix_incident_events_actor_timestamp", table_name="incident_events")
    op.drop_index("ix_incident_events_incident_timestamp", table_name="incident_events")
    op.drop_table("incident_events")

    # 4. Drop incidents table
    op.drop_index("ix_incidents_incident_number", table_name="incidents")
    op.drop_index("ix_incidents_primary_group_id", table_name="incidents")
    op.drop_index("ix_incidents_primary_track_id", table_name="incidents")
    op.drop_index("ix_incidents_assigned_to", table_name="incidents")
    op.drop_index("ix_incidents_created_at", table_name="incidents")
    op.drop_index("ix_incidents_severity", table_name="incidents")
    op.drop_index("ix_incidents_status", table_name="incidents")
    op.drop_table("incidents")
