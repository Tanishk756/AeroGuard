"""ArduPilot SITL Autopilot Adapter.

Manages ArduCopter SITL process launch (sim_vehicle.py / arducopter binary),
command-line argument construction for Quad-X frames, MAVLink socket binding, and clean process termination.
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

logger = logging.getLogger("aeroguard.simulation.ardupilot")


class ArduPilotSITLAdapter(BaseSimulationAdapter):
    """ArduPilot SITL Autopilot adapter."""

    def __init__(self, scenario: SimulationScenarioSpec):
        super().__init__(scenario)
        self._process: Optional[ManagedProcess] = None
        self._executable_path: Optional[str] = None
        self.mavlink_port = 14550

    async def validate_configuration(self) -> bool:
        path, err = SimulationProcessManager.resolve_executable("sim_vehicle.py", "AEROGUARD_ARDUPILOT_SITL_PATH")
        if not path:
            path, err = SimulationProcessManager.resolve_executable("arducopter", "AEROGUARD_ARDUPILOT_SITL_PATH")

        if not path:
            self.status = SimulationRunStatus.FAILED
            logger.error(f"ArduPilot SITL validation failed: {err}")
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

        # Build exact sim_vehicle.py arguments for ArduCopter Quad-X frame
        cmd_args = [
            self._executable_path,
            "-v", "ArduCopter",
            "-f", "quad",
            "--out", f"127.0.0.1:{self.mavlink_port}",
            "--wipe",
        ]
        try:
            self._process = await SimulationProcessManager.spawn_process("ArduPilotSITL", cmd_args)
            self.status = SimulationRunStatus.RUNNING
            logger.info(f"ArduPilot SITL started successfully on MAVLink UDP port {self.mavlink_port} (PID {self._process.pid})")
            return True
        except Exception as exc:
            self.status = SimulationRunStatus.FAILED
            logger.error(f"Failed to launch ArduPilot SITL process: {exc}")
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
        raise NotImplementedError("ArduPilot telemetry is ingested via MAVLinkNormalizer")


# Register adapter in Engine Factory
SimulationEngineFactory.register("ardupilot", ArduPilotSITLAdapter)
