"""Create Stage IM2 incident export archival table and seed incident export RBAC permission.

Revision ID: 0010_incident_export_archival
Revises: 0009_incident_analytics_indexes
"""

from datetime import UTC, datetime
from typing import Sequence, Union
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "0010_incident_export_archival"
down_revision: Union[str, None] = "0009_incident_analytics_indexes"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def stable_id(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"aeroguard:{kind}:{key}"))


def upgrade() -> None:
    # 1. Create incident_exports table
    op.create_table(
        "incident_exports",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("export_number", sa.String(64), nullable=False, unique=True),
        sa.Column("requested_by", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("format", sa.String(16), nullable=False),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("record_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("filter_params_json", sa.JSON(), nullable=False),
        sa.Column("payload_data", sa.Text(), nullable=False),
    )

    op.create_index("ix_incident_exports_export_number", "incident_exports", ["export_number"], unique=True)
    op.create_index("ix_incident_exports_requested_by", "incident_exports", ["requested_by"])
    op.create_index("ix_incident_exports_created_at", "incident_exports", ["created_at"])
    op.create_index("ix_incident_exports_status", "incident_exports", ["status"])

    # 2. Seed incidents.export permission
    conn = op.get_bind()
    now_str = datetime.now(UTC).replace(tzinfo=None).isoformat()
    perm_id = stable_id("permission", "incidents.export")

    perm_exists = conn.execute(
        sa.text("SELECT 1 FROM permissions WHERE key = 'incidents.export'")
    ).fetchone()

    if not perm_exists:
        conn.execute(
            sa.text(
                "INSERT INTO permissions (id, key, resource, action, description, created_at) "
                "VALUES (:id, 'incidents.export', 'incidents', 'export', 'Allows exporting incident compliance payloads', :created_at)"
            ),
            {"id": perm_id, "created_at": now_str},
        )

    # Assign to SUPER_ADMIN and OPERATIONS_ADMIN roles
    for role_name in ["SUPER_ADMIN", "OPERATIONS_ADMIN"]:
        role_row = conn.execute(
            sa.text("SELECT id FROM roles WHERE name = :name"),
            {"name": role_name},
        ).fetchone()

        if role_row:
            role_id = role_row[0]
            link_exists = conn.execute(
                sa.text(
                    "SELECT 1 FROM role_permissions WHERE role_id = :role_id AND permission_id = :perm_id"
                ),
                {"role_id": role_id, "perm_id": perm_id},
            ).fetchone()

            if not link_exists:
                conn.execute(
                    sa.text(
                        "INSERT INTO role_permissions (role_id, permission_id) VALUES (:role_id, :perm_id)"
                    ),
                    {"role_id": role_id, "perm_id": perm_id},
                )


def downgrade() -> None:
    conn = op.get_bind()
    perm_id = stable_id("permission", "incidents.export")

    # Remove permission assignments
    conn.execute(
        sa.text("DELETE FROM role_permissions WHERE permission_id = :perm_id"),
        {"perm_id": perm_id},
    )
    conn.execute(
        sa.text("DELETE FROM permissions WHERE id = :perm_id"),
        {"perm_id": perm_id},
    )

    # Drop incident_exports table and indexes
    op.drop_index("ix_incident_exports_status", table_name="incident_exports")
    op.drop_index("ix_incident_exports_created_at", table_name="incident_exports")
    op.drop_index("ix_incident_exports_requested_by", table_name="incident_exports")
    op.drop_index("ix_incident_exports_export_number", table_name="incident_exports")
    op.drop_table("incident_exports")
