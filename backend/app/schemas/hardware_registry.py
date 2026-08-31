"""Stage S4 Hardware Registry & Vehicle Builder Domain Schemas.

Defines Pydantic data contracts for hardware components, motor/ESC/battery/FC specifications,
vehicle configurations, physical parameter calculations, and compatibility diagnostics.
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class HardwareCategory(str, Enum):
    FRAME = "frame"
    MOTOR = "motor"
    ESC = "esc"
    PROPELLER = "propeller"
    BATTERY = "battery"
    FLIGHT_CONTROLLER = "flight_controller"
    AUTOPILOT = "autopilot"
    GPS = "gps"
    RADIO = "radio"
    CAMERA = "camera"
    PAYLOAD = "payload"
    SENSOR = "sensor"


class MotorSpecificationSchema(BaseModel):
    kv_rating: float = Field(..., description="Motor velocity constant in RPM per volt")
    max_voltage_v: float = Field(..., description="Maximum operating voltage in Volts")
    max_current_a: float = Field(..., description="Maximum continuous current rating in Amperes")
    max_thrust_g: float = Field(..., description="Maximum static thrust in grams")
    shaft_diameter_mm: float = Field(..., description="Motor output shaft diameter in millimeters")


class EscSpecificationSchema(BaseModel):
    current_rating_a: float = Field(..., description="Continuous current rating in Amperes")
    peak_current_a: float = Field(..., description="Burst peak current rating in Amperes")
    min_cells: int = Field(1, description="Minimum supported battery cell count")
    max_cells: int = Field(6, description="Maximum supported battery cell count")
    protocol: str = Field("DShot600", description="Motor control protocol")
    telemetry_capable: bool = Field(True, description="Supports ESC telemetry output")


class PropellerSpecificationSchema(BaseModel):
    diameter_inch: float = Field(..., description="Propeller diameter in inches")
    pitch_inch: float = Field(..., description="Propeller pitch in inches")
    blades: int = Field(2, description="Number of propeller blades")
    rotation_direction: str = Field("CW_CCW_PAIR", description="Rotation direction configuration")


class BatterySpecificationSchema(BaseModel):
    chemistry: str = Field("LiPo", description="Battery chemistry type")
    cell_count_s: int = Field(..., description="Series cell count (e.g. 4 for 4S)")
    nominal_voltage_v: float = Field(..., description="Nominal pack voltage in Volts")
    capacity_mah: float = Field(..., description="Total battery capacity in milliampere-hours")
    continuous_discharge_c: float = Field(..., description="Continuous discharge rate C rating")


class FlightControllerSpecificationSchema(BaseModel):
    mcu_family: str = Field("STM32F765", description="Microcontroller unit architecture")
    imu_sensor: str = Field("ICM-20689", description="Primary Inertial Measurement Unit sensor")
    baro_sensor: str = Field("MS5611", description="Barometric altimeter sensor")
    compass_sensor: Optional[str] = Field("IST8310", description="Magnetometer compass sensor")
    uart_ports: int = Field(6, description="Number of hardware serial UART ports")
    can_bus: bool = Field(True, description="Supports CAN bus interface")


class GpsSpecificationSchema(BaseModel):
    gnss_constellations: List[str] = Field(default_factory=lambda: ["GPS", "GLONASS"], description="Supported GNSS systems")
    update_rate_hz: int = Field(10, description="Navigation update rate in Hz")
    interface_type: str = Field("UART", description="Interface connector type")


class HardwareComponentCreate(BaseModel):
    manufacturer: str
    model: str
    category: HardwareCategory
    part_number: Optional[str] = None
    datasheet_url: Optional[str] = None
    mass_g: float = Field(..., ge=0.0, description="Mass of component in grams")
    dimensions_mm: Optional[Dict[str, float]] = None
    electrical_specs: Optional[Dict[str, Any]] = None
    interfaces: Optional[List[str]] = None
    supported_simulation_models: Optional[List[str]] = None
    metadata_json: Optional[Dict[str, Any]] = None


class HardwareComponentResponse(HardwareComponentCreate):
    id: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class VehicleCreate(BaseModel):
    project_id: str = Field("proj-default-01", description="Associated project ID")
    name: str = Field(..., description="Vehicle name")
    vehicle_type: str = Field("quadcopter", description="Vehicle airframe classification")
    frame_id: str = Field(..., description="Frame hardware component ID")
    motor_id: str = Field(..., description="Motor hardware component ID")
    esc_id: str = Field(..., description="ESC hardware component ID")
    propeller_id: str = Field(..., description="Propeller hardware component ID")
    battery_id: str = Field(..., description="Battery hardware component ID")
    flight_controller_id: str = Field(..., description="Flight controller hardware component ID")
    gps_id: Optional[str] = Field(None, description="GPS hardware component ID")


class VehicleCompatibilityDiagnostic(BaseModel):
    vehicle_id: Optional[str] = None
    compatible: bool
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    total_mass_g: float = 0.0
    estimated_hover_throttle: float = 0.5
    thrust_to_weight_ratio: float = 2.0


class VehicleResponse(BaseModel):
    id: str
    project_id: str
    name: str
    vehicle_type: str
    frame_id: str
    motor_id: str
    esc_id: str
    propeller_id: str
    battery_id: str
    flight_controller_id: str
    gps_id: Optional[str] = None
    total_mass_g: float
    estimated_hover_throttle: float
    thrust_to_weight_ratio: float
    compatibility: VehicleCompatibilityDiagnostic
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
