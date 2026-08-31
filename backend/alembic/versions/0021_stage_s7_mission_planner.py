"""Create missions, mission_items, and mission_run_snapshots tables for Stage S7 Mission Platform.

Revision ID: 0021_stage_s7_mission_planner
Revises: 0020_stage_s6_scenario_world_environment
Create Date: 2026-08-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0021_stage_s7_mission_planner"
down_revision: Union[str, None] = "0020_stage_s6_scenario_world_environment"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "missions",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("scenario_id", sa.String(length=36), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenario_entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_missions_project_id", "missions", ["project_id"])

    op.create_table(
        "mission_items",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("command_type", sa.String(length=32), nullable=False),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        sa.Column("altitude_m", sa.Float(), nullable=False),
        sa.Column("acceptance_radius_m", sa.Float(), nullable=False),
        sa.Column("loiter_duration_s", sa.Float(), nullable=False),
        sa.Column("params_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mission_items_mission_id", "mission_items", ["mission_id"])

    op.create_table(
        "mission_run_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("mission_id", sa.String(length=36), nullable=False),
        sa.Column("mission_hash", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_hash", sa.String(length=64), nullable=False),
        sa.Column("scenario_id", sa.String(length=36), nullable=False),
        sa.Column("scenario_hash", sa.String(length=64), nullable=False),
        sa.Column("world_hash", sa.String(length=64), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["mission_id"], ["missions.id"]),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["scenario_id"], ["scenario_entities.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_mission_run_snapshots_run_id", "mission_run_snapshots", ["run_id"], unique=True)


def downgrade() -> None:
    op.drop_table("mission_run_snapshots")
    op.drop_table("mission_items")
    op.drop_table("missions")
