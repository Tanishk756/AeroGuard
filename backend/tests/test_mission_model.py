"""Stage S7 Mission Model Test Suite."""

import pytest
import app.models
from app.models.mission import PersistentMission, PersistentMissionItem
from app.models.hardware_registry import PersistentVehicle, PersistentHardwareComponent
from app.models.scenario_world import PersistentSimulationWorld, PersistentScenarioEntity


@pytest.fixture
def sample_mission_entities(database):
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-msn-model-01",
        project_id="proj-default-01",
        name="Mission Test Quad-X",
        vehicle_type="quadcopter",
        frame_id=frame.id,
        motor_id=motor.id,
        esc_id=esc.id,
        propeller_id=prop.id,
        battery_id=bat.id,
        flight_controller_id=fc.id,
        total_mass_g=1126.0,
    )
    world = PersistentSimulationWorld(id="world-msn-01", project_id="proj-default-01", name="Flat Ground", world_type="FLAT_GROUND")
    database.add_all([vehicle, world])
    database.commit()

    scen = PersistentScenarioEntity(
        id="scen-msn-01",
        project_id="proj-default-01",
        name="Mission Scenario",
        vehicle_id=vehicle.id,
        simulator="GAZEBO",
        autopilot="ARDUPILOT",
        world_id=world.id,
        environment_config_json={},
        physics_config_json={},
        weather_config_json={},
        spawn_config_json={},
        random_seed=42,
    )
    database.add(scen)
    database.commit()
    return vehicle, scen


def test_persistent_mission_lifecycle(database, sample_mission_entities):
    """VERIFIED: PersistentMission and PersistentMissionItem cascade lifecycle."""
    vehicle, scen = sample_mission_entities
    mission = PersistentMission(
        id="msn-model-01",
        project_id="proj-default-01",
        vehicle_id=vehicle.id,
        scenario_id=scen.id,
        name="Surveillance Flight Alpha",
        status="CREATED",
    )
    database.add(mission)
    database.commit()

    item1 = PersistentMissionItem(id="mi-01", mission_id=mission.id, sequence=1, command_type="TAKEOFF", altitude_m=20.0)
    item2 = PersistentMissionItem(id="mi-02", mission_id=mission.id, sequence=2, command_type="WAYPOINT", latitude=37.7749, longitude=-122.4194, altitude_m=25.0)
    database.add_all([item1, item2])
    database.commit()
    database.refresh(mission)

    assert len(mission.items) == 2
    assert mission.items[0].command_type == "TAKEOFF"
    assert mission.items[1].latitude == 37.7749
