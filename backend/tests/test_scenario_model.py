"""Stage S6 Scenario Model Test Suite."""

import pytest
import app.models
from app.models.scenario_world import PersistentScenarioEntity, PersistentSimulationWorld
from app.models.hardware_registry import PersistentVehicle, PersistentHardwareComponent


@pytest.fixture
def sample_setup(database):
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-scen-model-01",
        project_id="proj-default-01",
        name="Scenario Test Quad-X",
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
        id="world-scen-model-01",
        project_id="proj-default-01",
        name="Test World",
        world_type="FLAT_GROUND",
    )
    database.add_all([vehicle, world])
    database.commit()
    return vehicle, world


def test_first_class_scenario_entity_creation(database, sample_setup):
    """VERIFIED: PersistentScenarioEntity creates versioned scenario entity with environment/physics configs."""
    vehicle, world = sample_setup
    scen = PersistentScenarioEntity(
        id="scen-model-test-01",
        project_id="proj-default-01",
        name="Evaluation Flight Alpha",
        vehicle_id=vehicle.id,
        simulator="GAZEBO",
        autopilot="ARDUPILOT",
        world_id=world.id,
        environment_config_json={"gravity": [0, 0, -9.81]},
        physics_config_json={"step_size_s": 0.004, "simulation_rate_hz": 250.0},
        weather_config_json={"wind_speed_m_s": 5.0, "wind_direction_deg": 90.0},
        spawn_config_json={"position": [0.0, 0.0, 0.2]},
        random_seed=42,
        configuration_version=1,
    )
    database.add(scen)
    database.commit()
    database.refresh(scen)

    assert scen.id == "scen-model-test-01"
    assert scen.configuration_version == 1
    assert scen.weather_config_json["wind_speed_m_s"] == 5.0
