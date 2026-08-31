"""Stage S7 Mission Validation Engine.

Performs deterministic validation of item sequence, contiguous ordering, geographic bounds, altitude limits, and vehicle/scenario existence.
"""

from typing import List
from sqlalchemy.orm import Session

from app.models.hardware_registry import PersistentVehicle
from app.models.scenario_world import PersistentScenarioEntity
from app.schemas.mission import MissionCreate, MissionItemSpec, MissionValidationDiagnostic
from app.core.telemetry import MISSIONS_VALIDATED_TOTAL, MISSION_VALIDATION_FAILURES_TOTAL


class MissionValidationEngine:
    """Validates complete mission specification integrity without silent corrections."""

    @classmethod
    def validate_mission_payload(
        cls,
        payload: MissionCreate,
        db: Session,
    ) -> MissionValidationDiagnostic:
        MISSIONS_VALIDATED_TOTAL.inc()
        errors = []
        warnings = []

        # 1. Vehicle & Scenario Existence Check
        vehicle = db.get(PersistentVehicle, payload.vehicle_id)
        if not vehicle:
            errors.append(f"Referenced vehicle '{payload.vehicle_id}' does not exist.")

        scenario = db.get(PersistentScenarioEntity, payload.scenario_id)
        if not scenario:
            errors.append(f"Referenced scenario '{payload.scenario_id}' does not exist.")

        # 2. Items List Presence
        if not payload.items or len(payload.items) == 0:
            errors.append("Mission must contain at least one mission item.")
            MISSION_VALIDATION_FAILURES_TOTAL.inc()
            return MissionValidationDiagnostic(valid=False, errors=errors, warnings=warnings)

        # 3. Sequence Ordering & Contiguity Check
        seqs = [item.sequence for item in payload.items]
        if len(seqs) != len(set(seqs)):
            errors.append("Mission items must have unique sequence numbers.")

        expected_seqs = list(range(1, len(payload.items) + 1))
        if sorted(seqs) != expected_seqs:
            errors.append(f"Mission item sequences must be contiguous starting at 1. Found: {seqs}")

        # 4. Item Parameter & Geographic Sanity Check
        for idx, item in enumerate(payload.items):
            # Takeoff Rule
            if item.command_type == "TAKEOFF" and idx != 0:
                warnings.append(f"Item {item.sequence} (TAKEOFF) is placed after mission start.")

            # Altitude Bounds
            if item.altitude_m < 0.0 or item.altitude_m > 500.0:
                errors.append(f"Item {item.sequence} altitude ({item.altitude_m}m) out of bounds [1, 500]m.")

            # Coordinate Validation for Waypoints
            if item.command_type in ("WAYPOINT", "LOITER"):
                if item.latitude is None or item.longitude is None:
                    errors.append(f"Item {item.sequence} ({item.command_type}) missing latitude/longitude coordinates.")
                else:
                    if item.latitude < -90.0 or item.latitude > 90.0:
                        errors.append(f"Item {item.sequence} latitude ({item.latitude}) invalid.")
                    if item.longitude < -180.0 or item.longitude > 180.0:
                        errors.append(f"Item {item.sequence} longitude ({item.longitude}) invalid.")

        is_valid = len(errors) == 0
        if not is_valid:
            MISSION_VALIDATION_FAILURES_TOTAL.inc()

        return MissionValidationDiagnostic(
            valid=is_valid,
            errors=errors,
            warnings=warnings,
        )
