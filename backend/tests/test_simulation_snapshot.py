"""Stage S5 Simulation Snapshot & Artifact Isolation Test Suite."""

import pytest
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.simulation.core.run_snapshot import SimulationSnapshotManager


@pytest.fixture
def sample_vehicle(database):
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)

    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-snap-test",
        project_id="proj-default-01",
        name="Snapshot Test Quad-X",
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
    database.refresh(vehicle)
    return vehicle


def test_simulation_run_freezing_and_artifact_isolation(database, sample_vehicle, tmp_path):
    """VERIFIED: SimulationSnapshotManager creates isolated artifact dir and freezes database snapshot."""
    run_info = SimulationSnapshotManager.freeze_simulation_run(
        run_id="run-test-snap-01",
        vehicle=sample_vehicle,
        world_name="shapes.sdf",
        db=database,
        base_dir=str(tmp_path),
    )

    assert run_info["run_id"] == "run-test-snap-01"
    assert len(run_info["compiled_model_hash"]) == 64
    assert len(run_info["artifact_hash"]) == 64
    assert (tmp_path / "run-test-snap-01" / "vehicle.sdf").exists()
    assert (tmp_path / "run-test-snap-01" / "manifest.json").exists()
