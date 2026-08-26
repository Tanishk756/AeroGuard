"""Transaction-owning detection ingestion service."""

from dataclasses import dataclass
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.ingestion.normalization import DetectionNormalizer
from app.ingestion.registry import SensorRegistry
from app.models.detection import Detection
from app.models.sensor import SensorStatus
from app.schemas.ingestion import RawDetection


@dataclass(frozen=True)
class DetectionIngested:
    detection_id: str
    sensor_id: str
    source_detection_id: str
    timestamp: datetime


@dataclass(frozen=True)
class IngestionResult:
    detection: Detection
    created: bool
    event: DetectionIngested


class DetectionIngestionService:
    def __init__(self, db: Session, registry: SensorRegistry | None = None, normalizer: DetectionNormalizer | None = None):
        self.db = db
        self.registry = registry or SensorRegistry(db)
        self.normalizer = normalizer or DetectionNormalizer()

    def ingest(self, raw: RawDetection) -> IngestionResult:
        sensor = self.registry.resolve(raw.sensor_id)
        if sensor.status == SensorStatus.DISABLED:
            raise PermissionError("Sensor is disabled")
        detection = self.normalizer.normalize(raw, sensor)
        try:
            with self.db.begin_nested():
                self.db.add(detection)
                self.db.flush()
        except IntegrityError:
            existing = self.db.scalar(select(Detection).where(Detection.sensor_id == sensor.id, Detection.source_detection_id == raw.source_detection_id))
            if existing is None:
                self.db.rollback()
                raise
            detection = existing
            created = False
        else:
            created = True
        try:
            self.db.commit()
        except Exception:
            self.db.rollback()
            raise
        event = DetectionIngested(detection.id, detection.sensor_id, detection.source_detection_id, detection.timestamp)
        return IngestionResult(detection, created, event)
