"""Operational threat assessment event contracts."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class ThreatAssessed:
    track_id: str
    score: float
    level: str
    factors: dict
    timestamp: datetime
