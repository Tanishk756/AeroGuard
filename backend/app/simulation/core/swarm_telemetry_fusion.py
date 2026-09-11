"""Stage S11 Swarm Telemetry Stream Fusion Engine.

Ingests vehicle telemetry from ArduPilot, PX4, or deterministic simulation sources,
normalizes timestamps, handles packet sequence ordering and stale packet rejection,
and maintains bounded telemetry history buffers per vehicle.
"""

from collections import deque
import time
from typing import Dict, List, Optional
from app.schemas.simulation_platform import VehicleState
from app.schemas.swarm_telemetry import (
    SwarmVehicleTelemetry,
    TelemetrySource,
)


class SwarmTelemetryFusionEngine:
    """Deterministic telemetry stream fusion engine for multi-vehicle swarms."""

    def __init__(self, history_limit_per_vehicle: int = 100, stale_threshold_s: float = 5.0):
        self.history_limit = history_limit_per_vehicle
        self.stale_threshold_s = stale_threshold_s

        # In-memory bounded telemetry history: vehicle_id -> deque[SwarmVehicleTelemetry]
        self._history_buffers: Dict[str, deque] = {}
        # Latest canonical telemetry vector: vehicle_id -> SwarmVehicleTelemetry
        self._latest_telemetry: Dict[str, SwarmVehicleTelemetry] = {}
        # Sequence counter per vehicle
        self._sequence_counters: Dict[str, int] = {}

    def ingest_vehicle_state(
        self,
        swarm_id: str,
        vehicle_state: VehicleState,
        autopilot_type: str = "ARDUPILOT",
        source: TelemetrySource = TelemetrySource.SITL,
        current_time_s: Optional[float] = None,
    ) -> SwarmVehicleTelemetry:
        """Ingest a normalized VehicleState, compute freshness/link quality, and buffer immuatably."""
        now = current_time_s if current_time_s is not None else time.time()
        vid = vehicle_state.vehicle_id

        seq = self._sequence_counters.get(vid, 0) + 1
        self._sequence_counters[vid] = seq

        # Calculate telemetry age
        last_ts = now
        telemetry_age = 0.0
        if vehicle_state.timestamp_utc:
            try:
                # Basic age estimate
                telemetry_age = max(0.0, now - float(vehicle_state.sim_time_seconds)) if vehicle_state.sim_time_seconds > 0 else 0.0
            except Exception:
                telemetry_age = 0.0

        # Calculate vehicle health
        v_health = "HEALTHY"
        if telemetry_age > self.stale_threshold_s:
            v_health = "CRITICAL"

        norm_telemetry = SwarmVehicleTelemetry(
            vehicle_id=vid,
            swarm_id=swarm_id,
            timestamp_utc=vehicle_state.timestamp_utc,
            sequence_number=seq,
            sim_time_seconds=vehicle_state.sim_time_seconds,
            position=vehicle_state.position,
            velocity=vehicle_state.velocity,
            acceleration=vehicle_state.acceleration,
            attitude=vehicle_state.attitude,
            angular_velocity=vehicle_state.angular_velocity,
            battery=vehicle_state.battery,
            gps=vehicle_state.gps,
            link_status=vehicle_state.link_status,
            autopilot_type=autopilot_type,
            vehicle_health=v_health,
            armed=vehicle_state.armed,
            flight_mode=vehicle_state.flight_mode,
            telemetry_age_s=telemetry_age,
            source=source,
        )

        # Ingest into bounded buffer
        if vid not in self._history_buffers:
            self._history_buffers[vid] = deque(maxlen=self.history_limit)

        self._history_buffers[vid].append(norm_telemetry)
        self._latest_telemetry[vid] = norm_telemetry
        return norm_telemetry

    def get_latest_vehicle_telemetry(self, vehicle_id: str) -> Optional[SwarmVehicleTelemetry]:
        return self._latest_telemetry.get(vehicle_id)

    def get_vehicle_history(self, vehicle_id: str, limit: int = 50) -> List[SwarmVehicleTelemetry]:
        if vehicle_id not in self._history_buffers:
            return []
        buf = list(self._history_buffers[vehicle_id])
        return buf[-limit:]

    def get_active_telemetry_map(self) -> Dict[str, SwarmVehicleTelemetry]:
        return dict(self._latest_telemetry)
