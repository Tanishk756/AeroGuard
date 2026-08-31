"""Stage S1 Simulation Platform Pydantic Schemas and Domain Data Models.

Defines simulator-neutral VehicleState vectors, vehicle digital-twin configurations,
simulation scenarios, run lifecycle statuses, and system capability diagnostics.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SimulationRunStatus(str, Enum):
    """Lifecycle statuses for simulation execution runs."""
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    STARTING = "STARTING"
    RUNNING = "RUNNING"
    PAUSED = "PAUSED"
    STOPPING = "STOPPING"
    STOPPED = "STOPPED"
    FAILED = "FAILED"


class SimulatorType(str, Enum):
    """Supported simulation engine types."""
    GAZEBO = "GAZEBO"
    MOCK = "MOCK"


class AutopilotType(str, Enum):
    """Supported flight controller autopilot runtimes."""
    ARDUPILOT = "ARDUPILOT"
    MOCK = "MOCK"


class VehicleType(str, Enum):
    """Supported vehicle frame classifications."""
    QUADROTOR = "QUADROTOR"
    FIXED_WING = "FIXED_WING"
    VTOL = "VTOL"
    ROVER = "ROVER"


# --- Vehicle Digital Twin Schemas ---

class HardwareComponentSpec(BaseModel):
    """Generic hardware component specification snapshot."""
    component_id: str
    category: str  # FRAME, FLIGHT_CONTROLLER, MOTOR, ESC, BATTERY, GNSS, IMU, RADIOS
    manufacturer: str = "Generic"
    model: str
    mass_grams: float = 0.0
    specifications: Dict[str, Any] = Field(default_factory=dict)


class VehicleModelConfig(BaseModel):
    """Canonical digital twin vehicle configuration schema."""
    vehicle_id: str = "quad-x-001"
    name: str = "AeroGuard Quad-X Recon"
    vehicle_type: VehicleType = VehicleType.QUADROTOR
    frame: str = "Quad-X"
    autopilot: AutopilotType = AutopilotType.ARDUPILOT
    firmware_version: str = "ArduCopter 4.5.1"
    total_mass_kg: float = 1.5
    components: List[HardwareComponentSpec] = Field(default_factory=list)


# --- Simulation Scenario & Run Schemas ---

class SimulationScenarioSpec(BaseModel):
    """Configuration specification for a reproducible simulation scenario."""
    scenario_id: str
    name: str
    vehicle_config: VehicleModelConfig = Field(default_factory=VehicleModelConfig)
    simulator_type: SimulatorType = SimulatorType.GAZEBO
    autopilot_type: AutopilotType = AutopilotType.ARDUPILOT
    world_name: str = "default_grassland"
    random_seed: int = 42
    created_at: datetime = Field(default_factory=datetime.utcnow)


class SimulationScenarioCreate(BaseModel):
    name: str
    vehicle_config: Optional[VehicleModelConfig] = None
    simulator_type: SimulatorType = SimulatorType.GAZEBO
    autopilot_type: AutopilotType = AutopilotType.ARDUPILOT
    world_name: str = "default_grassland"
    random_seed: int = 42


class SimulationScenarioResponse(BaseModel):
    id: str
    name: str
    configuration_version: int = 1
    configuration_metadata: Dict[str, Any]
    created_at: datetime


class SimulationRunCreate(BaseModel):
    scenario_id: str


class SimulationRunResponse(BaseModel):
    id: str
    scenario_id: str
    status: SimulationRunStatus
    started_at: Optional[datetime] = None
    stopped_at: Optional[datetime] = None
    telemetry_count: int = 0
    created_at: datetime


# --- Normalized VehicleState Schema ---

class PositionVector(BaseModel):
    latitude: float = 0.0
    longitude: float = 0.0
    altitude_msl: float = 0.0
    altitude_relative: float = 0.0


class VelocityVector(BaseModel):
    vx: float = 0.0
    vy: float = 0.0
    vz: float = 0.0
    ground_speed: float = 0.0


class AttitudeVector(BaseModel):
    roll_deg: float = 0.0
    pitch_deg: float = 0.0
    yaw_deg: float = 0.0


class AngularVelocityVector(BaseModel):
    roll_rate: float = 0.0
    pitch_rate: float = 0.0
    yaw_rate: float = 0.0


class AccelerationVector(BaseModel):
    ax: float = 0.0
    ay: float = 0.0
    az: float = 9.81


class BatteryState(BaseModel):
    voltage_v: float = 14.8
    current_a: float = 0.0
    remaining_percent: float = 100.0
    consumed_mah: float = 0.0


class GPSState(BaseModel):
    fix_type: int = 3  # 3 = 3D Fix
    satellites_visible: int = 12
    hdop: float = 0.8
    vdop: float = 1.0


class LinkStatus(BaseModel):
    rssi_dbm: int = -65
    packet_loss_percent: float = 0.0
    latency_ms: float = 15.0


class VehicleState(BaseModel):
    """Normalized simulator-neutral vehicle telemetry state vector."""
    timestamp_utc: str
    sim_time_seconds: float
    vehicle_id: str
    flight_mode: str = "STABILIZE"
    armed: bool = False
    position: PositionVector = Field(default_factory=PositionVector)
    velocity: VelocityVector = Field(default_factory=VelocityVector)
    attitude: AttitudeVector = Field(default_factory=AttitudeVector)
    angular_velocity: AngularVelocityVector = Field(default_factory=AngularVelocityVector)
    acceleration: AccelerationVector = Field(default_factory=AccelerationVector)
    battery: BatteryState = Field(default_factory=BatteryState)
    gps: GPSState = Field(default_factory=GPSState)
    link_status: LinkStatus = Field(default_factory=LinkStatus)
    sensor_health: Dict[str, bool] = Field(default_factory=lambda: {"imu1": True, "mag1": True, "baro1": True, "gps1": True})


# --- Capability Diagnostic Schema ---

class CapabilityStatus(BaseModel):
    available: bool
    version: Optional[str] = None
    reason: Optional[str] = None
    path: Optional[str] = None


class CapabilityDiagnosticResponse(BaseModel):
    gazebo: CapabilityStatus
    ardupilot_sitl: CapabilityStatus
    mavlink: CapabilityStatus
    system_os: str = "windows"
