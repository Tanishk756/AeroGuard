"""Create append-only audit events.

Revision ID: 0004_audit_events
Revises: 0003_rbac
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_audit_events"
down_revision: Union[str, None] = "0003_rbac"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "audit_events",
        sa.Column("id", sa.String(36), primary_key=True), sa.Column("event_type", sa.String(64), nullable=False),
        sa.Column("event_version", sa.Integer, nullable=False), sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("action", sa.String(128), nullable=False), sa.Column("result", sa.String(16), nullable=False),
        sa.Column("correlation_id", sa.String(64), nullable=False), sa.Column("actor_user_id", sa.String(36), nullable=True),
        sa.Column("actor_session_id", sa.String(36), nullable=True), sa.Column("target_type", sa.String(64), nullable=True),
        sa.Column("target_id", sa.String(128), nullable=True), sa.Column("reason", sa.String(512), nullable=True),
        sa.Column("permission", sa.String(128), nullable=True), sa.Column("source_ip", sa.String(45), nullable=True),
        sa.Column("user_agent", sa.String(512), nullable=True), sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["actor_session_id"], ["sessions.id"], ondelete="SET NULL"),
    )
    op.create_index("ix_audit_events_timestamp_id", "audit_events", ["timestamp", "id"])
    op.create_index("ix_audit_events_event_type", "audit_events", ["event_type"])
    op.create_index("ix_audit_events_result", "audit_events", ["result"])
    op.create_index("ix_audit_events_actor_user_id", "audit_events", ["actor_user_id"])
    op.create_index("ix_audit_events_target", "audit_events", ["target_type", "target_id"])
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("CREATE TRIGGER audit_events_no_update BEFORE UPDATE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END")
        op.execute("CREATE TRIGGER audit_events_no_delete BEFORE DELETE ON audit_events BEGIN SELECT RAISE(ABORT, 'audit events are immutable'); END")


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name == "sqlite":
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_update")
        op.execute("DROP TRIGGER IF EXISTS audit_events_no_delete")
    op.drop_table("audit_events")