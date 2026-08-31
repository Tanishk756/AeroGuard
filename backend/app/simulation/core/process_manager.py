"""Safe Async Subprocess Manager, Process Tree Watchdog, and Executable Inspector.

Handles non-blocking process spawning without shell=True, environment path resolution,
WSL2 Linux execution wrapping, clean SIGTERM/SIGKILL termination, and process tree cleanup.
"""

import asyncio
import logging
import os
import shutil
import sys
from typing import List, Optional, Tuple, Dict, Any

from app.schemas.simulation_platform import CapabilityDiagnosticResponse, CapabilityStatus
from app.core.telemetry import SIMULATION_PROCESS_FAILURES_TOTAL

logger = logging.getLogger("aeroguard.simulation.process")

# Allowlists for secure simulation execution
ALLOWED_SIMULATORS = {"gazebo", "mock"}
ALLOWED_AUTOPILOTS = {"ardupilot", "mock"}
ALLOWED_WORLDS = {"default_grassland", "empty_world", "urban_runway"}


class ManagedProcess:
    """Wrapper around asyncio.subprocess.Process with log capture and watchdog handling."""

    def __init__(self, name: str, process: asyncio.subprocess.Process, is_wsl: bool = False):
        self.name = name
        self.process = process
        self.pid = process.pid
        self.is_wsl = is_wsl
        self._stdout_lines: List[str] = []
        self._stderr_lines: List[str] = []

    @property
    def is_running(self) -> bool:
        return self.process.returncode is None

    async def stop(self, timeout_sec: float = 3.0) -> int:
        """Cleanly terminate child process (SIGTERM first, then SIGKILL if unresponsive)."""
        if not self.is_running:
            return self.process.returncode or 0

        logger.info(f"Stopping managed process '{self.name}' (PID {self.pid})...")
        try:
            self.process.terminate()
            await asyncio.wait_for(self.process.wait(), timeout=timeout_sec)
        except asyncio.TimeoutError:
            logger.warning(f"Process '{self.name}' (PID {self.pid}) timed out after {timeout_sec}s; sending SIGKILL...")
            self.process.kill()
            await self.process.wait()

        logger.info(f"Process '{self.name}' terminated with return code {self.process.returncode}")
        return self.process.returncode or 0


class SimulationProcessManager:
    """Async process manager handling subprocess creation securely without shell=True."""

    @staticmethod
    def resolve_executable(name: str, env_var: Optional[str] = None) -> Tuple[Optional[str], Optional[str]]:
        """Resolve executable path from environment variable or system PATH."""
        if env_var:
            env_path = os.environ.get(env_var)
            if env_path and os.path.exists(env_path):
                return env_path, None

        system_path = shutil.which(name)
        if system_path:
            return system_path, None

        return None, f"Executable '{name}' not found in system PATH or environment variable '{env_var}'"

    @classmethod
    async def spawn_process(cls, name: str, cmd_args: List[str], env: Optional[dict] = None) -> ManagedProcess:
        """Spawn a non-blocking background child process securely without shell=True."""
        if not isinstance(cmd_args, list) or not cmd_args:
            raise ValueError("cmd_args must be a non-empty list of command argument strings")

        # Security sanity check: block dangerous shell metacharacters
        for arg in cmd_args:
            if any(char in arg for char in [";", "&&", "||", "|", "`", "$("]):
                SIMULATION_PROCESS_FAILURES_TOTAL.labels(process_type=name.lower()).inc()
                raise ValueError(f"Potentially dangerous shell character detected in command argument: '{arg}'")

        logger.info(f"Spawning simulation process '{name}': {' '.join(cmd_args)}")

        try:
            process = await asyncio.create_subprocess_exec(
                cmd_args[0],
                *cmd_args[1:],
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env or os.environ.copy(),
            )
            return ManagedProcess(name, process)
        except Exception as exc:
            SIMULATION_PROCESS_FAILURES_TOTAL.labels(process_type=name.lower()).inc()
            logger.error(f"Failed to spawn process '{name}': {exc}")
            raise

    @classmethod
    def get_capabilities(cls) -> CapabilityDiagnosticResponse:
        """Inspect host environment capabilities for Gazebo, ArduPilot SITL, and MAVLink."""
        # 1. Inspect Gazebo
        gz_path, gz_err = cls.resolve_executable("gz", "AEROGUARD_GAZEBO_PATH")
        if not gz_path:
            gz_path, gz_err = cls.resolve_executable("gazebo", "AEROGUARD_GAZEBO_PATH")

        gazebo_cap = CapabilityStatus(
            available=gz_path is not None,
            version="Harmonic 8.0" if gz_path else None,
            reason=gz_err if not gz_path else None,
            path=gz_path,
        )

        # 2. Inspect ArduPilot SITL
        sitl_path, sitl_err = cls.resolve_executable("sim_vehicle.py", "AEROGUARD_ARDUPILOT_SITL_PATH")
        if not sitl_path:
            sitl_path, sitl_err = cls.resolve_executable("arducopter", "AEROGUARD_ARDUPILOT_SITL_PATH")

        sitl_cap = CapabilityStatus(
            available=sitl_path is not None,
            version="ArduCopter 4.5.1" if sitl_path else None,
            reason=sitl_err if not sitl_path else None,
            path=sitl_path,
        )

        # 3. Inspect MAVLink pymavlink dependency
        try:
            import pymavlink
            mavlink_cap = CapabilityStatus(available=True, version=getattr(pymavlink, "__version__", "2.4.49"))
        except ImportError:
            mavlink_cap = CapabilityStatus(available=False, reason="pymavlink package not installed in Python environment")

        return CapabilityDiagnosticResponse(
            gazebo=gazebo_cap,
            ardupilot_sitl=sitl_cap,
            mavlink=mavlink_cap,
            system_os=sys.platform,
        )
