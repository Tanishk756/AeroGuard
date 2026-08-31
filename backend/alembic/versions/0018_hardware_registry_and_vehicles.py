"""Create hardware_components and vehicles tables for Stage S4 Hardware Builder.

Revision ID: 0018_hardware_registry_and_vehicles
Revises: 0017_simulation_platform_tables
Create Date: 2026-08-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0018_hardware_registry_and_vehicles"
down_revision: Union[str, None] = "0017_simulation_platform_tables"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Create hardware_components table
    op.create_table(
        "hardware_components",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("manufacturer", sa.String(length=100), nullable=False),
        sa.Column("model", sa.String(length=100), nullable=False),
        sa.Column("category", sa.String(length=50), nullable=False),
        sa.Column("part_number", sa.String(length=100), nullable=True),
        sa.Column("datasheet_url", sa.String(length=500), nullable=True),
        sa.Column("mass_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("dimensions_mm", sa.JSON(), nullable=True),
        sa.Column("electrical_specs", sa.JSON(), nullable=True),
        sa.Column("interfaces", sa.JSON(), nullable=True),
        sa.Column("supported_simulation_models", sa.JSON(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_hardware_components_manufacturer", "hardware_components", ["manufacturer"])
    op.create_index("ix_hardware_components_model", "hardware_components", ["model"])
    op.create_index("ix_hardware_components_category", "hardware_components", ["category"])

    # 2. Create vehicles table
    op.create_table(
        "vehicles",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("project_id", sa.String(length=100), nullable=False),
        sa.Column("name", sa.String(length=150), nullable=False),
        sa.Column("vehicle_type", sa.String(length=50), nullable=False, server_default="quadcopter"),
        sa.Column("frame_id", sa.String(length=36), nullable=False),
        sa.Column("motor_id", sa.String(length=36), nullable=False),
        sa.Column("esc_id", sa.String(length=36), nullable=False),
        sa.Column("propeller_id", sa.String(length=36), nullable=False),
        sa.Column("battery_id", sa.String(length=36), nullable=False),
        sa.Column("flight_controller_id", sa.String(length=36), nullable=False),
        sa.Column("gps_id", sa.String(length=36), nullable=True),
        sa.Column("total_mass_g", sa.Float(), nullable=False, server_default="0.0"),
        sa.Column("estimated_hover_throttle", sa.Float(), nullable=False, server_default="0.5"),
        sa.Column("thrust_to_weight_ratio", sa.Float(), nullable=False, server_default="2.0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["frame_id"], ["hardware_components.id"]),
        sa.ForeignKeyConstraint(["motor_id"], ["hardware_components.id"]),
        sa.ForeignKeyConstraint(["esc_id"], ["hardware_components.id"]),
        sa.ForeignKeyConstraint(["propeller_id"], ["hardware_components.id"]),
        sa.ForeignKeyConstraint(["battery_id"], ["hardware_components.id"]),
        sa.ForeignKeyConstraint(["flight_controller_id"], ["hardware_components.id"]),
        sa.ForeignKeyConstraint(["gps_id"], ["hardware_components.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_vehicles_project_id", "vehicles", ["project_id"])


def downgrade() -> None:
    op.drop_table("vehicles")
    op.drop_table("hardware_components")
