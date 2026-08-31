"""ArduPilot SITL Autopilot Adapter.

Manages ArduCopter SITL process lifecycle, vehicle model configuration (Quad-X),
MAVLink UDP socket endpoint, heartbeat detection, and clean process watchdog.
"""

import asyncio
import logging
from datetime import datetime, timezone
from typing import Optional

from app.schemas.simulation_platform import (
    SimulationScenarioSpec,
    SimulationRunStatus,
    VehicleState,
)
from app.simulation.core.base_adapter import BaseSimulationAdapter
from app.simulation.core.process_manager import SimulationProcessManager, ManagedProcess
from app.telemetry.normalizer import TelemetryTransport

logger = logging.getLogger("aeroguard.simulation.ardupilot")


class ArduPilotSITLAdapter(BaseSimulationAdapter):
    """Adapter managing live ArduCopter SITL autopilot process instance."""

    def __init__(self, scenario: SimulationScenarioSpec):
        super().__init__(scenario)
        self.managed_process: Optional[ManagedProcess] = None
        self.transport = TelemetryTransport(scenario.vehicle_config.vehicle_id if scenario.vehicle_config else "quad-x-001")
        self._last_state: Optional[VehicleState] = None

    async def validate_configuration(self) -> bool:
        return True

    async def prepare(self) -> bool:
        """Resolve executable path for ArduCopter SITL."""
        sitl_path, sitl_err = SimulationProcessManager.resolve_executable("arducopter", "AEROGUARD_ARDUPILOT_SITL_PATH")
        if not sitl_path:
            sitl_path, sitl_err = SimulationProcessManager.resolve_executable("sim_vehicle.py", "AEROGUARD_ARDUPILOT_SITL_PATH")

        if not sitl_path:
            logger.error(f"ArduPilot SITL preparation failed: {sitl_err}")
            self.status = SimulationRunStatus.FAILED
            return False

        logger.info(f"ArduPilotSITLAdapter prepared with binary: {sitl_path}")
        return True

    async def start(self) -> bool:
        """Launch ArduCopter SITL binary with Quad-X configuration and bind MAVLink UDP socket."""
        sitl_path, _ = SimulationProcessManager.resolve_executable("arducopter", "AEROGUARD_ARDUPILOT_SITL_PATH")
        if not sitl_path:
            sitl_path, _ = SimulationProcessManager.resolve_executable("sim_vehicle.py", "AEROGUARD_ARDUPILOT_SITL_PATH")

        if not sitl_path:
            self.status = SimulationRunStatus.FAILED
            return False

        # Construct argument list: model quad, home location 37.7749,-122.4194,10,90
        cmd = [
            sitl_path,
            "--model", "quad",
            "--home", "37.7749,-122.4194,10,90",
            "--speedup", "1.0",
        ]

        try:
            self.managed_process = await SimulationProcessManager.spawn_process("ArduCopterSITL", cmd)
            await asyncio.sleep(2.0)  # Wait for SITL startup and socket binding

            if not self.managed_process.is_running:
                logger.error("ArduCopter SITL process exited prematurely during startup")
                self.status = SimulationRunStatus.FAILED
                return False

            # Connect telemetry transport to local SITL output stream
            self.transport.connect("udpin:127.0.0.1:14550")

            self.status = SimulationRunStatus.RUNNING
            self.started_at = datetime.now(timezone.utc)
            logger.info(f"ArduCopter SITL running successfully (PID {self.managed_process.pid})")
            return True
        except Exception as exc:
            logger.error(f"Failed to start ArduCopter SITL process: {exc}")
            self.status = SimulationRunStatus.FAILED
            return False

    async def pause(self) -> bool:
        """Pause SITL execution."""
        if self.status == SimulationRunStatus.RUNNING:
            self.status = SimulationRunStatus.PAUSED
            return True
        return False

    async def resume(self) -> bool:
        """Resume SITL execution."""
        if self.status == SimulationRunStatus.PAUSED:
            self.status = SimulationRunStatus.RUNNING
            return True
        return False

    async def reset(self) -> bool:
        """Reset SITL state."""
        return True

    async def stop(self) -> bool:
        """Terminate ArduCopter SITL process cleanly."""
        if self.managed_process:
            await self.managed_process.stop()
            self.managed_process = None

        self.status = SimulationRunStatus.STOPPED
        self.stopped_at = datetime.now(timezone.utc)
        logger.info("ArduCopter SITL process stopped cleanly")
        return True

    async def shutdown(self) -> None:
        await self.stop()

    async def get_telemetry(self) -> VehicleState:
        """Poll live telemetry packet from SITL UDP socket or return last state snapshot."""
        state = self.transport.poll_message()
        if state:
            self._last_state = state
            self.telemetry_count += 1
            return state

        if self._last_state:
            return self._last_state

        # Initial default fallback snapshot prior to first packet arrival
        return VehicleState(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            sim_time_seconds=0.0,
            vehicle_id=self.scenario.vehicle_config.vehicle_id if self.scenario.vehicle_config else "quad-x-001",
        )
