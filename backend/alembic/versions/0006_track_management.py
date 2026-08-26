"""Create Stage F3 track management and association tables.

Revision ID: 0006_track_management
Revises: 0005_operational_core
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006_track_management"
down_revision: Union[str, None] = "0005_operational_core"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

TRACK_ASSOCIATION_DECISION = sa.Enum(
    "ASSOCIATED",
    "NEW_TRACK",
    "NO_CANDIDATE",
    "GATE_REJECTED",
    "STALE_DETECTION",
    "CLOSED_TRACK",
    "DUPLICATE",
    native_enum=False,
    create_constraint=True,
    name="track_association_decision",
)


def upgrade() -> None:
    op.create_table(
        "track_associations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("detection_id", sa.String(36), sa.ForeignKey("detections.id", ondelete="CASCADE"), nullable=False),
        sa.Column("track_id", sa.String(36), sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sensor_id", sa.String(36), sa.ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("distance_meters", sa.Float, nullable=True),
        sa.Column("vertical_distance_meters", sa.Float, nullable=True),
        sa.Column("time_delta_seconds", sa.Float, nullable=True),
        sa.Column("score", sa.Float, nullable=True),
        sa.Column("decision", TRACK_ASSOCIATION_DECISION, nullable=False),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("gate_result", sa.String(64), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("detection_id", name="uq_track_associations_detection_id"),
        sa.CheckConstraint("score is null or (score >= 0 and score <= 1)", name="ck_track_associations_score"),
        sa.CheckConstraint("distance_meters is null or distance_meters >= 0", name="ck_track_associations_distance"),
        sa.CheckConstraint("vertical_distance_meters is null or vertical_distance_meters >= 0", name="ck_track_associations_vertical_distance"),
        sa.CheckConstraint("time_delta_seconds is null or time_delta_seconds >= 0", name="ck_track_associations_time_delta"),
    )
    op.create_index("ix_track_associations_track_timestamp", "track_associations", ["track_id", "timestamp"])
    op.create_index("ix_track_associations_sensor_timestamp", "track_associations", ["sensor_id", "timestamp"])
    op.create_index("ix_track_associations_decision_timestamp", "track_associations", ["decision", "timestamp"])
    op.create_index("ix_track_associations_detection_id", "track_associations", ["detection_id"])


def downgrade() -> None:
    op.drop_table("track_associations")
