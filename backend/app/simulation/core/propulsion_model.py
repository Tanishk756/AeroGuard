"""Stage S5 Motor, ESC, and Propeller Propulsion Dynamics Model."""

from typing import Dict, Any
from app.models.hardware_registry import PersistentHardwareComponent


class PropulsionEngine:
    """Computes RPM, max thrust, torque, and hover throttle estimates from component specs."""

    @classmethod
    def evaluate_propulsion(
        cls,
        motor: PersistentHardwareComponent,
        esc: PersistentHardwareComponent,
        propeller: PersistentHardwareComponent,
        battery: PersistentHardwareComponent,
        total_mass_kg: float,
        num_motors: int = 4,
    ) -> Dict[str, Any]:
        motor_specs = motor.electrical_specs or {}
        bat_specs = battery.electrical_specs or {}

        kv = float(motor_specs.get("kv", 920.0))
        max_v = float(motor_specs.get("max_voltage_v", 16.8))
        bat_v = float(bat_specs.get("nominal_voltage_v", 14.8))
        effective_v = min(max_v, bat_v)

        # 1. No-Load & Estimated Full Load RPM
        no_load_rpm = kv * effective_v
        estimated_max_rpm = round(no_load_rpm * 0.75, 0)  # ~75% loaded efficiency

        # 2. Maximum Theoretical Thrust (g / motor)
        max_thrust_g_per_motor = float(motor_specs.get("max_thrust_g", 1100.0))
        total_max_thrust_kg = (max_thrust_g_per_motor * num_motors) / 1000.0

        # 3. Thrust-to-Weight Ratio
        tw_ratio = round(total_max_thrust_kg / max(total_mass_kg, 0.1), 2)

        # 4. Hover Throttle Estimate (Linearized first-order inverse)
        hover_throttle = round(min(1.0, max(0.1, 1.0 / max(tw_ratio, 0.1))), 2)

        # 5. Torque Estimate (N*m)
        max_current_a = float(motor_specs.get("max_current_a", 18.0))
        # Kt = 9.55 / KV
        kt = 9.55 / max(kv, 1.0)
        max_torque_nm = round(kt * max_current_a, 4)

        return {
            "kv": kv,
            "operating_voltage_v": effective_v,
            "estimated_max_rpm": estimated_max_rpm,
            "max_thrust_g_per_motor": max_thrust_g_per_motor,
            "total_max_thrust_kg": round(total_max_thrust_kg, 3),
            "thrust_to_weight_ratio": tw_ratio,
            "estimated_hover_throttle": hover_throttle,
            "estimated_max_torque_nm": max_torque_nm,
        }
