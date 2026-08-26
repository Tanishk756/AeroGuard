"""Alert data contracts and API response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.alert import AlertSeverity, AlertStatus, AlertType
from app.schemas._operational import OperationalSchema


class AlertSchema(OperationalSchema):
    id: str | None = None
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus = AlertStatus.OPEN
    track_id: str | None = None
    sensor_id: str | None = None
    reason: str = Field(min_length=1, max_length=512)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class AlertResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    type: AlertType
    severity: AlertSeverity
    status: AlertStatus
    track_id: str | None = None
    sensor_id: str | None = None
    reason: str
    metadata: dict = Field(alias="metadata_json")
    created_at: datetime
    updated_at: datetime
    acknowledged_at: datetime | None = None
    resolved_at: datetime | None = None


class AlertPage(BaseModel):
    items: list[AlertResponse]
    next_cursor: str | None = None