"""Stage S12 Bounded & Deterministic Simulation Recorder.

Captures, stores, and serializes versioned SimulationSnapshots during live execution.
Computes deterministic cryptographic hashes for auditability and verification.
"""

import hashlib
import json
from typing import Dict, List, Optional
from pydantic import BaseModel

from app.schemas.simulation_snapshot import SimulationSnapshot, SimulationRecordingMetadata


class SimulationRecorder:
    """Bounded, high-performance in-memory recorder for simulation snapshots."""

    def __init__(
        self,
        recording_id: str,
        scenario_id: str,
        dt_seconds: float = 0.1,
        max_snapshots: int = 36000,  # Default 1 hour at 10Hz
    ):
        self.recording_id: str = recording_id
        self.scenario_id: str = scenario_id
        self.dt_seconds: float = dt_seconds
        self.max_snapshots: int = max_snapshots

        self.snapshots: List[SimulationSnapshot] = []
        self.event_index: Dict[str, List[int]] = {
            "safety_events": [],
            "safety_decisions": [],
            "mission_events": [],
        }

    def record_snapshot(self, snapshot: SimulationSnapshot) -> SimulationSnapshot:
        """Record a single timestamped snapshot.

        Enforces bounds and calculates deterministic snapshot hash if not present.
        """
        if len(self.snapshots) >= self.max_snapshots:
            self.snapshots.pop(0)

        # Compute hash for snapshot determinism
        snapshot_dict = snapshot.model_dump(exclude={"snapshot_hash"})
        serialized = json.dumps(snapshot_dict, sort_keys=True, default=str)
        snapshot.snapshot_hash = hashlib.sha256(serialized.encode("utf-8")).hexdigest()

        self.snapshots.append(snapshot)
        tick_idx = len(self.snapshots) - 1

        # Index events for rapid replay jumping
        if snapshot.safety_events:
            self.event_index["safety_events"].append(tick_idx)
        if snapshot.safety_decisions:
            self.event_index["safety_decisions"].append(tick_idx)
        if snapshot.mission_progress:
            self.event_index["mission_events"].append(tick_idx)

        return snapshot

    def get_snapshot_by_tick(self, tick_count: int) -> Optional[SimulationSnapshot]:
        """Retrieve snapshot matching exact tick count."""
        for snap in self.snapshots:
            if snap.tick_count == tick_count:
                return snap
        return None

    def get_snapshot_by_time(self, sim_time_s: float) -> Optional[SimulationSnapshot]:
        """Retrieve snapshot closest to given simulation time."""
        if not self.snapshots:
            return None
        target_tick = int(round(sim_time_s / self.dt_seconds))
        return self.get_snapshot_by_tick(target_tick) or min(
            self.snapshots, key=lambda s: abs(s.sim_time_seconds - sim_time_s)
        )

    def get_metadata(self) -> SimulationRecordingMetadata:
        """Generate metadata summary for the recorded session."""
        total_ticks = len(self.snapshots)
        duration_s = round(total_ticks * self.dt_seconds, 6) if total_ticks > 0 else 0.0
        vehicle_count = len(self.snapshots[-1].vehicles_state) if self.snapshots else 0
        swarm_id = self.snapshots[-1].swarm_state.swarm_id if (self.snapshots and self.snapshots[-1].swarm_state) else None

        # Compute recording-level SHA256 hash
        hash_input = "".join(s.snapshot_hash or "" for s in self.snapshots)
        rec_hash = hashlib.sha256(hash_input.encode("utf-8")).hexdigest()

        return SimulationRecordingMetadata(
            recording_id=self.recording_id,
            scenario_id=self.scenario_id,
            swarm_id=swarm_id,
            vehicle_count=vehicle_count,
            total_ticks=total_ticks,
            total_duration_s=duration_s,
            dt_seconds=self.dt_seconds,
            recording_hash=rec_hash,
            sample_count=total_ticks,
        )

    def export_json(self) -> str:
        """Export full recording as JSON string."""
        data = {
            "metadata": self.get_metadata().model_dump(),
            "snapshots": [s.model_dump() for s in self.snapshots],
            "event_index": self.event_index,
        }
        return json.dumps(data, indent=2, default=str)

    def clear(self) -> None:
        """Clear recorded snapshots."""
        self.snapshots.clear()
        for k in self.event_index:
            self.event_index[k].clear()
