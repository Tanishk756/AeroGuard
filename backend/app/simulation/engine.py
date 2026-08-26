"""Deterministic simulation engine orchestrator."""

import random
from datetime import datetime

from app.schemas.ingestion import RawDetection
from app.schemas.scenario import ScenarioConfiguration
from app.simulation.clock import SimulationClock
from app.simulation.sensors import SyntheticSensor
from app.simulation.trajectories import TargetKinematicState, TrajectoryEngine


class SimulationEngine:
    def __init__(self, config: ScenarioConfiguration):
        self._config = config
        self._clock = SimulationClock(
            start_time=config.start_time,
            tick_rate_hz=float(config.tick_rate_hz),
        )
        self._prng = random.Random(config.seed)
        self._trajectories = TrajectoryEngine(config.targets)
        self._sensors = [SyntheticSensor(s) for s in sorted(config.sensors, key=lambda s: s.sensor_id)]
        self._generated_detections_count = 0

    @property
    def clock(self) -> SimulationClock:
        return self._clock

    @property
    def trajectories(self) -> TrajectoryEngine:
        return self._trajectories

    @property
    def sensors(self) -> list[SyntheticSensor]:
        return self._sensors

    @property
    def generated_detections_count(self) -> int:
        return self._generated_detections_count

    @property
    def active_targets(self) -> list[TargetKinematicState]:
        return [t for t in self._trajectories.targets.values() if t.is_active]

    def reset(self) -> None:
        """Reset the simulation engine to initial state with fresh PRNG and targets."""
        self._clock.reset()
        self._prng = random.Random(self._config.seed)
        self._trajectories = TrajectoryEngine(self._config.targets)
        self._generated_detections_count = 0

    def step(self, ticks: int = 1) -> list[RawDetection]:
        """Execute N discrete simulation ticks and return all emitted raw observations in deterministic order."""
        if ticks < 1:
            raise ValueError("ticks must be at least 1")

        all_detections: list[RawDetection] = []

        for _ in range(ticks):
            sim_time, tick_index = self._clock.step(1)
            # Advance trajectories by one tick delta
            self._trajectories.advance(self._clock.dt_seconds)

            tick_detections: list[RawDetection] = []
            for sensor in self._sensors:
                for target_id in sorted(self._trajectories.targets.keys()):
                    target = self._trajectories.targets[target_id]
                    detection = sensor.evaluate_target(target, sim_time, tick_index, self._prng)
                    if detection is not None:
                        tick_detections.append(detection)

            # Sort tick detections deterministically by (timestamp, sensor_id, target_id)
            tick_detections.sort(
                key=lambda d: (
                    d.timestamp,
                    d.sensor_id,
                    d.metadata.get("target_id", "") if d.metadata else "",
                )
            )
            all_detections.extend(tick_detections)
            self._generated_detections_count += len(tick_detections)

        return all_detections
