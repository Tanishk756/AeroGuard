"""Add failed_login_attempts and locked_until columns for Stage PR1-C login security.

Revision ID: 0016_login_lockout_security
Revises: 0015_scheduler_locks
Create Date: 2026-08-30
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "0016_login_lockout_security"
down_revision: Union[str, None] = "0015_scheduler_locks"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column("failed_login_attempts", sa.Integer(), nullable=False, server_default="0"),
    )
    op.add_column(
        "users",
        sa.Column("locked_until", sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("users", "locked_until")
    op.drop_column("users", "failed_login_attempts")
