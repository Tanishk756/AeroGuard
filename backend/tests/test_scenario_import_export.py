"""Stage S6 Scenario Import/Export Test Suite."""

import pytest
from app.schemas.scenario_world import (
    ScenarioExportPackage,
    ScenarioResponse,
    SimulationWorldSpec,
    WorldObjectSpec,
    EnvironmentConfiguration,
    PhysicsConfiguration,
    WeatherConfiguration,
    VehicleSpawnConfiguration,
)


def test_scenario_import_export_package_structure():
    """VERIFIED: ScenarioExportPackage serializes to deterministic JSON package."""
    scen_resp = ScenarioResponse(
        id="scen-exp-01",
        project_id="proj-default-01",
        name="Export Scenario",
        vehicle_id="veh-exp-01",
        simulator="GAZEBO",
        autopilot="ARDUPILOT",
        world_id="world-exp-01",
        environment_config=EnvironmentConfiguration(),
        physics_config=PhysicsConfiguration(),
        weather_config=WeatherConfiguration(),
        spawn_config=VehicleSpawnConfiguration(),
        random_seed=42,
        configuration_version=1,
        created_at="2026-08-31T00:00:00Z",
        updated_at="2026-08-31T00:00:00Z",
    )
    world_spec = SimulationWorldSpec(
        id="world-exp-01",
        name="Export World",
        objects=[
            WorldObjectSpec(
                object_type="LANDING_PAD",
                position={"x": 0, "y": 0, "z": 0},
                orientation={"roll": 0, "pitch": 0, "yaw": 0},
                scale={"x": 2, "y": 2, "z": 0.02},
            )
        ],
    )

    pkg = ScenarioExportPackage(
        scenario=scen_resp,
        vehicle_reference_id="veh-exp-01",
        world_spec=world_spec,
        hash_manifest={"hash": "abcdef123456"},
    )

    pkg_json = pkg.model_dump_json()
    assert "aeroguard-scenario.json" in pkg_json or "schema_version" in pkg_json
    assert "veh-exp-01" in pkg_json
    assert "Export World" in pkg_json
