"""Realtime event contracts and serialization envelopes."""

from datetime import UTC, datetime
from enum import StrEnum
from typing import Any
import uuid

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.schemas._operational import validate_utc


class RealtimeChannel(StrEnum):
    OPERATIONAL = "operational"
    SIMULATION = "simulation"
    SYSTEM = "system"


class RealtimeEventType(StrEnum):
    # Operational track events
    TRACK_CREATED = "track.created"
    TRACK_UPDATED = "track.updated"
    TRACK_DROPPED = "track.dropped"

    # Operational alert & threat events
    ALERT_CREATED = "alert.created"
    ALERT_UPDATED = "alert.updated"
    THREAT_UPDATED = "threat.updated"
    GEOFENCE_BREACH = "geofence.breach"

    # Defensive AI & intelligence events
    ANOMALY_UPDATED = "anomaly.updated"
    TRAJECTORY_UPDATED = "trajectory.updated"
    INGRESS_UPDATED = "ingress.updated"
    AI_SUMMARY = "ai.summary"
    AI_GROUP = "ai.group"
    AI_BEHAVIOR = "ai.behavior"
    AI_PRIORITY = "ai.priority"
    AI_MULTI_SUMMARY = "ai.multi_summary"

    # Simulation lifecycle & clock events
    SIMULATION_STATE = "simulation.state"
    SIMULATION_STEP = "simulation.step"
    SIMULATION_CLOCK = "simulation.clock"
    SIMULATION_RESET = "simulation.reset"

    # System & connection events
    HEARTBEAT = "system.heartbeat"


class RealtimeEventEnvelope(BaseModel):
    """Canonical realtime event envelope for WebSocket event streaming."""

    model_config = ConfigDict(extra="forbid")

    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=64)
    channel: str = Field(min_length=1, max_length=32)
    sequence: int = Field(ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resource_type: str | None = Field(default=None, max_length=64)
    resource_id: str | None = Field(default=None, max_length=128)
    correlation_id: str | None = Field(default=None, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)

    @field_validator("timestamp")
    @classmethod
    def timestamp_is_utc(cls, value: datetime) -> datetime:
        return validate_utc(value)
