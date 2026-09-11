"""Tests for Stage S8 Persistent Payload Attachment Registry."""

import pytest
from app.models.hardware_registry import PersistentVehicle, PersistentHardwareComponent
from app.models.sensor_payload import PersistentPayloadInstance


def test_payload_instance_attachment(database):
    """Verify attaching a payload entity to a vehicle digital twin."""
    frame = PersistentHardwareComponent(id="f2", manufacturer="Test", model="Frame", category="frame", mass_g=300)
    motor = PersistentHardwareComponent(id="m2", manufacturer="Test", model="Motor", category="motor", mass_g=50)
    esc = PersistentHardwareComponent(id="e2", manufacturer="Test", model="ESC", category="esc", mass_g=15)
    prop = PersistentHardwareComponent(id="p2", manufacturer="Test", model="Prop", category="propeller", mass_g=15)
    bat = PersistentHardwareComponent(id="b2", manufacturer="Test", model="Bat", category="battery", mass_g=400)
    fc = PersistentHardwareComponent(id="fc2", manufacturer="Test", model="FC", category="flight_controller", mass_g=50)

    vehicle = PersistentVehicle(
        id="v-payload-test-1",
        name="Payload Vehicle",
        vehicle_type="quadcopter",
        frame_id="f2", motor_id="m2", esc_id="e2", propeller_id="p2", battery_id="b2", flight_controller_id="fc2",
        total_mass_g=840.0, estimated_hover_throttle=0.45, thrust_to_weight_ratio=2.2
    )
    database.add_all([frame, motor, esc, prop, bat, fc, vehicle])
    database.commit()

    payload = PersistentPayloadInstance(
        id="p-cam-1",
        vehicle_id=vehicle.id,
        payload_type="CAMERA_PAYLOAD",
        name="4K EO/IR Camera Gimbal",
        mass_g=320.0,
        power_w=8.5,
        position_json={"x": 0.05, "y": 0.0, "z": -0.05},
        orientation_json={"roll": 0, "pitch": 0, "yaw": 0},
    )
    database.add(payload)
    database.commit()

    fetched = database.get(PersistentPayloadInstance, "p-cam-1")
    assert fetched is not None
    assert fetched.payload_type == "CAMERA_PAYLOAD"
    assert fetched.mass_g == 320.0
    assert fetched.power_w == 8.5
