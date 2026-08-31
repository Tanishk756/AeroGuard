"""Stage S5 Simulation Run Snapshot & Artifact Isolation Engine.

Freezes vehicle configuration, generated SDF, world file, and manifest under `.aeroguard/simulations/<run-id>/`
and records persistent snapshot in database.
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional
from sqlalchemy.orm import Session

from app.models.snapshot import PersistentSimulationRunSnapshot
from app.models.hardware_registry import PersistentVehicle
from app.simulation.core.vehicle_compiler import VehicleAssemblyCompiler
from app.simulation.core.sdf_generator import GazeboVehicleGenerator
from app.core.telemetry import SIMULATION_SNAPSHOT_TOTAL


class SimulationSnapshotManager:
    """Manages run-specific artifact isolation directories and immutable database snapshot freezing."""

    @classmethod
    def freeze_simulation_run(
        cls,
        run_id: str,
        vehicle: PersistentVehicle,
        world_name: str,
        db: Session,
        world_sdf_content: Optional[str] = None,
        scenario_id: Optional[str] = None,
        base_dir: str = ".aeroguard/simulations",
    ) -> Dict[str, Any]:
        SIMULATION_SNAPSHOT_TOTAL.inc()

        # 1. Compile Vehicle Model
        compiled_model = VehicleAssemblyCompiler.compile_vehicle(vehicle)

        # 2. Generate Gazebo SDF Artifact
        sdf_xml, sdf_hash = GazeboVehicleGenerator.generate_sdf(compiled_model)

        # 3. Create Isolated Run Directory
        run_dir = Path(base_dir) / run_id
        run_dir.mkdir(parents=True, exist_ok=True)

        vehicle_sdf_path = run_dir / "vehicle.sdf"
        world_sdf_path = run_dir / "world.sdf"
        config_json_path = run_dir / "configuration.json"
        manifest_json_path = run_dir / "manifest.json"

        # Write artifacts securely
        vehicle_sdf_path.write_text(sdf_xml, encoding="utf-8")
        world_content = world_sdf_content or f"<!-- World: {world_name} -->"
        world_sdf_path.write_text(world_content, encoding="utf-8")
        config_json_path.write_text(compiled_model.model_dump_json(indent=2), encoding="utf-8")

        manifest = {
            "run_id": run_id,
            "vehicle_id": vehicle.id,
            "scenario_id": scenario_id,
            "compiled_model_hash": compiled_model.compiled_model_hash,
            "artifact_hash": sdf_hash,
            "world_name": world_name,
            "compiler_version": "v1.0.0-s6",
        }
        manifest_json_path.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

        # 4. Freeze Persistent Database Snapshot Record
        snapshot = PersistentSimulationRunSnapshot(
            run_id=run_id,
            vehicle_id=vehicle.id,
            compiled_model_hash=compiled_model.compiled_model_hash,
            artifact_hash=sdf_hash,
            provenance_json={k: v.model_dump() for k, v in compiled_model.provenance.items()},
            compiled_metadata_json=compiled_model.model_dump(),
        )

        db.add(snapshot)
        db.commit()
        db.refresh(snapshot)

        return {
            "snapshot_id": snapshot.id,
            "run_id": run_id,
            "compiled_model_hash": compiled_model.compiled_model_hash,
            "artifact_hash": sdf_hash,
            "run_dir": str(run_dir.resolve()),
            "sdf_path": str(vehicle_sdf_path.resolve()),
        }
