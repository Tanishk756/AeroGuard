"""Stage S4 Hardware Registry & Vehicle Builder Integration Test Suite."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from app.main import app
from app.models.role import Role
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.simulation.core.compatibility import HardwareCompatibilityEngine
from app.simulation.core.vehicle_calculator import VehicleCalculator


@pytest.fixture
def sample_components(database):
    """Seed test database with verified sample reference components."""
    frame = PersistentHardwareComponent(
        id="test-frame-01",
        manufacturer="Holybro",
        model="S500 Quad-X",
        category="frame",
        mass_g=280.0,
    )
    motor = PersistentHardwareComponent(
        id="test-motor-01",
        manufacturer="T-Motor",
        model="MN2212 920KV",
        category="motor",
        mass_g=55.0,
        electrical_specs={"max_voltage_v": 16.8, "max_current_a": 18.0, "max_thrust_g": 1100.0},
    )
    esc = PersistentHardwareComponent(
        id="test-esc-01",
        manufacturer="Holybro",
        model="Tekko32 30A",
        category="esc",
        mass_g=12.0,
        electrical_specs={"current_rating_a": 30.0, "min_cells": 2, "max_cells": 6},
    )
    prop = PersistentHardwareComponent(
        id="test-prop-01",
        manufacturer="Gemfan",
        model="1045 Propellers",
        category="propeller",
        mass_g=15.0,
    )
    battery = PersistentHardwareComponent(
        id="test-bat-01",
        manufacturer="Tattu",
        model="4S 5000mAh",
        category="battery",
        mass_g=450.0,
        electrical_specs={"cell_count_s": 4, "nominal_voltage_v": 14.8, "capacity_mah": 5000.0},
    )
    fc = PersistentHardwareComponent(
        id="test-fc-01",
        manufacturer="Holybro",
        model="Pixhawk 4",
        category="flight_controller",
        mass_g=68.0,
    )
    gps = PersistentHardwareComponent(
        id="test-gps-01",
        manufacturer="u-blox",
        model="NEO-M8N",
        category="gps",
        mass_g=32.0,
    )

    database.add_all([frame, motor, esc, prop, battery, fc, gps])
    database.commit()

    return {
        "frame": frame,
        "motor": motor,
        "esc": esc,
        "prop": prop,
        "battery": battery,
        "fc": fc,
        "gps": gps,
    }


def test_hardware_registry_crud_api(client):
    """VERIFIED: Hardware registry CRUD API endpoints."""
    # 1. List categories
    cat_resp = client.get("/api/v1/hardware/categories")
    assert cat_resp.status_code == 200
    assert "motor" in cat_resp.json()

    # 2. Create Component
    create_resp = client.post(
        "/api/v1/hardware",
        json={
            "manufacturer": "BetaFPV",
            "model": "1103 11000KV",
            "category": "motor",
            "mass_g": 3.8,
            "electrical_specs": {"max_voltage_v": 8.4, "max_current_a": 6.0},
        },
    )
    assert create_resp.status_code == 201
    comp_data = create_resp.json()
    comp_id = comp_data["id"]

    # 3. Get Component
    get_resp = client.get(f"/api/v1/hardware/{comp_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["model"] == "1103 11000KV"

    # 4. Delete Component
    del_resp = client.delete(f"/api/v1/hardware/{comp_id}")
    assert del_resp.status_code == 204


def test_vehicle_calculator_and_compatibility_engine(sample_components):
    """VERIFIED: Physical mass calculation, T/W ratio, and deterministic compatibility validation."""
    c = sample_components
    diag = HardwareCompatibilityEngine.validate_vehicle_assembly(
        c["frame"], c["motor"], c["esc"], c["prop"], c["battery"], c["fc"], c["gps"]
    )
    assert diag.compatible is True
    assert diag.total_mass_g == 1158.0
    assert diag.thrust_to_weight_ratio > 3.0
    assert diag.estimated_hover_throttle < 0.4


def test_incompatible_hardware_assembly_rejection(database, sample_components):
    """VERIFIED: Incompatible voltage/current hardware combinations are rejected."""
    c = sample_components

    # High Voltage Battery (8S 29.6V) exceeding 4S Motor rating (16.8V)
    bad_bat = PersistentHardwareComponent(
        id="bad-bat-8s",
        manufacturer="Overvolt",
        model="8S LiPo",
        category="battery",
        mass_g=800.0,
        electrical_specs={"cell_count_s": 8, "nominal_voltage_v": 29.6},
    )
    database.add(bad_bat)
    database.commit()

    diag = HardwareCompatibilityEngine.validate_vehicle_assembly(
        c["frame"], c["motor"], c["esc"], c["prop"], bad_bat, c["fc"], c["gps"]
    )
    assert diag.compatible is False
    assert any("voltage" in err.lower() for err in diag.errors)


def test_vehicle_crud_and_simulation_generation(client, sample_components):
    """VERIFIED: Vehicle assembly creation, validation, and 'Simulate This Vehicle' scenario generation."""
    c = sample_components
    v_resp = client.post(
        "/api/v1/vehicles",
        json={
            "project_id": "proj-default-01",
            "name": "Integration Quad-X",
            "vehicle_type": "quadcopter",
            "frame_id": c["frame"].id,
            "motor_id": c["motor"].id,
            "esc_id": c["esc"].id,
            "propeller_id": c["prop"].id,
            "battery_id": c["battery"].id,
            "flight_controller_id": c["fc"].id,
            "gps_id": c["gps"].id,
        },
    )
    assert v_resp.status_code == 201
    v_data = v_resp.json()
    vehicle_id = v_data["id"]
    assert v_data["total_mass_g"] == 1158.0

    # Simulate Vehicle Action
    sim_resp = client.post(f"/api/v1/vehicles/{vehicle_id}/simulate")
    assert sim_resp.status_code == 200
    sim_data = sim_resp.json()
    assert "Digital Twin Simulation" in sim_data["name"]
