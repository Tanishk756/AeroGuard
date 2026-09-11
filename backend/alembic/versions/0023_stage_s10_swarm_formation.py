"""Create swarms and swarm_members tables for Stage S10 Swarm Formation Control Engine.

Revision ID: 0023_stage_s10_swarm_formation
Revises: 0022_stage_s8_sensors_payloads
Create Date: 2026-09-11
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0023_stage_s10_swarm_formation"
down_revision: Union[str, None] = "0022_stage_s8_sensors_payloads"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "swarms",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("leader_vehicle_id", sa.String(length=36), nullable=True),
        sa.Column("formation_type", sa.String(length=32), nullable=False, server_default="LINE"),
        sa.Column("formation_spacing_m", sa.Float(), nullable=False, server_default="10.0"),
        sa.Column("min_separation_m", sa.Float(), nullable=False, server_default="5.0"),
        sa.Column("status", sa.String(length=32), nullable=False, server_default="IDLE"),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["leader_vehicle_id"], ["vehicles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swarms_leader_vehicle_id", "swarms", ["leader_vehicle_id"])

    op.create_table(
        "swarm_members",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("swarm_id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False, server_default="FOLLOWER"),
        sa.Column("slot_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("offset_x", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("offset_y", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("offset_z", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["swarm_id"], ["swarms.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_swarm_members_swarm_id", "swarm_members", ["swarm_id"])
    op.create_index("ix_swarm_members_vehicle_id", "swarm_members", ["vehicle_id"])


def downgrade() -> None:
    op.drop_table("swarm_members")
    op.drop_table("swarms")
