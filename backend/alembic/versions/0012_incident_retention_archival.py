"""Create Stage IM2-D retention policy, holds, archival tables, and seed retention permissions.

Revision ID: 0012_incident_retention_archival
Revises: 0011_incident_export_pdf_format
"""

from datetime import UTC, datetime
from typing import Sequence, Union
from uuid import NAMESPACE_URL, uuid5

import sqlalchemy as sa
from alembic import op

revision: str = "0012_incident_retention_archival"
down_revision: Union[str, None] = "0011_incident_export_pdf_format"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def stable_id(kind: str, key: str) -> str:
    return str(uuid5(NAMESPACE_URL, f"aeroguard:{kind}:{key}"))


def upgrade() -> None:
    # 1. Create incident_retention_policies table
    op.create_table(
        "incident_retention_policies",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("policy_name", sa.String(128), nullable=False, unique=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("incident_retention_days", sa.Integer(), nullable=False, server_default="90"),
        sa.Column("export_retention_days", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("minimum_archive_age_days", sa.Integer(), nullable=False, server_default="30"),
        sa.Column("minimum_purge_age_days", sa.Integer(), nullable=False, server_default="180"),
        sa.Column("require_archive_before_purge", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("require_supervisor_approval", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("dry_run_by_default", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("created_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("updated_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_incident_retention_policies_enabled", "incident_retention_policies", ["enabled"])

    # 2. Create incident_retention_holds table
    op.create_table(
        "incident_retention_holds",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.Text(), nullable=False),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="1"),
        sa.Column("placed_by", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("placed_at", sa.DateTime(), nullable=False),
        sa.Column("released_by", sa.String(36), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("released_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_incident_retention_holds_incident_id", "incident_retention_holds", ["incident_id"])
    op.create_index("ix_incident_retention_holds_active", "incident_retention_holds", ["active"])

    # 3. Create incident_archives table
    op.create_table(
        "incident_archives",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("archive_number", sa.String(64), nullable=False, unique=True),
        sa.Column("incident_id", sa.String(36), sa.ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False),
        sa.Column("policy_id", sa.String(36), sa.ForeignKey("incident_retention_policies.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sha256_checksum", sa.String(64), nullable=False),
        sa.Column("file_size_bytes", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("archive_format", sa.String(16), nullable=False, server_default="JSON"),
        sa.Column("payload_data", sa.Text(), nullable=False),
        sa.Column("archived_at", sa.DateTime(), nullable=False),
        sa.Column("archived_by", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("verified_at", sa.DateTime(), nullable=True),
    )
    op.create_index("ix_incident_archives_archive_number", "incident_archives", ["archive_number"], unique=True)
    op.create_index("ix_incident_archives_incident_id", "incident_archives", ["incident_id"])
    op.create_index("ix_incident_archives_archived_at", "incident_archives", ["archived_at"])

    # 4. Add archival columns to incidents table
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.add_column(sa.Column("archival_state", sa.String(32), nullable=False, server_default="ACTIVE"))
        batch_op.add_column(sa.Column("archived_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_incidents_archival_state", ["archival_state"])

    # 5. Seed default retention permissions
    conn = op.get_bind()
    now_str = datetime.now(UTC).replace(tzinfo=None).isoformat()

    new_permissions = [
        ("incidents.retention.read", "Allows reading retention policies, holds, and eligibility evaluations"),
        ("incidents.archive", "Allows triggering explicit incident archival"),
        ("incidents.purge", "Allows executing privileged retention purge operations"),
    ]

    for key, desc in new_permissions:
        perm_id = stable_id("permission", key)
        perm_exists = conn.execute(
            sa.text("SELECT 1 FROM permissions WHERE key = :key"), {"key": key}
        ).fetchone()

        if not perm_exists:
            conn.execute(
                sa.text(
                    "INSERT INTO permissions (id, key, resource, action, description, created_at) "
                    "VALUES (:id, :key, 'incidents', :action, :desc, :created_at)"
                ),
                {
                    "id": perm_id,
                    "key": key,
                    "action": key.split(".")[-1],
                    "desc": desc,
                    "created_at": now_str,
                },
            )

    # 6. Seed Default Retention Policy
    policy_id = stable_id("retention_policy", "DEFAULT_POLICY")
    policy_exists = conn.execute(
        sa.text("SELECT 1 FROM incident_retention_policies WHERE policy_name = 'DEFAULT_POLICY'")
    ).fetchone()

    if not policy_exists:
        conn.execute(
            sa.text(
                "INSERT INTO incident_retention_policies "
                "(id, policy_name, description, enabled, incident_retention_days, export_retention_days, "
                "minimum_archive_age_days, minimum_purge_age_days, require_archive_before_purge, "
                "require_supervisor_approval, dry_run_by_default, created_at, updated_at) "
                "VALUES (:id, 'DEFAULT_POLICY', 'Default AeroGuard Compliance Retention Policy', 1, 90, 180, 30, 180, 1, 1, 1, :created_at, :updated_at)"
            ),
            {
                "id": policy_id,
                "created_at": now_str,
                "updated_at": now_str,
            },
        )


def downgrade() -> None:
    with op.batch_alter_table("incidents") as batch_op:
        batch_op.drop_index("ix_incidents_archival_state")
        batch_op.drop_column("archived_at")
        batch_op.drop_column("archival_state")

    op.drop_table("incident_archives")
    op.drop_table("incident_retention_holds")
    op.drop_table("incident_retention_policies")
