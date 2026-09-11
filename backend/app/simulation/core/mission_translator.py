"""Stage S9 Multi-Autopilot Mission Translation Engine.

Translates AeroGuard unified CompiledMission specifications into autopilot-specific MAVLink command items
for ArduPilot (ArduCopter) and PX4, with strict validation for command support, coordinate frames, and parameters.
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from app.schemas.simulation_platform import AutopilotType
from app.schemas.mission import CompiledMission, CompiledMissionItem


class MissionTranslationDiagnostic(BaseModel):
    """Diagnostic report from mission translation engine."""
    valid: bool
    autopilot_type: AutopilotType
    total_items: int = 0
    translated_count: int = 0
    errors: List[str] = Field(default_factory=list)
    warnings: List[str] = Field(default_factory=list)
    translated_items: List[Dict[str, Any]] = Field(default_factory=list)


class MissionTranslator:
    """Translator converting simulator-neutral missions to ArduPilot and PX4 MAVLink format."""

    SUPPORTED_COMMANDS = {"TAKEOFF", "WAYPOINT", "LOITER", "LAND", "RETURN_TO_HOME", "RTL"}

    MAV_CMD_MAP = {
        "WAYPOINT": 16,
        "TAKEOFF": 22,
        "LOITER": 19,
        "LAND": 21,
        "RETURN_TO_HOME": 20,
        "RTL": 20,
    }

    @classmethod
    def translate(cls, mission: CompiledMission, target_autopilot: AutopilotType) -> MissionTranslationDiagnostic:
        errors: List[str] = []
        warnings: List[str] = []
        translated_items: List[Dict[str, Any]] = []

        if not mission.items:
            errors.append("Mission contains no flight waypoints or commands.")
            return MissionTranslationDiagnostic(
                valid=False,
                autopilot_type=target_autopilot,
                total_items=0,
                translated_count=0,
                errors=errors,
            )

        for idx, item in enumerate(mission.items):
            cmd_upper = item.command_type.upper()

            # 1. Validate Command Support
            if cmd_upper not in cls.SUPPORTED_COMMANDS:
                errors.append(f"Item #{item.sequence}: Command '{item.command_type}' is unsupported by {target_autopilot.value}.")
                continue

            # 2. Validate Latitude / Longitude / Altitude boundaries
            if cmd_upper not in ("RETURN_TO_HOME", "RTL"):
                if item.latitude < -90.0 or item.latitude > 90.0:
                    errors.append(f"Item #{item.sequence}: Invalid latitude '{item.latitude}'; must be in [-90, 90].")
                if item.longitude < -180.0 or item.longitude > 180.0:
                    errors.append(f"Item #{item.sequence}: Invalid longitude '{item.longitude}'; must be in [-180, 180].")
                if item.altitude_m < 0.0 or item.altitude_m > 500.0:
                    errors.append(f"Item #{item.sequence}: Invalid altitude '{item.altitude_m}m'; must be in [0, 500]m.")

            mav_cmd = cls.MAV_CMD_MAP.get(cmd_upper, 16)

            # 3. Autopilot-Specific Translation
            if target_autopilot == AutopilotType.ARDUPILOT or target_autopilot == AutopilotType.MOCK:
                translated_item = cls._translate_ardupilot(item, mav_cmd)
            elif target_autopilot == AutopilotType.PX4:
                translated_item = cls._translate_px4(item, mav_cmd)
            else:
                errors.append(f"Unsupported target autopilot type: {target_autopilot}")
                continue

            translated_items.append(translated_item)

        valid = len(errors) == 0
        return MissionTranslationDiagnostic(
            valid=valid,
            autopilot_type=target_autopilot,
            total_items=len(mission.items),
            translated_count=len(translated_items),
            errors=errors,
            warnings=warnings,
            translated_items=translated_items,
        )

    @classmethod
    def _translate_ardupilot(cls, item: CompiledMissionItem, mav_cmd: int) -> Dict[str, Any]:
        """Translate item to ArduPilot MAVLink structure."""
        return {
            "seq": item.sequence,
            "frame": 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
            "command": mav_cmd,
            "current": 1 if item.sequence == 1 else 0,
            "autocontinue": 1,
            "param1": item.loiter_duration_s if mav_cmd == 19 else 0.0,
            "param2": item.acceptance_radius_m if mav_cmd == 16 else 0.0,
            "param3": 0.0,
            "param4": 0.0,
            "x_lat": int(item.latitude * 1e7),
            "y_lon": int(item.longitude * 1e7),
            "z_alt": item.altitude_m,
            "autopilot_target": "ARDUPILOT",
        }

    @classmethod
    def _translate_px4(cls, item: CompiledMissionItem, mav_cmd: int) -> Dict[str, Any]:
        """Translate item to PX4 MAVLink structure."""
        return {
            "seq": item.sequence,
            "frame": 3,  # MAV_FRAME_GLOBAL_RELATIVE_ALT
            "command": mav_cmd,
            "current": 1 if item.sequence == 1 else 0,
            "autocontinue": 1,
            "param1": item.loiter_duration_s if mav_cmd in (16, 19) else (15.0 if mav_cmd == 22 else 0.0),  # Pitch angle for takeoff
            "param2": item.acceptance_radius_m if mav_cmd == 16 else 0.0,
            "param3": 0.0,
            "param4": 0.0,
            "param5_lat": item.latitude,
            "param6_lon": item.longitude,
            "param7_alt": item.altitude_m,
            "autopilot_target": "PX4",
        }
