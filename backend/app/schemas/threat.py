"""Threat assessment data contracts and API response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat

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


class ThreatAssessmentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    track_id: str
    score: float
    level: ThreatLevel
    factors: dict
    created_at: datetime
    updated_at: datetime


class ThreatAssessmentPage(BaseModel):
    items: list[ThreatAssessmentResponse]
    next_cursor: str | None = None