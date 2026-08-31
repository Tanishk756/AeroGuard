"""Vehicle Mass & Performance Calculator Engine.

Computes physical parameters: total mass, hover throttle estimate,
maximum theoretical thrust, and thrust-to-weight ratio for UAV configurations.
"""

from typing import Dict, Any, List, Optional
from app.models.hardware_registry import PersistentHardwareComponent


class VehicleCalculator:
    """Computes mass and theoretical flight dynamics estimates for vehicle assemblies."""

    @staticmethod
    def calculate_vehicle_metrics(
        frame: PersistentHardwareComponent,
        motor: PersistentHardwareComponent,
        esc: PersistentHardwareComponent,
        propeller: PersistentHardwareComponent,
        battery: PersistentHardwareComponent,
        flight_controller: PersistentHardwareComponent,
        gps: Optional[PersistentHardwareComponent] = None,
        num_motors: int = 4,
    ) -> Dict[str, float]:
        # 1. Total Mass Calculation
        total_mass_g = (
            frame.mass_g
            + (motor.mass_g * num_motors)
            + (esc.mass_g * num_motors)
            + (propeller.mass_g * num_motors)
            + battery.mass_g
            + flight_controller.mass_g
            + (gps.mass_g if gps else 0.0)
        )

        # 2. Maximum Theoretical Thrust Calculation
        motor_max_thrust_g = 1200.0  # Default 1.2kg per motor if unspecified
        if motor.electrical_specs and isinstance(motor.electrical_specs, dict):
            motor_max_thrust_g = float(motor.electrical_specs.get("max_thrust_g", 1200.0))

        total_max_thrust_g = motor_max_thrust_g * num_motors

        # 3. Thrust-to-Weight Ratio
        tw_ratio = round(total_max_thrust_g / max(total_mass_g, 1.0), 2)

        # 4. Estimated Hover Throttle (Inverse of T/W ratio)
        hover_throttle = round(min(1.0, max(0.1, 1.0 / max(tw_ratio, 0.1))), 2)

        return {
            "total_mass_g": round(total_mass_g, 1),
            "total_max_thrust_g": round(total_max_thrust_g, 1),
            "thrust_to_weight_ratio": tw_ratio,
            "estimated_hover_throttle": hover_throttle,
        }
