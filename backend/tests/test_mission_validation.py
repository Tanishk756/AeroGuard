"""Stage S7 Mission Validation Test Suite."""

import pytest
import app.models
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.models.scenario_world import PersistentSimulationWorld, PersistentScenarioEntity
from app.schemas.mission import MissionCreate, MissionItemSpec
from app.simulation.core.mission_validator import MissionValidationEngine


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
        id="veh-val-msn-01",
        project_id="proj-default-01",
        name="Validation Quad-X",
        vehicle_type="quadcopter",
        frame_id=frame.id,
        motor_id=motor.id,
        esc_id=esc.id,
        propeller_id=prop.id,
        battery_id=bat.id,
        flight_controller_id=fc.id,
        total_mass_g=1126.0,
    )
    world = PersistentSimulationWorld(id="w-val-01", project_id="proj-default-01", name="Flat Ground", world_type="FLAT_GROUND")
    database.add_all([vehicle, world])
    database.commit()

    scen = PersistentScenarioEntity(
        id="scen-val-01",
        project_id="proj-default-01",
        name="Validation Scenario",
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


def test_mission_validation_valid_sequence(database, sample_setup):
    """VERIFIED: MissionValidationEngine approves valid contiguous mission items."""
    vehicle, scen = sample_setup
    payload = MissionCreate(
        vehicle_id=vehicle.id,
        scenario_id=scen.id,
        name="Valid Flight",
        items=[
            MissionItemSpec(sequence=1, command_type="TAKEOFF", altitude_m=20.0),
            MissionItemSpec(sequence=2, command_type="WAYPOINT", latitude=37.7749, longitude=-122.4194, altitude_m=25.0),
            MissionItemSpec(sequence=3, command_type="LAND", altitude_m=1.0),
        ],
    )
    diag = MissionValidationEngine.validate_mission_payload(payload, database)
    assert diag.valid is True
    assert len(diag.errors) == 0


def test_mission_validation_non_contiguous_sequence(database, sample_setup):
    """VERIFIED: MissionValidationEngine flags non-contiguous sequence numbers."""
    vehicle, scen = sample_setup
    payload = MissionCreate(
        vehicle_id=vehicle.id,
        scenario_id=scen.id,
        name="Invalid Sequence Flight",
        items=[
            MissionItemSpec(sequence=1, command_type="TAKEOFF", altitude_m=20.0),
            MissionItemSpec(sequence=3, command_type="WAYPOINT", latitude=37.7749, longitude=-122.4194, altitude_m=25.0),
        ],
    )
    diag = MissionValidationEngine.validate_mission_payload(payload, database)
    assert diag.valid is False
    assert any("contiguous" in e for e in diag.errors)
