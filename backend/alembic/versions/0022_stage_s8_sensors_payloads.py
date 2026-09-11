"""Create sensor_instances and payload_instances tables for Stage S8 Sensor Payload Platform.

Revision ID: 0022_stage_s8_sensors_payloads
Revises: 0021_stage_s7_mission_planner
Create Date: 2026-08-31
"""

from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "0022_stage_s8_sensors_payloads"
down_revision: Union[str, None] = "0021_stage_s7_mission_planner"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "sensor_instances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("sensor_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("mass_g", sa.Float(), nullable=False),
        sa.Column("power_w", sa.Float(), nullable=False),
        sa.Column("position_json", sa.JSON(), nullable=False),
        sa.Column("orientation_json", sa.JSON(), nullable=False),
        sa.Column("update_rate_hz", sa.Float(), nullable=False),
        sa.Column("health_status", sa.String(length=32), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sensor_instances_vehicle_id", "sensor_instances", ["vehicle_id"])

    op.create_table(
        "payload_instances",
        sa.Column("id", sa.String(length=36), nullable=False),
        sa.Column("vehicle_id", sa.String(length=36), nullable=False),
        sa.Column("payload_type", sa.String(length=32), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("mass_g", sa.Float(), nullable=False),
        sa.Column("power_w", sa.Float(), nullable=False),
        sa.Column("position_json", sa.JSON(), nullable=False),
        sa.Column("orientation_json", sa.JSON(), nullable=False),
        sa.Column("config_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["vehicle_id"], ["vehicles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_payload_instances_vehicle_id", "payload_instances", ["vehicle_id"])


def downgrade() -> None:
    op.drop_table("payload_instances")
    op.drop_table("sensor_instances")
