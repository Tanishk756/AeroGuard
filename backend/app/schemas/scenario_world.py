"""Stage S6 Scenario, World, Weather, Physics, and Environment Schemas."""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class EnvironmentConfiguration(BaseModel):
    """Atmospheric, lighting, and gravitational environmental parameters."""
    gravity: List[float] = Field(default=[-0.0, -0.0, -9.80665])  # m/s^2
    atmosphere_pressure_pa: float = Field(default=101325.0)       # Standard sea level pressure
    temperature_k: float = Field(default=288.15)                  # 15 deg C
    lighting_ambient_lux: float = Field(default=1000.0)
    visibility_m: float = Field(default=10000.0)


class WeatherConfiguration(BaseModel):
    """Wind, turbulence, and meteorological parameters."""
    wind_speed_m_s: float = Field(default=0.0, ge=0.0, le=50.0)
    wind_direction_deg: float = Field(default=0.0, ge=0.0, le=360.0)
    turbulence_level: str = Field(default="LOW")  # NONE, LOW, MEDIUM, HIGH


class PhysicsConfiguration(BaseModel):
    """Simulator solver, timestep, and deterministic seed parameters."""
    gravity: float = Field(default=9.80665)
    simulation_rate_hz: float = Field(default=250.0)
    real_time_factor: float = Field(default=1.0)
    step_size_s: float = Field(default=0.004)
    random_seed: int = Field(default=42)


class VehicleSpawnConfiguration(BaseModel):
    """Vehicle spawn position and initial orientation vector."""
    position: List[float] = Field(default=[0.0, 0.0, 0.2])  # [x, y, z] meters
    orientation: List[float] = Field(default=[0.0, 0.0, 0.0])  # [roll, pitch, yaw] deg
    altitude_m: float = Field(default=0.2)
    heading_deg: float = Field(default=0.0)


class WorldObjectSpec(BaseModel):
    """Static box, cylinder, mesh, or landing pad placed in world."""
    id: Optional[str] = None
    object_type: str  # STATIC_BOX, STATIC_CYLINDER, LANDING_PAD
    position: Dict[str, float] = Field(default={"x": 0.0, "y": 0.0, "z": 0.0})
    orientation: Dict[str, float] = Field(default={"roll": 0.0, "pitch": 0.0, "yaw": 0.0})
    scale: Dict[str, float] = Field(default={"x": 1.0, "y": 1.0, "z": 1.0})
    collision_enabled: bool = True
    visual_enabled: bool = True
    metadata: Optional[Dict[str, Any]] = None


class SimulationWorldSpec(BaseModel):
    """Simulator-neutral world containing static objects and ground configuration."""
    id: Optional[str] = None
    project_id: str = "proj-default-01"
    name: str = "Flat Ground World"
    world_type: str = "FLAT_GROUND"  # EMPTY, FLAT_GROUND
    description: Optional[str] = None
    objects: List[WorldObjectSpec] = Field(default_factory=list)


class ScenarioCreate(BaseModel):
    """Request payload to create or version a SimulationScenario."""
    project_id: str = "proj-default-01"
    name: str
    description: Optional[str] = None
    vehicle_id: str
    simulator: str = "GAZEBO"
    autopilot: str = "ARDUPILOT"
    world_id: str
    environment_config: EnvironmentConfiguration = Field(default_factory=EnvironmentConfiguration)
    physics_config: PhysicsConfiguration = Field(default_factory=PhysicsConfiguration)
    weather_config: WeatherConfiguration = Field(default_factory=WeatherConfiguration)
    spawn_config: VehicleSpawnConfiguration = Field(default_factory=VehicleSpawnConfiguration)
    random_seed: int = 42


class ScenarioResponse(BaseModel):
    """Response payload for a versioned SimulationScenario."""
    id: str
    project_id: str
    name: str
    description: Optional[str] = None
    vehicle_id: str
    simulator: str
    autopilot: str
    world_id: str
    environment_config: EnvironmentConfiguration
    physics_config: PhysicsConfiguration
    weather_config: WeatherConfiguration
    spawn_config: VehicleSpawnConfiguration
    random_seed: int
    configuration_version: int
    created_at: str
    updated_at: str


class ScenarioValidationDiagnostic(BaseModel):
    """Diagnostic result from ScenarioValidationEngine."""
    valid: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)


class ScenarioExportPackage(BaseModel):
    """Deterministic JSON export format aeroguard-scenario.json."""
    schema_version: str = "1.0.0-s6"
    scenario: ScenarioResponse
    vehicle_reference_id: str
    world_spec: SimulationWorldSpec
    hash_manifest: Dict[str, str]
