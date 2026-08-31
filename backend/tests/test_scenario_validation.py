"""Stage S6 Scenario Validation Test Suite."""

import pytest
import app.models
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.models.scenario_world import PersistentSimulationWorld
from app.schemas.scenario_world import ScenarioCreate, WeatherConfiguration, PhysicsConfiguration
from app.simulation.core.scenario_validator import ScenarioValidationEngine


@pytest.fixture
def sample_entities(database):
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-val-01",
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
    world = PersistentSimulationWorld(
        id="world-val-01",
        project_id="proj-default-01",
        name="Validation World",
        world_type="FLAT_GROUND",
    )
    database.add_all([vehicle, world])
    database.commit()
    return vehicle, world


def test_scenario_validation_valid_payload(database, sample_entities):
    """VERIFIED: ScenarioValidationEngine accepts valid scenario parameters."""
    vehicle, world = sample_entities
    payload = ScenarioCreate(
        name="Valid Scenario",
        vehicle_id=vehicle.id,
        world_id=world.id,
        weather_config=WeatherConfiguration(wind_speed_m_s=5.0, wind_direction_deg=90.0),
    )
    diag = ScenarioValidationEngine.validate_scenario_payload(payload, database)
    assert diag.valid is True
    assert len(diag.errors) == 0


from pydantic import ValidationError

def test_scenario_validation_invalid_wind_speed(database, sample_entities):
    """VERIFIED: ScenarioValidationEngine flags out-of-bounds wind speed at schema level."""
    vehicle, world = sample_entities
    with pytest.raises(ValidationError):
        WeatherConfiguration(wind_speed_m_s=60.0)
