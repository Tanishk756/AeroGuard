"""Deterministic local JSONL replay adapter."""

import json
from collections.abc import Iterable, Iterator
from pathlib import Path

from app.models.sensor import SensorSourceClass
from app.schemas.ingestion import RawDetection


class ReplaySensorAdapter:
    def __init__(self, sensor_id: str, source_type: str, path: str | Path):
        self._sensor_id = sensor_id
        self._source_type = source_type
        self._path = Path(path)

    @property
    def sensor_id(self) -> str:
        return self._sensor_id

    @property
    def source_type(self) -> str:
        return self._source_type

    @property
    def source_class(self) -> SensorSourceClass:
        return SensorSourceClass.REPLAY

    def read(self) -> Iterable[RawDetection]:
        return self._read_lines()

    def _read_lines(self) -> Iterator[RawDetection]:
        with self._path.open(encoding="utf-8") as source:
            for line_number, line in enumerate(source, start=1):
                if not line.strip():
                    continue
                try:
                    values = json.loads(line)
                    values["sensor_id"] = self._sensor_id
                    values["source_class"] = self.source_class
                    values["source_type"] = self._source_type
                    yield RawDetection.model_validate(values)
                except (json.JSONDecodeError, TypeError, ValueError) as exc:
                    raise ValueError(f"Invalid replay detection at line {line_number}") from exc
