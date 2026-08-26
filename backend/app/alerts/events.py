"""Operational alert event contracts."""

from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class AlertRaised:
    alert_id: str
    type: str
    severity: str
    track_id: str | None
    sensor_id: str | None
    reason: str
    timestamp: datetime
