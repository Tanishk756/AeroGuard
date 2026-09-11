"""Stage S9 Multi-Autopilot Hardware Abstraction Layer Architecture.

Provides unified contracts and interfaces for ArduPilot (ArduCopter) and PX4 SITL autopilots.
"""

from abc import abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from app.schemas.simulation_platform import (
    AutopilotType,
    SimulationScenarioSpec,
    VehicleState,
)
from app.simulation.core.base_adapter import BaseSimulationAdapter


class AutopilotCapability(str, Enum):
    """Capabilities supported by flight controller autopilots."""
    WAYPOINT_MISSION = "WAYPOINT_MISSION"
    TAKEOFF_COMMAND = "TAKEOFF_COMMAND"
    LAND_COMMAND = "LAND_COMMAND"
    RTL_COMMAND = "RTL_COMMAND"
    SET_MODE_GUIDED = "SET_MODE_GUIDED"
    SET_MODE_AUTO = "SET_MODE_AUTO"
    SET_MODE_OFFBOARD = "SET_MODE_OFFBOARD"
    TELEMETRY_STREAM = "TELEMETRY_STREAM"
    SENSOR_HEALTH = "SENSOR_HEALTH"


class AutopilotHealthStatus(BaseModel):
    """Autopilot hardware/SITL runtime readiness status."""
    autopilot_type: AutopilotType
    ready: bool
    status: str  # READY, INITIALIZING, DISCONNECTED, ERROR, BLOCKED
    connected: bool = False
    active_mode: str = "UNKNOWN"
    armed: bool = False
    mavlink_system_id: int = 1
    mavlink_component_id: int = 1
    environment_blocked: bool = False
    error_message: Optional[str] = None


class BaseAutopilotAdapter(BaseSimulationAdapter):
    """Abstract base adapter for flight controller SITL instances (ArduPilot, PX4, Mock)."""

    def __init__(self, scenario: SimulationScenarioSpec, autopilot_type: AutopilotType):
        super().__init__(scenario)
        self.autopilot_type = autopilot_type
        self.current_mode: str = "INITIALIZING"
        self.is_armed: bool = False

    @abstractmethod
    def get_capabilities(self) -> List[AutopilotCapability]:
        """Return list of supported capabilities for this autopilot runtime."""
        pass

    @abstractmethod
    async def check_health(self) -> AutopilotHealthStatus:
        """Check SITL runtime health, readiness, and MAVLink connectivity."""
        pass

    @abstractmethod
    async def upload_mission(self, mission_data: Dict[str, Any]) -> Dict[str, Any]:
        """Translate and upload mission items to autopilot."""
        pass

    @abstractmethod
    async def arm(self, force: bool = False) -> bool:
        """Arm vehicle flight controller motors."""
        pass

    @abstractmethod
    async def disarm(self) -> bool:
        """Disarm vehicle flight controller motors."""
        pass

    @abstractmethod
    async def set_flight_mode(self, mode_name: str) -> bool:
        """Change active flight mode (e.g., GUIDED, AUTO, OFFBOARD, RTL)."""
        pass

    @abstractmethod
    async def takeoff(self, altitude_m: float = 10.0) -> bool:
        """Execute automated takeoff command."""
        pass

    @abstractmethod
    async def land(self) -> bool:
        """Execute automated landing command."""
        pass
