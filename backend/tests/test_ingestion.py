"""F2 adapter, normalization, and ingestion service tests."""

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import select

from app.ingestion.adapters.replay import ReplaySensorAdapter
from app.ingestion.adapters.simulation import SimulationSensorAdapter
from app.ingestion.normalization import DetectionNormalizer
from app.ingestion.service import DetectionIngestionService
from app.models.detection import Detection
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.schemas.ingestion import RawDetection


def sensor(database, **values):
    item = Sensor(name="Ingestion Sensor", source_type="synthetic", source_class=SensorSourceClass.SIMULATION, **values)
    database.add(item)
    database.commit()
    return item


def raw(sensor_id: str, **values) -> RawDetection:
    defaults = dict(source_detection_id="source-1", timestamp=datetime.now(UTC), sensor_id=sensor_id, latitude=10, longitude=20, confidence=0.8, source_class=SensorSourceClass.SIMULATION, source_type="synthetic")
    defaults.update(values)
    return RawDetection(**defaults)


def test_ingestion_persists_and_duplicate_is_deterministic(database):
    item = sensor(database)
    service = DetectionIngestionService(database)
    first = service.ingest(raw(item.id))
    duplicate = service.ingest(raw(item.id, latitude=11))
    assert first.created is True
    assert duplicate.created is False
    assert duplicate.detection.id == first.detection.id
    assert database.scalar(select(Detection).where(Detection.sensor_id == item.id)).latitude == 10


def test_ingestion_rejects_unknown_disabled_and_mismatched_sources(database):
    item = sensor(database)
    with pytest.raises(LookupError):
        DetectionIngestionService(database).ingest(raw("missing"))
    item.status = SensorStatus.DISABLED
    database.commit()
    with pytest.raises(PermissionError):
        DetectionIngestionService(database).ingest(raw(item.id))
    item.status = SensorStatus.ACTIVE
    database.commit()
    with pytest.raises(ValueError):
        DetectionIngestionService(database).ingest(raw(item.id, source_class=SensorSourceClass.REPLAY))


def test_normalization_converts_heading_and_rejects_future(database):
    item = sensor(database)
    normalizer = DetectionNormalizer()
    assert normalizer.normalize(raw(item.id, heading=360), item).heading == 0
    with pytest.raises(ValueError):
        normalizer.normalize(raw(item.id, timestamp=datetime.now(UTC) + timedelta(minutes=6)), item)


def test_simulation_adapter_is_deterministic():
    first = list(SimulationSensorAdapter("sensor", seed=7, count=3).read())
    second = list(SimulationSensorAdapter("sensor", seed=7, count=3).read())
    assert [item.model_dump(exclude={"timestamp"}) for item in first] == [item.model_dump(exclude={"timestamp"}) for item in second]
    assert [item.source_detection_id for item in first] == ["simulation-7-0", "simulation-7-1", "simulation-7-2"]


def test_replay_adapter_is_local_and_deterministic(tmp_path):
    path = tmp_path / "detections.jsonl"
    path.write_text('{"source_detection_id":"replay-1","timestamp":"2026-01-01T00:00:00Z","latitude":1,"longitude":2,"confidence":0.5}\n', encoding="utf-8")
    detections = list(ReplaySensorAdapter("sensor", "replay", path).read())
    assert len(detections) == 1
    assert detections[0].source_class == SensorSourceClass.REPLAY
    assert detections[0].sensor_id == "sensor"