"""Deterministic synthetic adapter for ingestion tests."""

from collections.abc import Iterable
from datetime import UTC, datetime, timedelta
import random

from app.models.sensor import SensorSourceClass
from app.schemas.ingestion import RawDetection


class SimulationSensorAdapter:
    def __init__(self, sensor_id: str, source_type: str = "synthetic", seed: int = 0, count: int = 1, latitude: float = 0.0, longitude: float = 0.0, rate_hz: float = 1.0):
        if count < 0 or rate_hz <= 0:
            raise ValueError("count must be nonnegative and rate_hz must be positive")
        self._sensor_id = sensor_id
        self._source_type = source_type
        self._seed = seed
        self._count = count
        self._latitude = latitude
        self._longitude = longitude
        self._rate_hz = rate_hz

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_class(self) -> SensorSourceClass:
        return SensorSourceClass.SIMULATION

    def read(self) -> Iterable[RawDetection]:
        random_source = random.Random(self._seed)
        start = datetime(2020, 1, 1, tzinfo=UTC)
        for index in range(self._count):
            yield RawDetection(
                source_detection_id=f"simulation-{self._seed}-{index}",
                timestamp=start + timedelta(seconds=index / self._rate_hz),
                sensor_id=self._sensor_id,
                latitude=self._latitude + random_source.uniform(-0.001, 0.001),
                longitude=self._longitude + random_source.uniform(-0.001, 0.001),
                altitude=100.0,
                velocity=10.0,
                heading=random_source.uniform(0, 360),
                confidence=0.8,
                source_class=self.source_class,
                source_type=self._source_type,
                metadata={"generator": "simulation", "seed": self._seed},
            )
