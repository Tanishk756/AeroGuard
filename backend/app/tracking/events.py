"""Operational tracking event contracts."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class DetectionAssociated:
    detection_id: str
    track_id: str
    timestamp: datetime
    score: float | None
    decision: str
