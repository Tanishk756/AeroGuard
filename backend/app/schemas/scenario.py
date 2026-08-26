"""Scenario data contracts."""

from datetime import datetime

from pydantic import Field

from app.models.scenario import ScenarioStatus
from app.models.sensor import SensorSourceClass
from app.schemas._operational import OperationalSchema


class ScenarioSchema(OperationalSchema):
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    description: str = Field(max_length=1000)
    status: ScenarioStatus = ScenarioStatus.DRAFT
    created_by_user_id: str
    source_class: SensorSourceClass = SensorSourceClass.SIMULATION
    configuration_metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None