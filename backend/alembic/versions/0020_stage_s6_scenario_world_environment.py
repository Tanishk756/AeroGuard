"""Create simulation_worlds, world_objects, and scenario_entities tables for Stage S6 Scenario World Environment Platform.

Revision ID: 0020_stage_s6_scenario_world_environment
Revises: 0019_stage_s5_physics_digital_twin
Create Date: 2026-08-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0020_stage_s6_scenario_world_environment"
down_revision: Union[str, None] = "0019_stage_s5_physics_digital_twin"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulation_worlds",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("world_type", sa.String(length=32), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_worlds_project_id", "simulation_worlds", ["project_id"])

    op.create_table(
        "world_objects",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("world_id", sa.String(length=36), nullable=False),
        sa.Column("object_type", sa.String(length=64), nullable=False),
        sa.Column("position_json", sa.JSON(), nullable=False),
        sa.Column("orientation_json", sa.JSON(), nullable=False),
        sa.Column("scale_json", sa.JSON(), nullable=False),
        sa.Column("collision_enabled", sa.Boolean(), nullable=False),
        sa.Column("visual_enabled", sa.Boolean(), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["world_id"], ["simulation_worlds.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_world_objects_world_id", "world_objects", ["world_id"])

    op.create_table(
        "scenario_entities",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.String(length=256), nullable=True),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("simulator", sa.String(length=32), nullable=False),
        sa.Column("autopilot", sa.String(length=32), nullable=False),
        sa.Column("world_id", sa.String(length=36), nullable=False),
        sa.Column("environment_config_json", sa.JSON(), nullable=False),
        sa.Column("physics_config_json", sa.JSON(), nullable=False),
        sa.Column("weather_config_json", sa.JSON(), nullable=False),
        sa.Column("spawn_config_json", sa.JSON(), nullable=False),
        sa.Column("random_seed", sa.Integer(), nullable=False),
        sa.Column("configuration_version", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.ForeignKeyConstraint(["world_id"], ["simulation_worlds.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_scenario_entities_project_id", "scenario_entities", ["project_id"])


def downgrade() -> None:
    op.drop_table("scenario_entities")
    op.drop_table("world_objects")
    op.drop_table("simulation_worlds")
