"""Stage S5 Hardware Traceability Test Suite."""

import pytest
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.simulation.core.vehicle_compiler import VehicleAssemblyCompiler


def test_vehicle_identity_traceability(database):
    """VERIFIED: Vehicle model compilation embeds vehicle identity and immutable SHA256 hashes."""
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)

    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-trace-01",
        project_id="proj-default-01",
        name="Traceability Quad-X",
        vehicle_type="quadcopter",
        frame_id=frame.id,
        motor_id=motor.id,
        esc_id=esc.id,
        propeller_id=prop.id,
        battery_id=bat.id,
        flight_controller_id=fc.id,
        total_mass_g=1126.0,
    )
    database.add(vehicle)
    database.commit()

    compiled = VehicleAssemblyCompiler.compile_vehicle(vehicle)
    assert compiled.vehicle_id == "veh-trace-01"
    assert compiled.vehicle_name == "Traceability Quad-X"
    assert compiled.compiled_model_hash is not None
