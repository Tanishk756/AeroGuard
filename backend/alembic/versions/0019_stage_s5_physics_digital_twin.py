"""Create simulation_snapshots table for Stage S5 Physics Digital Twin Traceability.

Revision ID: 0019_stage_s5_physics_digital_twin
Revises: 0018_hardware_registry_and_vehicles
Create Date: 2026-08-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0019_stage_s5_physics_digital_twin"
down_revision: Union[str, None] = "0018_hardware_registry_and_vehicles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "simulation_snapshots",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("run_id", sa.String(length=64), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("compiled_model_hash", sa.String(length=64), nullable=False),
        sa.Column("artifact_hash", sa.String(length=64), nullable=False),
        sa.Column("provenance_json", sa.JSON(), nullable=False),
        sa.Column("compiled_metadata_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_simulation_snapshots_run_id", "simulation_snapshots", ["run_id"])


def downgrade() -> None:
    op.drop_table("simulation_snapshots")
