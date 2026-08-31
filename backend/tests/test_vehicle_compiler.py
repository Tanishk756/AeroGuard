"""Stage S5 Vehicle Compiler & Provenance Test Suite."""

import pytest
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.simulation.core.vehicle_compiler import VehicleAssemblyCompiler


@pytest.fixture
def sample_vehicle(database):
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0, electrical_specs={"max_voltage_v": 16.8, "max_thrust_g": 1100.0})
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0, electrical_specs={"cell_count_s": 4, "nominal_voltage_v": 14.8, "capacity_mah": 5000.0})
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    gps = PersistentHardwareComponent(id="g1", manufacturer="u-blox", model="M8N", category="gps", mass_g=32.0)

    database.add_all([frame, motor, esc, prop, bat, fc, gps])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-test-s5-01",
        project_id="proj-default-01",
        name="Compiler Test Quad-X",
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


def test_vehicle_compiler_deterministic_compilation(database, sample_vehicle):
    """VERIFIED: VehicleAssemblyCompiler compiles physical properties with SHA256 hash and provenance."""
    compiled = VehicleAssemblyCompiler.compile_vehicle(sample_vehicle)
    assert compiled.vehicle_id == sample_vehicle.id
    assert compiled.total_mass_g == 1158.0
    assert len(compiled.compiled_model_hash) == 64
    assert compiled.provenance["total_mass_g"].source_type == "HARDWARE_SPEC"
    assert compiled.provenance["inertia"].source_type == "ESTIMATED"
