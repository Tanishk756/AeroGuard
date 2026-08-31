"""Stage S4 Hardware Compatibility Engine.

Evaluates electrical, physical, and interface constraints between frame, motors, ESCs,
propellers, battery, flight controller, and GPS components.
"""

from typing import List, Optional
from app.models.hardware_registry import PersistentHardwareComponent
from app.schemas.hardware_registry import VehicleCompatibilityDiagnostic
from app.simulation.core.vehicle_calculator import VehicleCalculator
from app.core.telemetry import HARDWARE_VALIDATION_FAILURES, VEHICLE_VALIDATION_TOTAL


class HardwareCompatibilityEngine:
    """Deterministic validation engine inspecting hardware specification constraints."""

    @classmethod
    def validate_vehicle_assembly(
        cls,
        frame: PersistentHardwareComponent,
        motor: PersistentHardwareComponent,
        esc: PersistentHardwareComponent,
        propeller: PersistentHardwareComponent,
        battery: PersistentHardwareComponent,
        flight_controller: PersistentHardwareComponent,
        gps: Optional[PersistentHardwareComponent] = None,
        vehicle_id: Optional[str] = None,
    ) -> VehicleCompatibilityDiagnostic:
        VEHICLE_VALIDATION_TOTAL.inc()
        errors: List[str] = []
        warnings: List[str] = []

        motor_specs = motor.electrical_specs or {}
        esc_specs = esc.electrical_specs or {}
        battery_specs = battery.electrical_specs or {}

        # 1. Voltage Compatibility Check (Motor max voltage vs. Battery voltage)
        motor_max_v = float(motor_specs.get("max_voltage_v", 25.2))
        battery_v = float(battery_specs.get("nominal_voltage_v", 14.8))
        if battery_v > motor_max_v:
            errors.append(f"Motor voltage rating ({motor_max_v:.1f}V) exceeded by battery pack ({battery_v:.1f}V)")

        # 2. ESC Current Rating Check (Motor max current vs. ESC continuous current)
        motor_max_a = float(motor_specs.get("max_current_a", 30.0))
        esc_rating_a = float(esc_specs.get("current_rating_a", 30.0))
        if motor_max_a > esc_rating_a:
            errors.append(f"Motor max current ({motor_max_a:.1f}A) exceeds ESC continuous rating ({esc_rating_a:.1f}A)")

        # 3. ESC Cell Count Support Check
        battery_s = int(battery_specs.get("cell_count_s", 4))
        esc_min_s = int(esc_specs.get("min_cells", 2))
        esc_max_s = int(esc_specs.get("max_cells", 6))
        if not (esc_min_s <= battery_s <= esc_max_s):
            errors.append(f"Battery cell count ({battery_s}S) outside ESC supported range ({esc_min_s}S - {esc_max_s}S)")

        # 4. Calculate Mass & Thrust-to-Weight
        metrics = VehicleCalculator.calculate_vehicle_metrics(
            frame, motor, esc, propeller, battery, flight_controller, gps, num_motors=4
        )

        tw_ratio = metrics["thrust_to_weight_ratio"]
        if tw_ratio < 1.2:
            errors.append(f"Insufficient Thrust-to-Weight ratio ({tw_ratio:.2f}); minimum 1.2 required for flight")
        elif tw_ratio < 1.5:
            warnings.append(f"Marginal Thrust-to-Weight ratio ({tw_ratio:.2f}); recommended > 1.8")

        is_compatible = len(errors) == 0

        if not is_compatible:
            HARDWARE_VALIDATION_FAILURES.inc()

        return VehicleCompatibilityDiagnostic(
            vehicle_id=vehicle_id,
            compatible=is_compatible,
            errors=errors,
            warnings=warnings,
            total_mass_g=metrics["total_mass_g"],
            estimated_hover_throttle=metrics["estimated_hover_throttle"],
            thrust_to_weight_ratio=tw_ratio,
        )
