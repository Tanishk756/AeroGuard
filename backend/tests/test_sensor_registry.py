"""Tests for Stage S8 Persistent Sensor Registry."""

import pytest
from app.models.hardware_registry import PersistentVehicle, PersistentHardwareComponent
from app.models.sensor_payload import PersistentSensorInstance
from app.schemas.sensor_payload import SensorInstanceSpec


def test_sensor_instance_creation(database):
    """Verify creating a vehicle-mounted sensor instance entity."""
    frame = PersistentHardwareComponent(id="f1", manufacturer="Test", model="Frame", category="frame", mass_g=300)
    motor = PersistentHardwareComponent(id="m1", manufacturer="Test", model="Motor", category="motor", mass_g=50)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Test", model="ESC", category="esc", mass_g=15)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Test", model="Prop", category="propeller", mass_g=15)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Test", model="Bat", category="battery", mass_g=400)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Test", model="FC", category="flight_controller", mass_g=50)

    vehicle = PersistentVehicle(
        id="v-sensor-test-1",
        name="Test Vehicle",
        vehicle_type="quadcopter",
        frame_id="f1", motor_id="m1", esc_id="e1", propeller_id="p1", battery_id="b1", flight_controller_id="fc1",
        total_mass_g=840.0, estimated_hover_throttle=0.45, thrust_to_weight_ratio=2.2
    )
    database.add_all([frame, motor, esc, prop, bat, fc, vehicle])
    database.commit()

    sensor = PersistentSensorInstance(
        id="s-imu-1",
        vehicle_id=vehicle.id,
        sensor_type="IMU",
        name="High-Grade IMU",
        mass_g=20.0,
        power_w=0.6,
        position_json={"x": 0.0, "y": 0.0, "z": 0.05},
        orientation_json={"roll": 0, "pitch": 0, "yaw": 0},
        update_rate_hz=250.0,
        health_status="OK",
    )
    database.add(sensor)
    database.commit()

    fetched = database.get(PersistentSensorInstance, "s-imu-1")
    assert fetched is not None
    assert fetched.sensor_type == "IMU"
    assert fetched.mass_g == 20.0
    assert fetched.update_rate_hz == 250.0
