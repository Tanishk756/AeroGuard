"""Add incident_archive_integrity_checks table.

Revision ID: 0014_incident_archive_integrity
Revises: 0013_incident_s3_retention_storage
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_incident_archive_integrity"
down_revision: Union[str, None] = "0013_incident_s3_retention_storage"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "incident_archive_integrity_checks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("archive_id", sa.String(36), nullable=True),
        sa.Column("archive_number", sa.String(64), nullable=False),
        sa.Column("incident_id", sa.String(36), nullable=True),
        sa.Column("storage_provider", sa.String(32), nullable=False, server_default="LOCAL"),
        sa.Column("storage_location", sa.String(512), nullable=True),
        sa.Column("status", sa.String(32), nullable=False, server_default="HEALTHY"),
        sa.Column("expected_checksum", sa.String(64), nullable=True),
        sa.Column("observed_checksum", sa.String(64), nullable=True),
        sa.Column("expected_size_bytes", sa.Integer(), nullable=True),
        sa.Column("observed_size_bytes", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("error_code", sa.String(64), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("checked_at", sa.DateTime(), nullable=False),
    )
    op.create_index("ix_archive_integrity_checks_archive_id", "incident_archive_integrity_checks", ["archive_id"])
    op.create_index("ix_archive_integrity_checks_status", "incident_archive_integrity_checks", ["status"])
    op.create_index("ix_archive_integrity_checks_checked_at", "incident_archive_integrity_checks", ["checked_at"])


def downgrade() -> None:
    op.drop_index("ix_archive_integrity_checks_checked_at", table_name="incident_archive_integrity_checks")
    op.drop_index("ix_archive_integrity_checks_status", table_name="incident_archive_integrity_checks")
    op.drop_index("ix_archive_integrity_checks_archive_id", table_name="incident_archive_integrity_checks")
    op.drop_table("incident_archive_integrity_checks")
