"""Sensor data contracts."""

from datetime import datetime

from pydantic import Field

from app.models.sensor import SensorSourceClass, SensorStatus
from app.schemas._operational import OperationalSchema


class SensorSchema(OperationalSchema):
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    source_type: str = Field(min_length=1, max_length=64)
    source_class: SensorSourceClass
    status: SensorStatus = SensorStatus.REGISTERED
    configuration_version: int = Field(default=1, ge=1)
    configuration_metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

