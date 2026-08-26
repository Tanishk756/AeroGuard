"""Threat assessment data contracts."""

from datetime import datetime

from pydantic import Field, FiniteFloat

from app.models.threat import ThreatLevel
from app.schemas._operational import OperationalSchema


class ThreatAssessmentSchema(OperationalSchema):
    id: str | None = None
    track_id: str
    score: FiniteFloat = Field(ge=0, le=100)
    level: ThreatLevel
    factors: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None