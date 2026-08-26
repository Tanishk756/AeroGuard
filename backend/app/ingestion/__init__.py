"""Stage F2 sensor abstraction and detection ingestion."""

from app.ingestion.normalization import DetectionNormalizer
from app.ingestion.registry import SensorRegistry
from app.ingestion.service import DetectionIngested, DetectionIngestionService, IngestionResult

__all__ = ["DetectionIngested", "DetectionIngestionService", "DetectionNormalizer", "IngestionResult", "SensorRegistry"]
