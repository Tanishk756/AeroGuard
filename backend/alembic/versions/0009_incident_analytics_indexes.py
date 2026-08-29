"""Add incident analytics indexes for procedural action category query optimization.

Revision ID: 0009_incident_analytics_indexes
Revises: 0008_incident_management
"""

from typing import Sequence, Union

from alembic import op

revision: str = "0009_incident_analytics_indexes"
down_revision: Union[str, None] = "0008_incident_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("ix_incident_events_category", "incident_events", ["category"])


def downgrade() -> None:
    op.drop_index("ix_incident_events_category", table_name="incident_events")
