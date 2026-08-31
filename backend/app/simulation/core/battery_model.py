"""Stage S5 Battery Electrical & Energy Dynamics Model."""

from typing import Dict, Any
from app.models.hardware_registry import PersistentHardwareComponent


class BatteryEnergyEngine:
    """Computes total energy, hover current draw, power consumption, and runtime estimates."""

    @classmethod
    def evaluate_battery(
        cls,
        battery: PersistentHardwareComponent,
        total_mass_kg: float,
        hover_throttle: float,
        num_motors: int = 4,
    ) -> Dict[str, Any]:
        bat_specs = battery.electrical_specs or {}

        cell_count_s = int(bat_specs.get("cell_count_s", 4))
        nominal_voltage_v = float(bat_specs.get("nominal_voltage_v", 14.8))
        capacity_mah = float(bat_specs.get("capacity_mah", 5000.0))
        capacity_ah = capacity_mah / 1000.0

        # 1. Total Stored Electrical Energy (Watt-Hours)
        total_energy_wh = round(nominal_voltage_v * capacity_ah, 2)

        # 2. Estimated Power Required to Hover (W = mass_kg * g * V_descent / efficiency)
        # Empirical rule of thumb: ~150W per kg for typical multicopters
        hover_power_w = round(total_mass_kg * 150.0, 1)

        # 3. Estimated Hover Current Draw (Amperes)
        hover_current_a = round(hover_power_w / max(nominal_voltage_v, 1.0), 2)

        # 4. Estimated Hover Runtime (Minutes) assuming 80% usable depth of discharge (DoD)
        usable_capacity_ah = capacity_ah * 0.80
        runtime_hours = usable_capacity_ah / max(hover_current_a, 0.1)
        estimated_runtime_min = round(runtime_hours * 60.0, 1)

        return {
            "cell_count_s": cell_count_s,
            "nominal_voltage_v": nominal_voltage_v,
            "capacity_ah": capacity_ah,
            "total_energy_wh": total_energy_wh,
            "estimated_hover_power_w": hover_power_w,
            "estimated_hover_current_a": hover_current_a,
            "estimated_runtime_min": estimated_runtime_min,
        }
