"""Add scheduler_locks table for Stage PR1-B distributed background scheduler.

Revision ID: 0015
Revises: 0014
Create Date: 2026-08-30
"""

from alembic import op
import sqlalchemy as sa

revision = "0015"
down_revision = "0014"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "scheduler_locks",
        sa.Column("job_name", sa.String(length=64), primary_key=True, nullable=False),
        sa.Column("locked_by", sa.String(length=128), nullable=True),
        sa.Column("locked_at", sa.DateTime(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("last_run_at", sa.DateTime(), nullable=True),
        sa.Column("last_status", sa.String(length=32), nullable=True),
        sa.Column("last_duration_ms", sa.Float(), nullable=True),
        sa.Column("records_processed", sa.Integer(), nullable=True, server_default="0"),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=True, server_default="0"),
    )


def downgrade() -> None:
    op.drop_table("scheduler_locks")
