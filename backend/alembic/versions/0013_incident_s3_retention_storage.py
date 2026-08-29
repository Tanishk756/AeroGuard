"""Add S3 retention storage provider metadata columns to incident_archives.

Revision ID: 0013_incident_s3_retention_storage
Revises: 0012_incident_retention_archival
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_incident_s3_retention_storage"
down_revision: Union[str, None] = "0012_incident_retention_archival"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    with op.batch_alter_table("incident_archives") as batch_op:
        batch_op.add_column(sa.Column("storage_provider", sa.String(32), nullable=False, server_default="LOCAL"))
        batch_op.add_column(sa.Column("storage_location", sa.String(512), nullable=True))
        batch_op.add_column(sa.Column("presigned_url_expires_at", sa.DateTime(), nullable=True))
        batch_op.create_index("ix_incident_archives_storage_provider", ["storage_provider"])


def downgrade() -> None:
    with op.batch_alter_table("incident_archives") as batch_op:
        batch_op.drop_index("ix_incident_archives_storage_provider")
        batch_op.drop_column("presigned_url_expires_at")
        batch_op.drop_column("storage_location")
        batch_op.drop_column("storage_provider")
