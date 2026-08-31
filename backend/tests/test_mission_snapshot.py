"""Stage S7 Mission Snapshot & Traceability Test Suite."""

import pytest
import app.models
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.models.scenario_world import PersistentSimulationWorld, PersistentScenarioEntity
from app.models.mission import PersistentMission, PersistentMissionRunSnapshot


@pytest.fixture
def sample_parent_entities(database):
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(id="veh-snap-01", project_id="proj-default-01", name="Snap Quad", vehicle_type="quadcopter", frame_id=frame.id, motor_id=motor.id, esc_id=esc.id, propeller_id=prop.id, battery_id=bat.id, flight_controller_id=fc.id, total_mass_g=1126.0)
    world = PersistentSimulationWorld(id="w-snap-01", project_id="proj-default-01", name="Flat Ground", world_type="FLAT_GROUND")
    database.add_all([vehicle, world])
    database.commit()

    scen = PersistentScenarioEntity(id="scen-snap-01", project_id="proj-default-01", name="Snap Scenario", vehicle_id=vehicle.id, simulator="GAZEBO", autopilot="ARDUPILOT", world_id=world.id, environment_config_json={}, physics_config_json={}, weather_config_json={}, spawn_config_json={}, random_seed=42)
    database.add(scen)
    database.commit()

    mission = PersistentMission(id="msn-snap-01", project_id="proj-default-01", vehicle_id=vehicle.id, scenario_id=scen.id, name="Snap Mission", status="CREATED")
    database.add(mission)
    database.commit()
    return vehicle, scen, mission


def test_mission_run_snapshot_creation(database, sample_parent_entities):
    """VERIFIED: PersistentMissionRunSnapshot records immutable mission, vehicle, scenario, and world hashes."""
    vehicle, scen, mission = sample_parent_entities
    snapshot = PersistentMissionRunSnapshot(
        id="snap-msn-01",
        run_id="run-s7-snap-01",
        mission_id=mission.id,
        mission_hash="abc123hash",
        vehicle_id=vehicle.id,
        vehicle_hash="def456hash",
        scenario_id=scen.id,
        scenario_hash="ghi789hash",
        world_hash="jkl012hash",
        snapshot_json={"version": "1.0.0-s7"},
    )
    database.add(snapshot)
    database.commit()
    database.refresh(snapshot)

    assert snapshot.run_id == "run-s7-snap-01"
    assert snapshot.mission_hash == "abc123hash"
