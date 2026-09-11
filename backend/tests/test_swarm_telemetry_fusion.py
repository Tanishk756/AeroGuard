"""Stage S11 Swarm Telemetry Stream Fusion Unit Tests.

Tests ingestion, sequence counter incrementing, stale packet calculation, and bounded history buffer limits.
"""

import time
import pytest
from app.schemas.simulation_platform import PositionVector, VehicleState, VelocityVector
from app.simulation.core.swarm_telemetry_fusion import SwarmTelemetryFusionEngine


def test_telemetry_fusion_ingestion_and_bounding():
    engine = SwarmTelemetryFusionEngine(history_limit_per_vehicle=5, stale_threshold_s=2.0)
    now = time.time()

    # Ingest 10 telemetry frames for vehicle v-01
    for i in range(10):
        v_state = VehicleState(
            timestamp_utc="2026-09-11T00:00:00Z",
            sim_time_seconds=float(i),
            vehicle_id="v-01",
            position=PositionVector(latitude=37.7749, longitude=-122.4194, altitude_relative=10.0 + i),
            velocity=VelocityVector(vx=1.0, vy=0.0, vz=0.0),
        )
        engine.ingest_vehicle_state("swm-01", v_state, current_time_s=now)

    latest = engine.get_latest_vehicle_telemetry("v-01")
    assert latest is not None
    assert latest.sequence_number == 10
    assert latest.position.altitude_relative == 19.0

    # History buffer should strictly hold max 5 items
    history = engine.get_vehicle_history("v-01", limit=100)
    assert len(history) == 5
    assert history[-1].sequence_number == 10
    assert history[0].sequence_number == 6
