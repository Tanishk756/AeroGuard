"""Scenario execution service coordinating simulation engine, ingestion, and tracking."""

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ingestion.service import DetectionIngestionService
from app.models.scenario import Scenario, ScenarioStatus
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.schemas.scenario import (
    ScenarioConfiguration,
    ScenarioExecutionStatusResponse,
)
from app.simulation.engine import SimulationEngine
from app.tracking.service import TrackingService


@dataclass
class ScenarioExecutionSession:
    scenario_id: str
    engine: SimulationEngine
    config: ScenarioConfiguration
    is_paused: bool = False
    is_stopped: bool = False
    processed_detections_count: int = 0
    error: str | None = None


class ScenarioExecutionService:
    # In-memory registry of active execution sessions across requests
    _sessions: dict[str, ScenarioExecutionSession] = {}

    def __init__(self, db: Session):
        self.db = db
        self.ingestion_service = DetectionIngestionService(db)
        self.tracking_service = TrackingService(db)

    def _ensure_sensors_registered(self, config: ScenarioConfiguration) -> None:
        """Ensure all synthetic sensors in configuration exist in the database sensors table."""
        now = datetime.now(UTC).replace(tzinfo=None)
        for s_def in config.sensors:
            sensor = self.db.get(Sensor, s_def.sensor_id)
            if sensor is None:
                sensor = Sensor(
                    id=s_def.sensor_id,
                    name=f"Synthetic {s_def.modality.upper()} {s_def.sensor_id}",
                    source_type=s_def.modality,
                    source_class=SensorSourceClass.SIMULATION,
                    status=SensorStatus.ACTIVE,
                    configuration_version=1,
                    configuration_metadata={
                        "range_meters": s_def.range_meters,
                        "detection_probability": s_def.detection_probability,
                        "latitude": s_def.latitude,
                        "longitude": s_def.longitude,
                        "altitude": s_def.altitude,
                    },
                    created_at=now,
                    updated_at=now,
                )
                self.db.add(sensor)
            elif sensor.status == SensorStatus.DISABLED:
                sensor.status = SensorStatus.ACTIVE
                sensor.updated_at = now
        self.db.commit()

    def get_or_create_session(self, scenario: Scenario) -> ScenarioExecutionSession:
        if scenario.id in self._sessions:
            return self._sessions[scenario.id]

        config = ScenarioConfiguration.model_validate(scenario.configuration_metadata)
        self._ensure_sensors_registered(config)
        engine = SimulationEngine(config)
        session = ScenarioExecutionSession(
            scenario_id=scenario.id,
            engine=engine,
            config=config,
            is_paused=False,
            is_stopped=False,
            processed_detections_count=0,
            error=None,
        )
        self._sessions[scenario.id] = session
        return session

    def prepare_scenario(self, scenario_id: str) -> Scenario:
        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        if scenario.status not in (ScenarioStatus.DRAFT, ScenarioStatus.READY):
            raise ValueError(f"Cannot prepare scenario in status {scenario.status}")

        config = ScenarioConfiguration.model_validate(scenario.configuration_metadata)
        self._ensure_sensors_registered(config)
        session = self.get_or_create_session(scenario)
        session.engine.reset()
        session.is_paused = False
        session.is_stopped = False
        session.processed_detections_count = 0
        session.error = None

        scenario.status = ScenarioStatus.READY
        scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.commit()
        return scenario

    def start_scenario(self, scenario_id: str) -> ScenarioExecutionStatusResponse:
        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        if scenario.status == ScenarioStatus.DRAFT:
            raise ValueError("Scenario is in DRAFT status; prepare/validate it before starting")

        if scenario.status == ScenarioStatus.COMPLETED:
            raise ValueError("Scenario has already completed; reset before restarting")

        session = self.get_or_create_session(scenario)
        if session.is_stopped:
            raise ValueError("Scenario is stopped; reset before restarting")

        scenario.status = ScenarioStatus.RUNNING
        scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.commit()

        session.is_paused = False
        session.is_stopped = False
        return self.get_status(scenario_id)

    def pause_scenario(self, scenario_id: str) -> ScenarioExecutionStatusResponse:
        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        if scenario.status != ScenarioStatus.RUNNING:
            raise ValueError(f"Cannot pause scenario in status {scenario.status}")

        session = self.get_or_create_session(scenario)
        session.is_paused = True
        session.engine.clock.pause()
        return self.get_status(scenario_id)

    def resume_scenario(self, scenario_id: str) -> ScenarioExecutionStatusResponse:
        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        session = self.get_or_create_session(scenario)
        if session.is_stopped:
            raise ValueError("Cannot resume a stopped scenario; reset before running")

        session.is_paused = False
        session.engine.clock.resume()
        scenario.status = ScenarioStatus.RUNNING
        scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.commit()
        return self.get_status(scenario_id)

    def stop_scenario(self, scenario_id: str) -> ScenarioExecutionStatusResponse:
        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        session = self.get_or_create_session(scenario)
        session.is_stopped = True
        session.is_paused = False
        session.engine.clock.stop()

        scenario.status = ScenarioStatus.READY
        scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.commit()
        return self.get_status(scenario_id)

    def reset_scenario(self, scenario_id: str) -> ScenarioExecutionStatusResponse:
        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        session = self.get_or_create_session(scenario)
        session.engine.reset()
        session.is_paused = False
        session.is_stopped = False
        session.processed_detections_count = 0
        session.error = None

        scenario.status = ScenarioStatus.READY
        scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
        self.db.commit()
        return self.get_status(scenario_id)

    def step(self, scenario_id: str, ticks: int = 1) -> ScenarioExecutionStatusResponse:
        """Execute N discrete simulation ticks, feeding generated observations into F2 ingestion and F3/F4 pipeline."""
        if ticks < 1:
            raise ValueError("ticks must be at least 1")

        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        if scenario.status == ScenarioStatus.DRAFT:
            raise ValueError("Cannot step scenario in DRAFT status; prepare/validate it first")

        if scenario.status == ScenarioStatus.COMPLETED:
            raise ValueError("Cannot step a completed scenario")

        session = self.get_or_create_session(scenario)
        if session.is_stopped:
            raise ValueError("Cannot step a stopped scenario; reset before running")

        try:
            if scenario.status == ScenarioStatus.READY:
                scenario.status = ScenarioStatus.RUNNING
                self.db.commit()

            # Execute N ticks on the simulation engine
            raw_detections = session.engine.step(ticks=ticks)

            # Ingest each raw detection and process through tracking/fusion/threats/alerts
            for raw in raw_detections:
                ingest_res = self.ingestion_service.ingest(raw)
                self.tracking_service.process_detection(ingest_res.detection)
                session.processed_detections_count += 1

            # Check if duration limit reached
            elapsed_seconds = session.engine.clock.tick_count * session.engine.clock.dt_seconds
            if elapsed_seconds >= session.config.duration_seconds:
                scenario.status = ScenarioStatus.COMPLETED
                scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
                self.db.commit()

        except Exception as exc:
            scenario.status = ScenarioStatus.FAILED
            session.error = str(exc)
            scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
            self.db.commit()
            raise

        return self.get_status(scenario_id)

    def get_status(self, scenario_id: str) -> ScenarioExecutionStatusResponse:
        scenario = self.db.get(Scenario, scenario_id)
        if scenario is None:
            raise LookupError(f"Scenario {scenario_id} not found")

        session = self.get_or_create_session(scenario)
        return ScenarioExecutionStatusResponse(
            scenario_id=scenario.id,
            status=scenario.status,
            is_paused=session.is_paused,
            virtual_time=session.engine.clock.current_time,
            tick_count=session.engine.clock.tick_count,
            active_targets=len(session.engine.active_targets),
            generated_detections_count=session.engine.generated_detections_count,
            processed_detections_count=session.processed_detections_count,
            seed=session.config.seed,
            error=session.error,
        )
