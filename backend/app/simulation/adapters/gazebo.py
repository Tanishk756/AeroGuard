"""Gazebo Harmonic Physics Engine Adapter.

Manages Gazebo 'gz sim' process invocation, SDF world file generation,
physics loop execution, and graceful process teardown.
"""

import logging
from typing import Optional

from app.schemas.simulation_platform import (
    SimulationRunStatus,
    SimulationScenarioSpec,
    VehicleState,
)
from app.simulation.core.base_adapter import BaseSimulationAdapter, SimulationEngineFactory
from app.simulation.core.process_manager import ManagedProcess, SimulationProcessManager

logger = logging.getLogger("aeroguard.simulation.gazebo")


class GazeboHarmonicAdapter(BaseSimulationAdapter):
    """Real Gazebo Harmonic simulator adapter."""

    def __init__(self, scenario: SimulationScenarioSpec):
        super().__init__(scenario)
        self._process: Optional[ManagedProcess] = None
        self._executable_path: Optional[str] = None

    async def validate_configuration(self) -> bool:
        path, err = SimulationProcessManager.resolve_executable("gz", "AEROGUARD_GAZEBO_PATH")
        if not path:
            path, err = SimulationProcessManager.resolve_executable("gazebo", "AEROGUARD_GAZEBO_PATH")

        if not path:
            self.status = SimulationRunStatus.FAILED
            logger.error(f"Gazebo validation failed: {err}")
            return False

        self._executable_path = path
        return True

    async def prepare(self) -> bool:
        if not await self.validate_configuration():
            return False
        self.status = SimulationRunStatus.VALIDATING
        return True

    async def start(self) -> bool:
        if not self._executable_path:
            valid = await self.prepare()
            if not valid:
                return False

        cmd_args = [self._executable_path, "sim", "-v", "4", f"{self.scenario.world_name}.sdf"]
        try:
            self._process = await SimulationProcessManager.spawn_process("GazeboHarmonic", cmd_args)
            self.status = SimulationRunStatus.RUNNING
            logger.info(f"Gazebo Harmonic started successfully (PID {self._process.pid})")
            return True
        except Exception as exc:
            self.status = SimulationRunStatus.FAILED
            logger.error(f"Failed to launch Gazebo process: {exc}")
            return False

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
        return True

    async def stop(self) -> bool:
        if self._process:
            await self._process.stop()
            self._process = None
        self.status = SimulationRunStatus.STOPPED
        return True

    async def shutdown(self) -> None:
        await self.stop()

    async def get_telemetry(self) -> VehicleState:
        # Gazebo state is bridged via ROS 2 / MAVLink pipeline
        raise NotImplementedError("Direct Gazebo telemetry requires ROS 2 / MAVLink bridge pipeline")


# Register adapter in Engine Factory
SimulationEngineFactory.register("gazebo", GazeboHarmonicAdapter)
