"""Stage S5 Vehicle Assembly Compiler & Provenance Engine.

Compiles persistent vehicle hardware references into a deterministic physical model with SHA256 hash
and explicit provenance tracking (HARDWARE_SPEC, ESTIMATED, USER_DEFINED, SIMULATOR_GENERATED).
"""

import hashlib
import json
from typing import Dict, Any, List, Tuple
from pydantic import BaseModel, Field

from app.models.hardware_registry import PersistentVehicle, PersistentHardwareComponent
from app.simulation.core.physics_model import RigidBodyPhysicsEngine
from app.simulation.core.propulsion_model import PropulsionEngine
from app.simulation.core.battery_model import BatteryEnergyEngine


class PropertyProvenance(BaseModel):
    """Provenance tracking record for physical properties."""
    source_type: str  # HARDWARE_SPEC, ESTIMATED, USER_DEFINED, SIMULATOR_GENERATED
    description: str


class CompiledVehicleModel(BaseModel):
    """Deterministic compiled physical model of a UAV configuration."""
    vehicle_id: str
    vehicle_name: str
    vehicle_type: str
    compiled_model_hash: str

    # Physical Properties
    total_mass_kg: float
    total_mass_g: float
    wheelbase_mm: float
    arm_length_m: float
    center_of_mass: Dict[str, float]
    inertia: Dict[str, float]
    motor_positions: List[Tuple[float, float, float]]

    # Propulsion Properties
    operating_voltage_v: float
    estimated_max_rpm: float
    total_max_thrust_kg: float
    thrust_to_weight_ratio: float
    estimated_hover_throttle: float
    estimated_max_torque_nm: float

    # Battery Properties
    cell_count_s: int
    nominal_voltage_v: float
    capacity_ah: float
    total_energy_wh: float
    estimated_hover_power_w: float
    estimated_hover_current_a: float
    estimated_runtime_min: float

    # Provenance Map
    provenance: Dict[str, PropertyProvenance]


class VehicleAssemblyCompiler:
    """Simulator-neutral compiler resolving hardware entities into deterministic physical models."""

    @classmethod
    def compile_vehicle(cls, vehicle: PersistentVehicle) -> CompiledVehicleModel:
        frame = vehicle.frame
        motor = vehicle.motor
        esc = vehicle.esc
        prop = vehicle.propeller
        battery = vehicle.battery
        fc = vehicle.flight_controller
        gps = vehicle.gps

        # 1. Physics Calculations
        physics = RigidBodyPhysicsEngine.compute_physical_properties(
            frame, motor, esc, prop, battery, fc, gps, num_motors=4
        )

        # 2. Propulsion Calculations
        propulsion = PropulsionEngine.evaluate_propulsion(
            motor, esc, prop, battery, physics["total_mass_kg"], num_motors=4
        )

        # 3. Battery Energy Calculations
        battery_dynamics = BatteryEnergyEngine.evaluate_battery(
            battery, physics["total_mass_kg"], propulsion["estimated_hover_throttle"], num_motors=4
        )

        # 4. Property Provenance Mapping
        provenance = {
            "total_mass_g": PropertyProvenance(
                source_type="HARDWARE_SPEC",
                description="Summed manufacturer component masses",
            ),
            "inertia": PropertyProvenance(
                source_type="ESTIMATED",
                description="First-order central hub + motor point-mass rigid body tensor",
            ),
            "center_of_mass": PropertyProvenance(
                source_type="ESTIMATED",
                description="Assumed symmetric Quad-X origin",
            ),
            "thrust_to_weight_ratio": PropertyProvenance(
                source_type="ESTIMATED",
                description="Theoretical max thrust over total mass",
            ),
            "estimated_hover_throttle": PropertyProvenance(
                source_type="ESTIMATED",
                description="Inverse of thrust-to-weight ratio",
            ),
            "estimated_runtime_min": PropertyProvenance(
                source_type="ESTIMATED",
                description="Calculated from 80% battery capacity DoD over hover current draw",
            ),
        }

        # 5. Deterministic SHA256 Hash Generation
        hash_payload = {
            "vehicle_id": vehicle.id,
            "frame_id": frame.id,
            "motor_id": motor.id,
            "esc_id": esc.id,
            "prop_id": prop.id,
            "bat_id": battery.id,
            "fc_id": fc.id,
            "gps_id": gps.id if gps else None,
            "physics": physics,
            "propulsion": propulsion,
            "battery_dynamics": battery_dynamics,
        }

        model_hash = hashlib.sha256(
            json.dumps(hash_payload, sort_keys=True).encode("utf-8")
        ).hexdigest()

        return CompiledVehicleModel(
            vehicle_id=vehicle.id,
            vehicle_name=vehicle.name,
            vehicle_type=vehicle.vehicle_type,
            compiled_model_hash=model_hash,
            total_mass_kg=physics["total_mass_kg"],
            total_mass_g=physics["total_mass_g"],
            wheelbase_mm=physics["wheelbase_mm"],
            arm_length_m=physics["arm_length_m"],
            center_of_mass=physics["center_of_mass"],
            inertia=physics["inertia"],
            motor_positions=physics["motor_positions"],
            operating_voltage_v=propulsion["operating_voltage_v"],
            estimated_max_rpm=propulsion["estimated_max_rpm"],
            total_max_thrust_kg=propulsion["total_max_thrust_kg"],
            thrust_to_weight_ratio=propulsion["thrust_to_weight_ratio"],
            estimated_hover_throttle=propulsion["estimated_hover_throttle"],
            estimated_max_torque_nm=propulsion["estimated_max_torque_nm"],
            cell_count_s=battery_dynamics["cell_count_s"],
            nominal_voltage_v=battery_dynamics["nominal_voltage_v"],
            capacity_ah=battery_dynamics["capacity_ah"],
            total_energy_wh=battery_dynamics["total_energy_wh"],
            estimated_hover_power_w=battery_dynamics["estimated_hover_power_w"],
            estimated_hover_current_a=battery_dynamics["estimated_hover_current_a"],
            estimated_runtime_min=battery_dynamics["estimated_runtime_min"],
            provenance=provenance,
        )
