"""Tests for Stage S9 Multi-Autopilot Mission Translation Engine."""

import pytest
from app.schemas.simulation_platform import AutopilotType
from app.schemas.mission import CompiledMission, CompiledMissionItem
from app.simulation.core.mission_translator import MissionTranslator


def test_mission_translation_ardupilot():
    """Verify translating compiled mission to ArduPilot MAVLink structure."""
    compiled = CompiledMission(
        mission_id="m-101",
        version=1,
        vehicle_id="v1",
        scenario_id="s1",
        compiled_mission_hash="hash-123",
        items=[
            CompiledMissionItem(sequence=1, command_type="TAKEOFF", latitude=37.7749, longitude=-122.4194, altitude_m=10.0, acceptance_radius_m=2.0, loiter_duration_s=0.0),
            CompiledMissionItem(sequence=2, command_type="WAYPOINT", latitude=37.7755, longitude=-122.4190, altitude_m=20.0, acceptance_radius_m=3.0, loiter_duration_s=0.0),
            CompiledMissionItem(sequence=3, command_type="RETURN_TO_HOME", latitude=0.0, longitude=0.0, altitude_m=0.0, acceptance_radius_m=2.0, loiter_duration_s=0.0),
        ]
    )

    diag = MissionTranslator.translate(compiled, AutopilotType.ARDUPILOT)
    assert diag.valid is True
    assert diag.translated_count == 3
    assert diag.translated_items[0]["command"] == 22  # TAKEOFF
    assert diag.translated_items[0]["x_lat"] == 377749000
    assert diag.translated_items[1]["command"] == 16  # WAYPOINT
    assert diag.translated_items[2]["command"] == 20  # RTL


def test_mission_translation_px4():
    """Verify translating compiled mission to PX4 MAVLink structure."""
    compiled = CompiledMission(
        mission_id="m-102",
        version=1,
        vehicle_id="v1",
        scenario_id="s1",
        compiled_mission_hash="hash-456",
        items=[
            CompiledMissionItem(sequence=1, command_type="TAKEOFF", latitude=37.7749, longitude=-122.4194, altitude_m=15.0, acceptance_radius_m=2.0, loiter_duration_s=0.0),
            CompiledMissionItem(sequence=2, command_type="WAYPOINT", latitude=37.7755, longitude=-122.4190, altitude_m=25.0, acceptance_radius_m=4.0, loiter_duration_s=5.0),
            CompiledMissionItem(sequence=3, command_type="LAND", latitude=37.7755, longitude=-122.4190, altitude_m=0.0, acceptance_radius_m=2.0, loiter_duration_s=0.0),
        ]
    )

    diag = MissionTranslator.translate(compiled, AutopilotType.PX4)
    assert diag.valid is True
    assert diag.translated_count == 3
    assert diag.translated_items[0]["command"] == 22  # TAKEOFF
    assert diag.translated_items[0]["param7_alt"] == 15.0
    assert diag.translated_items[1]["command"] == 16  # WAYPOINT
    assert diag.translated_items[1]["param5_lat"] == 37.7755
    assert diag.translated_items[2]["command"] == 21  # LAND


def test_mission_translation_unsupported_command_and_invalid_params():
    """Verify mission translation catches unsupported commands and out-of-range parameters."""
    compiled = CompiledMission(
        mission_id="m-invalid",
        version=1,
        vehicle_id="v1",
        scenario_id="s1",
        compiled_mission_hash="hash-err",
        items=[
            CompiledMissionItem(sequence=1, command_type="UNSUPPORTED_MAGIC", latitude=37.7749, longitude=-122.4194, altitude_m=10.0, acceptance_radius_m=2.0, loiter_duration_s=0.0),
            CompiledMissionItem(sequence=2, command_type="WAYPOINT", latitude=150.0, longitude=-122.4190, altitude_m=-5.0, acceptance_radius_m=2.0, loiter_duration_s=0.0),
        ]
    )

    diag = MissionTranslator.translate(compiled, AutopilotType.PX4)
    assert diag.valid is False
    assert len(diag.errors) >= 2
    assert "unsupported" in diag.errors[0].lower()
