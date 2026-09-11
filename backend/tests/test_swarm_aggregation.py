"""Stage S11 Swarm State Aggregation Engine Unit Tests.

Tests centroid calculation, 3D bounding box/sphere extraction, pairwise separation statistics, and health breakdowns.
"""

import pytest
from app.schemas.simulation_platform import PositionVector, VelocityVector
from app.schemas.swarm_telemetry import SwarmVehicleTelemetry
from app.simulation.core.swarm_aggregation import SwarmAggregationEngine


def test_swarm_aggregation_metrics():
    # 2 vehicles placed at longitude 0.0 and 0.001 (approx 111.32m apart)
    t1 = SwarmVehicleTelemetry(
        vehicle_id="v1", swarm_id="s1", timestamp_utc="2026-09-11T00:00:00Z",
        position=PositionVector(latitude=0.0, longitude=0.0, altitude_relative=10.0),
        velocity=VelocityVector(vx=2.0, vy=0.0, vz=0.0),
        vehicle_health="HEALTHY",
    )
    t2 = SwarmVehicleTelemetry(
        vehicle_id="v2", swarm_id="s1", timestamp_utc="2026-09-11T00:00:00Z",
        position=PositionVector(latitude=0.0, longitude=0.001, altitude_relative=10.0),
        velocity=VelocityVector(vx=4.0, vy=0.0, vz=0.0),
        vehicle_health="DEGRADED",
    )

    telemetry_map = {"v1": t1, "v2": t2}
    snapshot = SwarmAggregationEngine.compute_swarm_snapshot(
        swarm_id="s1", snapshot_sequence=1, telemetry_map=telemetry_map
    )

    assert len(snapshot.active_vehicle_ids) == 2
    assert snapshot.average_velocity_enu[0] == 3.0
    assert snapshot.vehicle_health_summary.healthy_count == 1
    assert snapshot.vehicle_health_summary.degraded_count == 1
    assert abs(snapshot.pairwise_separation_stats.min_distance_m - 111.32) < 1.0
