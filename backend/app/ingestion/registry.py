"""Lightweight sensor and adapter lookup."""

from collections.abc import Iterable

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.protocols import SensorAdapter
from app.models.sensor import Sensor


class SensorRegistry:
    def __init__(self, db: Session, adapters: Iterable[SensorAdapter] = ()):
        self.db = db
        self._adapters = {adapter.sensor_id: adapter for adapter in adapters}

    def resolve(self, sensor_id: str) -> Sensor:
        sensor = self.db.scalar(select(Sensor).where(Sensor.id == sensor_id))
        if sensor is None:
            raise LookupError("Sensor not found")
        return sensor

    def adapter(self, sensor_id: str) -> SensorAdapter | None:
        return self._adapters.get(sensor_id)
