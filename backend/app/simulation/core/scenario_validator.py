"""Stage S6 Scenario Validation Engine.

Performs deterministic validation of vehicle existence, world specs, physics bounds, and weather settings.
"""

from typing import Optional
from sqlalchemy.orm import Session

from app.models.hardware_registry import PersistentVehicle
from app.models.scenario_world import PersistentSimulationWorld, PersistentScenarioEntity
from app.schemas.scenario_world import ScenarioCreate, ScenarioValidationDiagnostic
from app.core.telemetry import SCENARIOS_VALIDATED_TOTAL, SCENARIO_VALIDATION_FAILURES_TOTAL


class ScenarioValidationEngine:
    """Validates complete scenario configuration integrity without silent corrections."""

    @classmethod
    def validate_scenario_payload(
        cls,
        payload: ScenarioCreate,
        db: Session,
    ) -> ScenarioValidationDiagnostic:
        SCENARIOS_VALIDATED_TOTAL.inc()
        errors = []
        warnings = []

        # 1. Vehicle Existence Validation
        vehicle = db.get(PersistentVehicle, payload.vehicle_id)
        if not vehicle:
            errors.append(f"Referenced vehicle '{payload.vehicle_id}' does not exist in registry.")

        # 2. Simulator & Autopilot Support Validation
        if payload.simulator.upper() not in ("GAZEBO", "MOCK"):
            errors.append(f"Unsupported simulator engine '{payload.simulator}'. Must be GAZEBO or MOCK.")

        if payload.autopilot.upper() not in ("ARDUPILOT", "GENERIC"):
            errors.append(f"Unsupported autopilot stack '{payload.autopilot}'. Must be ARDUPILOT.")

        # 3. World Model Validation
        world = db.get(PersistentSimulationWorld, payload.world_id)
        if not world:
            errors.append(f"Referenced world '{payload.world_id}' does not exist.")

        # 4. Environment & Physics Validation
        if payload.physics_config.step_size_s <= 0:
            errors.append(f"Physics step size ({payload.physics_config.step_size_s}s) must be positive.")

        if payload.physics_config.simulation_rate_hz <= 0:
            errors.append(f"Simulation rate ({payload.physics_config.simulation_rate_hz}Hz) must be positive.")

        if payload.environment_config.atmosphere_pressure_pa <= 0:
            errors.append(f"Atmospheric pressure ({payload.environment_config.atmosphere_pressure_pa}Pa) must be positive.")

        # 5. Weather Parameters Validation
        if payload.weather_config.wind_speed_m_s < 0 or payload.weather_config.wind_speed_m_s > 50.0:
            errors.append(f"Wind speed ({payload.weather_config.wind_speed_m_s} m/s) out of valid range [0, 50].")

        if payload.weather_config.wind_speed_m_s > 15.0:
            warnings.push if hasattr(warnings, 'push') else warnings.append(f"High wind speed ({payload.weather_config.wind_speed_m_s} m/s) may destabilize light multicopters.")

        is_valid = len(errors) == 0
        if not is_valid:
            SCENARIO_VALIDATION_FAILURES_TOTAL.inc()

        return ScenarioValidationDiagnostic(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
        )
