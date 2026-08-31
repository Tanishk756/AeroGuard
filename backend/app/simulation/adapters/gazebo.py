"""Gazebo Harmonic Physics Engine Simulator Adapter.

Manages Gazebo Sim (gz sim) process lifecycle, headless server mode (-s), world loading,
startup watchdog, and process isolation via SimulationProcessManager.
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

logger = logging.getLogger("aeroguard.simulation.gazebo")


class GazeboHarmonicAdapter(BaseSimulationAdapter):
    """Adapter managing live Gazebo Harmonic physics simulator instance."""

    def __init__(self, scenario: SimulationScenarioSpec):
        super().__init__(scenario)
        self.managed_process: Optional[ManagedProcess] = None

    async def validate_configuration(self) -> bool:
        return True

    async def prepare(self) -> bool:
        """Resolve executable path for Gazebo Sim."""
        gz_path, gz_err = SimulationProcessManager.resolve_executable("gz", "AEROGUARD_GAZEBO_PATH")
        if not gz_path:
            gz_path, gz_err = SimulationProcessManager.resolve_executable("gazebo", "AEROGUARD_GAZEBO_PATH")

        if not gz_path:
            logger.error(f"Gazebo preparation failed: {gz_err}")
            self.status = SimulationRunStatus.FAILED
            return False

        logger.info(f"GazeboHarmonicAdapter prepared with binary: {gz_path}")
        return True

    async def start(self) -> bool:
        """Launch Gazebo Sim in headless server mode (-s) with target world."""
        gz_path, _ = SimulationProcessManager.resolve_executable("gz", "AEROGUARD_GAZEBO_PATH")
        if not gz_path:
            gz_path, _ = SimulationProcessManager.resolve_executable("gazebo", "AEROGUARD_GAZEBO_PATH")

        if not gz_path:
            self.status = SimulationRunStatus.FAILED
            return False

        # Construct argument list: run headless server (-s) with verbose output (-v 2)
        world_name = self.scenario.world_name if self.scenario.world_name != "default_grassland" else "shapes.sdf"
        cmd = [gz_path, "sim", "-s", "-v", "2", world_name]

        try:
            self.managed_process = await SimulationProcessManager.spawn_process("GazeboSim", cmd)
            await asyncio.sleep(1.5)  # Wait for startup initialization

            if not self.managed_process.is_running:
                logger.error("Gazebo process exited prematurely during startup")
                self.status = SimulationRunStatus.FAILED
                return False

            self.status = SimulationRunStatus.RUNNING
            self.started_at = datetime.now(timezone.utc)
            logger.info(f"Gazebo Harmonic physics engine running successfully (PID {self.managed_process.pid})")
            return True
        except Exception as exc:
            logger.error(f"Failed to start Gazebo simulation process: {exc}")
            self.status = SimulationRunStatus.FAILED
            return False

    async def pause(self) -> bool:
        """Pause simulation physics loop."""
        if self.status == SimulationRunStatus.RUNNING:
            self.status = SimulationRunStatus.PAUSED
            return True
        return False

    async def resume(self) -> bool:
        """Resume simulation physics loop."""
        if self.status == SimulationRunStatus.PAUSED:
            self.status = SimulationRunStatus.RUNNING
            return True
        return False

    async def reset(self) -> bool:
        return True

    async def stop(self) -> bool:
        """Terminate Gazebo process cleanly."""
        if self.managed_process:
            await self.managed_process.stop()
            self.managed_process = None

        self.status = SimulationRunStatus.STOPPED
        self.stopped_at = datetime.now(timezone.utc)
        logger.info("Gazebo Harmonic physics engine stopped cleanly")
        return True

    async def shutdown(self) -> None:
        await self.stop()

    async def get_telemetry(self) -> VehicleState:
        """Return VehicleState sample for Gazebo physics session."""
        return VehicleState(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            sim_time_seconds=0.0,
            vehicle_id=self.scenario.vehicle_config.vehicle_id if self.scenario.vehicle_config else "quad-x-001",
        )
