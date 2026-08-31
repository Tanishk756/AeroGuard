"""Stage S5 Dynamic Gazebo SDF Generator Test Suite."""

import pytest
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.simulation.core.vehicle_compiler import VehicleAssemblyCompiler
from app.simulation.core.sdf_generator import GazeboVehicleGenerator


@pytest.fixture
def sample_vehicle(database):
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    gps = PersistentHardwareComponent(id="g1", manufacturer="u-blox", model="M8N", category="gps", mass_g=32.0)

    database.add_all([frame, motor, esc, prop, bat, fc, gps])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-sdf-test",
        project_id="proj-default-01",
        name="SDF Test Quad-X",
        vehicle_type="quadcopter",
        frame_id=frame.id,
        motor_id=motor.id,
        esc_id=esc.id,
        propeller_id=prop.id,
        battery_id=bat.id,
        flight_controller_id=fc.id,
        gps_id=gps.id,
        total_mass_g=1158.0,
    )
    database.add(vehicle)
    database.commit()
    database.refresh(vehicle)
    return vehicle


def test_gazebo_sdf_xml_generation(database, sample_vehicle):
    """VERIFIED: GazeboVehicleGenerator produces valid Gazebo Harmonic SDF 1.9 XML."""
    compiled = VehicleAssemblyCompiler.compile_vehicle(sample_vehicle)
    sdf_xml, sdf_hash = GazeboVehicleGenerator.generate_sdf(compiled)

    assert '<sdf version="1.9">' in sdf_xml
    assert f"<mass>{compiled.total_mass_kg}</mass>" in sdf_xml
    assert "gz-sim-multicopter-motor-model-system" in sdf_xml
    assert "imu_sensor" in sdf_xml
    assert "navsat_sensor" in sdf_xml
    assert len(sdf_hash) == 64
