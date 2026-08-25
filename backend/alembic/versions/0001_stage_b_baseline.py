"""Stage B baseline migration.

Revision ID: 0001_stage_b_baseline
Revises:
Create Date: 2026-08-25
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0001_stage_b_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
