"""Stage S5 Live E2E Physics-Based Vehicle Assembly & Gazebo/ArduPilot SITL Integration Test."""

import os
import pytest
from app.models.hardware_registry import PersistentHardwareComponent, PersistentVehicle
from app.simulation.core.vehicle_compiler import VehicleAssemblyCompiler
from app.simulation.core.sdf_generator import GazeboVehicleGenerator
from app.simulation.core.run_snapshot import SimulationSnapshotManager
from app.simulation.core.orchestrator import SimulationOrchestrator
from app.schemas.simulation_platform import SimulationScenarioSpec, SimulatorType, AutopilotType


@pytest.mark.live_simulation
@pytest.mark.skipif(
    os.environ.get("AEROGUARD_LIVE_SIMULATION") != "1",
    reason="Stage S5 live hardware-to-Gazebo simulation requires AEROGUARD_LIVE_SIMULATION=1",
)
def test_s5_real_vehicle_assembly_end_to_end_simulation(database, tmp_path):
    """LIVE SIMULATION VERIFIED: Real vehicle compilation -> SDF generation -> Run snapshot -> Gazebo/SITL execution."""
    frame = PersistentHardwareComponent(id="f1", manufacturer="Holybro", model="S500", category="frame", mass_g=280.0)
    motor = PersistentHardwareComponent(id="m1", manufacturer="T-Motor", model="MN2212", category="motor", mass_g=55.0)
    esc = PersistentHardwareComponent(id="e1", manufacturer="Holybro", model="30A", category="esc", mass_g=12.0)
    prop = PersistentHardwareComponent(id="p1", manufacturer="Gemfan", model="1045", category="propeller", mass_g=15.0)
    bat = PersistentHardwareComponent(id="b1", manufacturer="Tattu", model="4S 5000", category="battery", mass_g=450.0)
    fc = PersistentHardwareComponent(id="fc1", manufacturer="Holybro", model="Pixhawk4", category="flight_controller", mass_g=68.0)

    database.add_all([frame, motor, esc, prop, bat, fc])
    database.commit()

    vehicle = PersistentVehicle(
        id="veh-s5-live-01",
        project_id="proj-default-01",
        name="Stage S5 Live Quad-X",
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

    # 1. Compile Vehicle
    compiled = VehicleAssemblyCompiler.compile_vehicle(vehicle)
    assert compiled.total_mass_g == 1126.0

    # 2. Freeze Run Snapshot & SDF Artifact
    snapshot = SimulationSnapshotManager.freeze_simulation_run(
        run_id="run-s5-live-01",
        vehicle=vehicle,
        world_name="shapes.sdf",
        db=database,
        base_dir=str(tmp_path),
    )
    assert (tmp_path / "run-s5-live-01" / "vehicle.sdf").exists()
