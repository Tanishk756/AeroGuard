"""Create Stage HI1 intelligence history and replay tables.

Revision ID: 0007_intelligence_history
Revises: 0006_track_management
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0007_intelligence_history"
down_revision: Union[str, None] = "0006_track_management"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. intelligence_snapshots table
    op.create_table(
        "intelligence_snapshots",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("active_track_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("group_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("formation_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("peak_threat_score", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("summary_json", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("active_track_count >= 0", name="ck_intelligence_snapshots_active_tracks"),
        sa.CheckConstraint("group_count >= 0", name="ck_intelligence_snapshots_groups"),
        sa.CheckConstraint("formation_count >= 0", name="ck_intelligence_snapshots_formations"),
        sa.CheckConstraint("peak_threat_score >= 0 and peak_threat_score <= 100", name="ck_intelligence_snapshots_peak_score"),
    )
    op.create_index("ix_intelligence_snapshots_timestamp", "intelligence_snapshots", ["timestamp"])

    # 2. track_group_history table
    op.create_table(
        "track_group_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("group_id", sa.String(64), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("member_track_ids", sa.JSON, nullable=False),
        sa.Column("member_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("centroid_lat", sa.Float, nullable=False),
        sa.Column("centroid_lon", sa.Float, nullable=False),
        sa.Column("radius_meters", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("behavioral_state", sa.String(32), nullable=False),
        sa.Column("coordination_index", sa.Float, nullable=True),
        sa.Column("formation_type", sa.String(32), nullable=True),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("member_count >= 0", name="ck_track_group_history_member_count"),
        sa.CheckConstraint("centroid_lat between -90 and 90", name="ck_track_group_history_centroid_lat"),
        sa.CheckConstraint("centroid_lon between -180 and 180", name="ck_track_group_history_centroid_lon"),
        sa.CheckConstraint("radius_meters >= 0", name="ck_track_group_history_radius"),
    )
    op.create_index("ix_track_group_history_timestamp_group", "track_group_history", ["timestamp", "group_id"])
    op.create_index("ix_track_group_history_group_id", "track_group_history", ["group_id"])
    op.create_index("ix_track_group_history_timestamp", "track_group_history", ["timestamp"])

    # 3. behavior_event_history table
    op.create_table(
        "behavior_event_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("track_id", sa.String(36), nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("previous_state", sa.String(32), nullable=True),
        sa.Column("new_state", sa.String(32), nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False, server_default="0.0"),
        sa.Column("confidence", sa.Float, nullable=False, server_default="1.0"),
        sa.Column("reasons", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("duration_seconds >= 0", name="ck_behavior_event_history_duration"),
        sa.CheckConstraint("confidence between 0 and 1", name="ck_behavior_event_history_confidence"),
    )
    op.create_index("ix_behavior_event_history_timestamp_track", "behavior_event_history", ["timestamp", "track_id"])
    op.create_index("ix_behavior_event_history_track_id", "behavior_event_history", ["track_id"])
    op.create_index("ix_behavior_event_history_timestamp", "behavior_event_history", ["timestamp"])


def downgrade() -> None:
    op.drop_index("ix_behavior_event_history_timestamp", table_name="behavior_event_history")
    op.drop_index("ix_behavior_event_history_track_id", table_name="behavior_event_history")
    op.drop_index("ix_behavior_event_history_timestamp_track", table_name="behavior_event_history")
    op.drop_table("behavior_event_history")

    op.drop_index("ix_track_group_history_timestamp", table_name="track_group_history")
    op.drop_index("ix_track_group_history_group_id", table_name="track_group_history")
    op.drop_index("ix_track_group_history_timestamp_group", table_name="track_group_history")
    op.drop_table("track_group_history")

    op.drop_index("ix_intelligence_snapshots_timestamp", table_name="intelligence_snapshots")
    op.drop_table("intelligence_snapshots")
