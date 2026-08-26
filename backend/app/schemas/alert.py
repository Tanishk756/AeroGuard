"""Alert data contracts."""

from datetime import datetime

from pydantic import Field

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