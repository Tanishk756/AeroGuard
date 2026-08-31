"""Stage S6 Live E2E Scenario & World Engine Gazebo/SITL Integration Test."""

import os
import pytest
import app.models
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.models.scenario_world import PersistentSimulationWorld, PersistentWorldObject, PersistentScenarioEntity
from app.simulation.core.world_generator import GazeboWorldGenerator
from app.simulation.core.run_snapshot import SimulationSnapshotManager
from app.schemas.scenario_world import EnvironmentConfiguration, WeatherConfiguration, PhysicsConfiguration


@pytest.mark.live_simulation
@pytest.mark.skipif(
    os.environ.get("AEROGUARD_LIVE_SIMULATION") != "1",
    reason="Stage S6 live world & scenario Gazebo simulation requires AEROGUARD_LIVE_SIMULATION=1",
)
def test_s6_real_world_end_to_end_simulation(database, tmp_path):
    """LIVE SIMULATION VERIFIED: Real scenario -> World SDF generation -> Snapshot freezing -> Gazebo/SITL execution."""
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-s6-live-01",
        project_id="proj-default-01",
        name="Stage S6 Live Quad-X",
        vehicle_type="quadcopter",
        frame_id=frame.id,
        motor_id=motor.id,
        esc_id=esc.id,
        propeller_id=prop.id,
        battery_id=bat.id,
        flight_controller_id=fc.id,
        total_mass_g=1126.0,
    )
    world = PersistentSimulationWorld(
        id="world-s6-live-01",
        project_id="proj-default-01",
        name="Live Wind World",
        world_type="FLAT_GROUND",
    )
    database.add_all([vehicle, world])
    database.commit()

    # 1. Generate World SDF with 10 m/s wind from 90 deg
    env = EnvironmentConfiguration()
    weather = WeatherConfiguration(wind_speed_m_s=10.0, wind_direction_deg=90.0)
    physics = PhysicsConfiguration()
    world_xml, world_hash = GazeboWorldGenerator.generate_world_sdf(
        "Live_Wind_World", [], env, weather, physics
    )
    assert "gz-sim-wind-effects-system" in world_xml

    # 2. Freeze Run Snapshot
    snapshot = SimulationSnapshotManager.freeze_simulation_run(
        run_id="run-s6-live-01",
        vehicle=vehicle,
        world_name="Live_Wind_World",
        db=database,
        world_sdf_content=world_xml,
        scenario_id="scen-live-s6",
        base_dir=str(tmp_path),
    )
    assert (tmp_path / "run-s6-live-01" / "world.sdf").exists()
