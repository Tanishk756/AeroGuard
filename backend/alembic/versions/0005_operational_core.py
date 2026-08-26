"""Create Stage F1 operational data foundation.

Revision ID: 0005_operational_core
Revises: 0004_audit_events
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005_operational_core"
down_revision: Union[str, None] = "0004_audit_events"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


SOURCE_CLASS = sa.Enum("REAL", "SIMULATION", "REPLAY", native_enum=False, create_constraint=True, name="sensor_source_class")
SENSOR_STATUS = sa.Enum("REGISTERED", "ACTIVE", "DEGRADED", "OFFLINE", "DISABLED", native_enum=False, create_constraint=True, name="sensor_status")
TRACK_STATE = sa.Enum("NEW", "ACTIVE", "STALE", "LOST", "ARCHIVED", native_enum=False, create_constraint=True, name="track_state")
ALERT_TYPE = sa.Enum("TRACK_DETECTED", "TRACK_LOST", "UNKNOWN_TRACK", "GEOFENCE_BREACH", "SENSOR_OFFLINE", "SENSOR_DEGRADED", "DATA_QUALITY_LOW", native_enum=False, create_constraint=True, name="alert_type")
ALERT_SEVERITY = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", native_enum=False, create_constraint=True, name="alert_severity")
ALERT_STATUS = sa.Enum("OPEN", "ACKNOWLEDGED", "RESOLVED", native_enum=False, create_constraint=True, name="alert_status")
THREAT_LEVEL = sa.Enum("LOW", "MEDIUM", "HIGH", "CRITICAL", native_enum=False, create_constraint=True, name="threat_level")
SCENARIO_STATUS = sa.Enum("DRAFT", "READY", "RUNNING", "COMPLETED", "FAILED", native_enum=False, create_constraint=True, name="scenario_status")


def upgrade() -> None:
    op.create_table(
        "sensors",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("source_class", SOURCE_CLASS, nullable=False),
        sa.Column("status", SENSOR_STATUS, nullable=False),
        sa.Column("configuration_version", sa.Integer, nullable=False),
        sa.Column("configuration_metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("length(name) between 1 and 200", name="ck_sensors_name_length"),
        sa.CheckConstraint("length(source_type) between 1 and 64", name="ck_sensors_source_type_length"),
    )
    op.create_index("ix_sensors_status", "sensors", ["status"])
    op.create_index("ix_sensors_source_type", "sensors", ["source_type"])
    op.create_index("ix_sensors_updated_at", "sensors", ["updated_at"])

    op.create_table(
        "tracks",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("state", TRACK_STATE, nullable=False),
        sa.Column("first_seen_at", sa.DateTime, nullable=False),
        sa.Column("last_seen_at", sa.DateTime, nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("altitude", sa.Float, nullable=True),
        sa.Column("velocity", sa.Float, nullable=True),
        sa.Column("heading", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("classification", sa.String(64), nullable=True),
        sa.Column("source_count", sa.Integer, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("latitude between -90 and 90", name="ck_tracks_latitude"),
        sa.CheckConstraint("longitude between -180 and 180", name="ck_tracks_longitude"),
        sa.CheckConstraint("heading is null or heading >= 0 and heading < 360", name="ck_tracks_heading"),
        sa.CheckConstraint("confidence between 0 and 1", name="ck_tracks_confidence"),
    )
    op.create_index("ix_tracks_state", "tracks", ["state"])
    op.create_index("ix_tracks_last_seen_at", "tracks", ["last_seen_at"])

    op.create_table(
        "detections",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("sensor_id", sa.String(36), sa.ForeignKey("sensors.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_detection_id", sa.String(128), nullable=True),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("altitude", sa.Float, nullable=True),
        sa.Column("velocity", sa.Float, nullable=True),
        sa.Column("heading", sa.Float, nullable=True),
        sa.Column("horizontal_uncertainty", sa.Float, nullable=True),
        sa.Column("vertical_uncertainty", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("classification", sa.String(64), nullable=True),
        sa.Column("quality", sa.String(32), nullable=True),
        sa.Column("source_class", SOURCE_CLASS, nullable=False),
        sa.Column("source_type", sa.String(64), nullable=False),
        sa.Column("track_id", sa.String(36), sa.ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("sensor_id", "source_detection_id", name="uq_detections_sensor_source_id"),
        sa.CheckConstraint("latitude between -90 and 90", name="ck_detections_latitude"),
        sa.CheckConstraint("longitude between -180 and 180", name="ck_detections_longitude"),
        sa.CheckConstraint("heading is null or heading >= 0 and heading < 360", name="ck_detections_heading"),
        sa.CheckConstraint("velocity is null or velocity >= 0", name="ck_detections_velocity"),
        sa.CheckConstraint("confidence between 0 and 1", name="ck_detections_confidence"),
        sa.CheckConstraint("horizontal_uncertainty is null or horizontal_uncertainty >= 0", name="ck_detections_horizontal_uncertainty"),
        sa.CheckConstraint("vertical_uncertainty is null or vertical_uncertainty >= 0", name="ck_detections_vertical_uncertainty"),
    )
    op.create_index("ix_detections_timestamp", "detections", ["timestamp"])
    op.create_index("ix_detections_sensor_timestamp", "detections", ["sensor_id", "timestamp"])
    op.create_index("ix_detections_track_id", "detections", ["track_id"])

    op.create_table(
        "track_history",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("track_id", sa.String(36), sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("sequence", sa.Integer, nullable=False),
        sa.Column("timestamp", sa.DateTime, nullable=False),
        sa.Column("latitude", sa.Float, nullable=False),
        sa.Column("longitude", sa.Float, nullable=False),
        sa.Column("altitude", sa.Float, nullable=True),
        sa.Column("velocity", sa.Float, nullable=True),
        sa.Column("heading", sa.Float, nullable=True),
        sa.Column("confidence", sa.Float, nullable=False),
        sa.Column("state", TRACK_STATE, nullable=False),
        sa.Column("provenance", SOURCE_CLASS, nullable=False),
        sa.Column("source_detection_ids", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("track_id", "sequence", name="uq_track_history_track_sequence"),
        sa.CheckConstraint("sequence >= 0", name="ck_track_history_sequence"),
        sa.CheckConstraint("latitude between -90 and 90", name="ck_track_history_latitude"),
        sa.CheckConstraint("longitude between -180 and 180", name="ck_track_history_longitude"),
        sa.CheckConstraint("heading is null or heading >= 0 and heading < 360", name="ck_track_history_heading"),
        sa.CheckConstraint("velocity is null or velocity >= 0", name="ck_track_history_velocity"),
        sa.CheckConstraint("confidence between 0 and 1", name="ck_track_history_confidence"),
    )
    op.create_index("ix_track_history_track_timestamp", "track_history", ["track_id", "timestamp"])

    op.create_table(
        "alerts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("type", ALERT_TYPE, nullable=False),
        sa.Column("severity", ALERT_SEVERITY, nullable=False),
        sa.Column("status", ALERT_STATUS, nullable=False),
        sa.Column("track_id", sa.String(36), sa.ForeignKey("tracks.id", ondelete="SET NULL"), nullable=True),
        sa.Column("sensor_id", sa.String(36), sa.ForeignKey("sensors.id", ondelete="SET NULL"), nullable=True),
        sa.Column("reason", sa.String(512), nullable=False),
        sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.Column("acknowledged_at", sa.DateTime, nullable=True),
        sa.Column("resolved_at", sa.DateTime, nullable=True),
    )
    op.create_index("ix_alerts_status_created_at", "alerts", ["status", "created_at"])
    op.create_index("ix_alerts_track_id", "alerts", ["track_id"])
    op.create_index("ix_alerts_sensor_id", "alerts", ["sensor_id"])

    op.create_table(
        "threat_assessments",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("track_id", sa.String(36), sa.ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float, nullable=False),
        sa.Column("level", THREAT_LEVEL, nullable=False),
        sa.Column("factors", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.UniqueConstraint("track_id", name="uq_threat_assessments_track_id"),
        sa.CheckConstraint("score between 0 and 100", name="ck_threat_assessments_score"),
    )

    op.create_table(
        "scenarios",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000), nullable=False),
        sa.Column("status", SCENARIO_STATUS, nullable=False),
        sa.Column("created_by_user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("source_class", SOURCE_CLASS, nullable=False),
        sa.Column("configuration_metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("length(name) between 1 and 200", name="ck_scenarios_name_length"),
        sa.CheckConstraint("length(description) <= 1000", name="ck_scenarios_description_length"),
    )
    op.create_index("ix_scenarios_status", "scenarios", ["status"])
    op.create_index("ix_scenarios_created_by_user_id", "scenarios", ["created_by_user_id"])

    op.create_table(
        "geofences",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean, nullable=False),
        sa.Column("geometry", sa.JSON, nullable=False),
        sa.Column("min_altitude", sa.Float, nullable=True),
        sa.Column("max_altitude", sa.Float, nullable=True),
        sa.Column("metadata", sa.JSON, nullable=False),
        sa.Column("created_at", sa.DateTime, nullable=False),
        sa.Column("updated_at", sa.DateTime, nullable=False),
        sa.CheckConstraint("length(name) between 1 and 200", name="ck_geofences_name_length"),
        sa.CheckConstraint("min_altitude is null or min_altitude >= 0", name="ck_geofences_min_altitude"),
        sa.CheckConstraint("max_altitude is null or max_altitude >= 0", name="ck_geofences_max_altitude"),
        sa.CheckConstraint("min_altitude is null or max_altitude is null or min_altitude <= max_altitude", name="ck_geofences_altitude_range"),
    )
    op.create_index("ix_geofences_enabled", "geofences", ["enabled"])


def downgrade() -> None:
    op.drop_table("geofences")
    op.drop_table("scenarios")
    op.drop_table("threat_assessments")
    op.drop_table("alerts")
    op.drop_table("track_history")
    op.drop_table("detections")
    op.drop_table("tracks")
    op.drop_table("sensors")