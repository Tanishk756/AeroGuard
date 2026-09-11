"""Tests for physics impact (mass, CoM, moment of inertia) of mounted sensors and payloads."""

from app.models.hardware_registry import PersistentHardwareComponent
from app.models.sensor_payload import PersistentSensorInstance, PersistentPayloadInstance
from app.simulation.core.physics_model import RigidBodyPhysicsEngine


def test_sensor_and_payload_physics_impact():
    """Verify mounted sensors and payloads shift mass and 3D CoM correctly."""
    frame = PersistentHardwareComponent(id="f3", mass_g=300, dimensions_mm={"wheelbase_mm": 450})
    motor = PersistentHardwareComponent(id="m3", mass_g=50)
    esc = PersistentHardwareComponent(id="e3", mass_g=15)
    prop = PersistentHardwareComponent(id="p3", mass_g=15)
    bat = PersistentHardwareComponent(id="b3", mass_g=400)
    fc = PersistentHardwareComponent(id="fc3", mass_g=50)

    # 1. Base physics without sensors/payloads
    base_physics = RigidBodyPhysicsEngine.compute_physical_properties(
        frame, motor, esc, prop, bat, fc, num_motors=4
    )
    assert base_physics["total_mass_g"] == 1070.0
    assert base_physics["center_of_mass"] == {"x": 0.0, "y": 0.0, "z": 0.0}

    # 2. Physics with mounted offset sensor and heavy camera payload
    sensor = PersistentSensorInstance(
        vehicle_id="v1", sensor_type="IMU", name="imu1", mass_g=20.0, power_w=0.5,
        position_json={"x": 0.0, "y": 0.0, "z": 0.10}
    )
    payload = PersistentPayloadInstance(
        vehicle_id="v1", payload_type="CAMERA_PAYLOAD", name="gimbal", mass_g=300.0, power_w=7.0,
        position_json={"x": 0.10, "y": 0.0, "z": -0.05}
    )

    loaded_physics = RigidBodyPhysicsEngine.compute_physical_properties(
        frame, motor, esc, prop, bat, fc, num_motors=4,
        sensors=[sensor], payloads=[payload]
    )

    assert loaded_physics["total_mass_g"] == 1390.0  # 1070 + 20 + 300
    # CoM shifted forward along X (+0.10 * 0.3kg / 1.36kg = +0.0221m)
    assert loaded_physics["center_of_mass"]["x"] > 0.0
    assert loaded_physics["inertia"]["ixx"] >= base_physics["inertia"]["ixx"]
