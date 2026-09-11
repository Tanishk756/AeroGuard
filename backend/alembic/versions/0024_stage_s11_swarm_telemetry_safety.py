"""Create swarm_safety_policies and swarm_safety_events tables for Stage S11 Swarm Telemetry & Safety-Action Engine.

Revision ID: 0024_stage_s11_swarm_telemetry_safety
Revises: 0023_stage_s10_swarm_formation
Create Date: 2026-09-11
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0024_stage_s11_swarm_telemetry_safety"
down_revision: Union[str, None] = "0023_stage_s10_swarm_formation"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "swarm_safety_policies",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("swarm_id", sa.String(length=36), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("min_separation_m", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("warning_separation_m", sa.Float(), nullable=False, server_default="8.0"),
        sa.Column("critical_separation_m", sa.Float(), nullable=False, server_default="3.0"),
        sa.Column("telemetry_timeout_s", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("link_quality_threshold_percent", sa.Float(), nullable=False, server_default="50.0"),
        sa.Column("formation_deviation_threshold_m", sa.Float(), nullable=False, server_default="4.0"),
        sa.Column("leader_timeout_s", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("cooldown_s", sa.Float(), nullable=False, server_default="10.0"),
        sa.Column("action_escalation", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),

        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["swarm_id"], ["swarms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swarm_safety_policies_swarm_id", "swarm_safety_policies", ["swarm_id"])

    op.create_table(
        "swarm_safety_events",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("swarm_id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("target_vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("event_type", sa.String(length=64), nullable=False),
        sa.Column("severity", sa.String(length=32), nullable=False, server_default="WARNING"),
        sa.Column("measured_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("executed_action", sa.String(length=64), nullable=True),
        sa.Column("policy_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["swarm_id"], ["swarms.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swarm_safety_events_swarm_id", "swarm_safety_events", ["swarm_id"])
    op.create_index("ix_swarm_safety_events_event_type", "swarm_safety_events", ["event_type"])
    op.create_index("ix_swarm_safety_events_timestamp", "swarm_safety_events", ["timestamp"])


def downgrade() -> None:
    op.drop_table("swarm_safety_events")
    op.drop_table("swarm_safety_policies")
