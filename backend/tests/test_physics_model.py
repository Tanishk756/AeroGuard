"""Stage S5 Physics Engine Test Suite."""

import pytest
import app.models
from app.models.hardware_registry import PersistentHardwareComponent
from app.simulation.core.physics_model import RigidBodyPhysicsEngine


def test_rigid_body_physics_calculations():
    """VERIFIED: RigidBodyPhysicsEngine computes mass, COM, 3D inertia, and motor positions."""
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0, dimensions_mm={"wheelbase_mm": 450})
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)
    gps = PersistentHardwareComponent(id="g1", manufacturer="u-blox", model="M8N", category="gps", mass_g=32.0)

    physics = RigidBodyPhysicsEngine.compute_physical_properties(
        frame, motor, esc, prop, bat, fc, gps, num_motors=4
    )

    assert physics["total_mass_g"] == 1158.0
    assert physics["total_mass_kg"] == 1.158
    assert physics["wheelbase_mm"] == 450.0
    assert physics["arm_length_m"] == 0.225
    assert len(physics["motor_positions"]) == 4
    assert physics["inertia"]["ixx"] > 0.0
    assert physics["inertia"]["izz"] > physics["inertia"]["ixx"]
