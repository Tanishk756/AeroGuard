"""Hardware-independent sensor adapter contracts."""

from collections.abc import Iterable
from typing import Protocol

from app.models.sensor import SensorSourceClass
from app.schemas.ingestion import RawDetection


class SensorAdapter(Protocol):
    @property
    def sensor_id(self) -> str:
        ...

    @property
    def source_type(self) -> str:
        ...

    @property
    def source_class(self) -> SensorSourceClass:
        ...

    def read(self) -> Iterable[RawDetection]:
        ...
