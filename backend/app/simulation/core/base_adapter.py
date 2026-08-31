"""Abstract Base Simulator Adapter and Engine Registry.

Defines simulator-neutral lifecycle contracts and in-memory mock engine for unit testing.
"""

from abc import ABC, abstractmethod
import math
import random
import time
from datetime import datetime, timezone
from typing import Dict, Optional, Type

from app.schemas.simulation_platform import (
    SimulationRunStatus,
    SimulationScenarioSpec,
    VehicleState,
    PositionVector,
    VelocityVector,
    AttitudeVector,
    BatteryState,
    GPSState,
)


class BaseSimulationAdapter(ABC):
    """Abstract Base Class for all simulation engine adapters."""

    def __init__(self, scenario: SimulationScenarioSpec):
        self.scenario = scenario
        self.status = SimulationRunStatus.CREATED
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.telemetry_count: int = 0

    @abstractmethod
    async def validate_configuration(self) -> bool:
        """Validate scenario configuration specs prior to launch."""
        pass

    @abstractmethod
    async def prepare(self) -> bool:
        """Prepare engine resources (world files, environment paths, ports)."""
        pass

    @abstractmethod
    async def start(self) -> bool:
        """Launch simulator and autopilot runtime processes."""
        pass

    @abstractmethod
    async def pause(self) -> bool:
        """Pause simulation physics loop."""
        pass

    @abstractmethod
    async def resume(self) -> bool:
        """Resume simulation physics loop."""
        pass

    @abstractmethod
    async def reset(self) -> bool:
        """Reset simulation engine state to initial scenario parameters."""
        pass

    @abstractmethod
    async def stop(self) -> bool:
        """Stop simulation and terminate child processes cleanly."""
        pass

    @abstractmethod
    async def get_telemetry(self) -> VehicleState:
        """Fetch latest normalized VehicleState sample."""
        pass

    @abstractmethod
    async def shutdown(self) -> None:
        """Emergency process cleanup and resource releasing."""
        pass


class MockSimulationEngine(BaseSimulationAdapter):
    """In-memory mock simulation engine for isolated testing and systems without native Gazebo binaries."""

    def __init__(self, scenario: SimulationScenarioSpec):
        super().__init__(scenario)
        self._step_counter = 0
        self._start_monotonic = time.monotonic()
        self._prng = random.Random(scenario.random_seed)

    async def validate_configuration(self) -> bool:
        return True

    async def prepare(self) -> bool:
        self.status = SimulationRunStatus.VALIDATING
        return True

    async def start(self) -> bool:
        self.status = SimulationRunStatus.RUNNING
        self.started_at = datetime.now(timezone.utc)
        self._start_monotonic = time.monotonic()
        return True

    async def pause(self) -> bool:
        if self.status == SimulationRunStatus.RUNNING:
            self.status = SimulationRunStatus.PAUSED
            return True
        return False

    async def resume(self) -> bool:
        if self.status == SimulationRunStatus.PAUSED:
            self.status = SimulationRunStatus.RUNNING
            return True
        return False

    async def reset(self) -> bool:
        self._step_counter = 0
        self.telemetry_count = 0
        self._prng = random.Random(self.scenario.random_seed)
        self.status = SimulationRunStatus.RUNNING
        return True

    async def stop(self) -> bool:
        self.status = SimulationRunStatus.STOPPED
        self.stopped_at = datetime.now(timezone.utc)
        return True

    async def shutdown(self) -> None:
        self.status = SimulationRunStatus.STOPPED

    async def get_telemetry(self) -> VehicleState:
        self._step_counter += 1
        self.telemetry_count += 1
        elapsed = time.monotonic() - self._start_monotonic

        # Generate realistic smooth helical flight trajectory for testing visualization
        radius = 50.0
        angular_speed = 0.1
        lat_base = 37.7749
        lon_base = -122.4194

        lat = lat_base + (radius * math.cos(angular_speed * elapsed)) / 111000.0
        lon = lon_base + (radius * math.sin(angular_speed * elapsed)) / (111000.0 * math.cos(math.radians(lat_base)))
        alt = 10.0 + (elapsed * 0.5) % 40.0

        yaw = (angular_speed * elapsed * 180.0 / math.pi) % 360.0

        return VehicleState(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            sim_time_seconds=round(elapsed, 2),
            vehicle_id=self.scenario.vehicle_config.vehicle_id,
            flight_mode="GUIDED" if self.status == SimulationRunStatus.RUNNING else "PAUSED",
            armed=True,
            position=PositionVector(
                latitude=round(lat, 7),
                longitude=round(lon, 7),
                altitude_msl=round(alt + 100.0, 2),
                altitude_relative=round(alt, 2),
            ),
            velocity=VelocityVector(
                vx=round(-radius * angular_speed * math.sin(angular_speed * elapsed), 2),
                vy=round(radius * angular_speed * math.cos(angular_speed * elapsed), 2),
                vz=0.5,
                ground_speed=round(radius * angular_speed, 2),
            ),
            attitude=AttitudeVector(
                roll_deg=round(math.sin(elapsed) * 5.0, 2),
                pitch_deg=round(math.cos(elapsed) * 3.0, 2),
                yaw_deg=round(yaw, 2),
            ),
            battery=BatteryState(
                voltage_v=round(14.8 - (elapsed * 0.01), 2),
                remaining_percent=max(0.0, round(100.0 - (elapsed * 0.1), 1)),
            ),
            gps=GPSState(fix_type=3, satellites_visible=14, hdop=0.7),
        )


class SimulationEngineFactory:
    """Factory registry for instantiating simulation adapters dynamically."""

    _registry: Dict[str, Type[BaseSimulationAdapter]] = {"mock": MockSimulationEngine}

    @classmethod
    def register(cls, name: str, adapter_cls: Type[BaseSimulationAdapter]) -> None:
        cls._registry[name.lower()] = adapter_cls

    @classmethod
    def create(cls, name: str, scenario: SimulationScenarioSpec) -> BaseSimulationAdapter:
        adapter_cls = cls._registry.get(name.lower())
        if not adapter_cls:
            raise ValueError(f"Unknown simulation engine adapter: '{name}'. Available: {list(cls._registry.keys())}")
        return adapter_cls(scenario)
