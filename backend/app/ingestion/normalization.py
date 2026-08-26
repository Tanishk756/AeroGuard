"""Normalize validated raw detections into F1 persistence values."""

from datetime import UTC, datetime, timedelta

from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass
from app.schemas._operational import validate_metadata
from app.schemas.ingestion import RawDetection


class DetectionNormalizer:
    def __init__(self, future_tolerance: timedelta = timedelta(minutes=5)):
        self.future_tolerance = future_tolerance

    def normalize(self, raw: RawDetection, sensor: Sensor) -> Detection:
        if raw.sensor_id != sensor.id:
            raise ValueError("Detection sensor does not match the requested sensor")
        if raw.source_class != sensor.source_class:
            raise ValueError("Detection source class does not match the sensor")
        if raw.source_type != sensor.source_type:
            raise ValueError("Detection source type does not match the sensor")
        now = datetime.now(UTC)
        if raw.timestamp > now + self.future_tolerance and raw.source_class != SensorSourceClass.REPLAY:
            raise ValueError("Detection timestamp is too far in the future")
        heading = 0.0 if raw.heading == 360 else raw.heading
        return Detection(
            sensor_id=sensor.id,
            source_detection_id=raw.source_detection_id,
            timestamp=raw.timestamp.astimezone(UTC).replace(tzinfo=None),
            latitude=raw.latitude,
            longitude=raw.longitude,
            altitude=raw.altitude,
            velocity=raw.velocity,
            heading=heading,
            horizontal_uncertainty=raw.horizontal_uncertainty,
            vertical_uncertainty=raw.vertical_uncertainty,
            confidence=raw.confidence,
            classification=raw.classification,
            quality=raw.quality,
            source_class=raw.source_class,
            source_type=raw.source_type,
            metadata_json=validate_metadata(raw.metadata),
        )
