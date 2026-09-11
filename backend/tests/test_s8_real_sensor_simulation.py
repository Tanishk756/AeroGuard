"""Integration test for Stage S8 Real Sensor & Payload Digital Twin Simulation chain."""

import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import get_db
from app.models.hardware_registry import PersistentVehicle, PersistentHardwareComponent
from app.models.sensor_payload import PersistentSensorInstance, PersistentPayloadInstance

client = TestClient(app)


def test_s8_sensor_payload_integration_chain(client, database):
    """Verify complete end-to-end chain from vehicle assembly -> sensors/payloads -> power budget -> SDF."""
    frame = PersistentHardwareComponent(id="f-s8", manufacturer="Holybro", model="S500", category="frame", mass_g=280)
    motor = PersistentHardwareComponent(id="m-s8", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55)
    esc = PersistentHardwareComponent(id="e-s8", manufacturer="Holybro", model="30A", category="esc", mass_g=12)
    prop = PersistentHardwareComponent(id="p-s8", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15)
    bat = PersistentHardwareComponent(id="b-s8", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450)
    fc = PersistentHardwareComponent(id="fc-s8", manufacturer="Holybro", model="Pixhawk 4", category="flight_controller", mass_g=68)

    vehicle = PersistentVehicle(
        id="v-s8-chain-1",
        name="Stage S8 Sensor Twin",
        vehicle_type="quadcopter",
        frame_id="f-s8", motor_id="m-s8", esc_id="e-s8", propeller_id="p-s8", battery_id="b-s8", flight_controller_id="fc-s8",
        total_mass_g=1000.0, estimated_hover_throttle=0.45, thrust_to_weight_ratio=2.2
    )
    database.add_all([frame, motor, esc, prop, bat, fc, vehicle])
    database.commit()

    # 1. Add Sensor via REST API
    res_s = client.post(f"/api/v1/vehicles/{vehicle.id}/sensors", json={
        "vehicle_id": vehicle.id,
        "sensor_type": "IMU",
        "name": "High-Hz Nav IMU",
        "mass_g": 18.0,
        "power_w": 0.5,
        "position": {"x": 0, "y": 0, "z": 0.05},
        "orientation": {"roll": 0, "pitch": 0, "yaw": 0},
        "update_rate_hz": 250.0,
        "health_status": "OK"
    })
    assert res_s.status_code == 201
    sensor_data = res_s.json()
    assert sensor_data["sensor_type"] == "IMU"

    # 2. Add Payload via REST API
    res_p = client.post(f"/api/v1/vehicles/{vehicle.id}/payloads", json={
        "vehicle_id": vehicle.id,
        "payload_type": "CAMERA_PAYLOAD",
        "name": "4K Gimbal Camera",
        "mass_g": 250.0,
        "power_w": 6.0,
        "position": {"x": 0.05, "y": 0, "z": -0.05},
        "orientation": {"roll": 0, "pitch": 0, "yaw": 0}
    })
    assert res_p.status_code == 201
    payload_data = res_p.json()
    assert payload_data["payload_type"] == "CAMERA_PAYLOAD"

    # 3. Check Power Budget via REST API
    res_pb = client.get(f"/api/v1/vehicles/{vehicle.id}/power-budget")
    assert res_pb.status_code == 200
    pb = res_pb.json()
    assert pb["sensor_power_w"] == 0.5
    assert pb["payload_power_w"] == 6.0
    assert pb["total_non_propulsion_power_w"] == 11.5  # 5.0 + 0.5 + 6.0

    # 4. Generate dynamic Gazebo SDF XML
    res_sdf = client.post(f"/api/v1/vehicles/{vehicle.id}/sdf")
    assert res_sdf.status_code == 200
    sdf_res = res_sdf.json()
    assert "sdf_xml" in sdf_res
    assert sdf_res["artifact_hash"] is not None

    # 5. Inject Sensor Fault
    res_fault = client.post("/api/v1/simulation/fail-sensor", json={
        "run_id": "run-s8-e2e",
        "sensor_type": "GPS",
        "fault_type": "DISCONNECTED"
    })
    assert res_fault.status_code == 200
    fault_res = res_fault.json()
    assert fault_res["fault_type"] == "SENSOR_GPS_DISCONNECTED"
