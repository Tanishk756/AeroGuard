"""Stage S11 Swarm Safety-Action Engine Unit Tests.

Tests rule-based safety policy evaluations and deterministic decision generation.
"""

import time
import pytest
from app.schemas.simulation_platform import PositionVector
from app.schemas.swarm_safety import SafetyActionType, SwarmSafetyPolicyCreate
from app.schemas.swarm_telemetry import SwarmVehicleTelemetry
from app.simulation.core.swarm_aggregation import SwarmAggregationEngine
from app.simulation.core.swarm_safety_action_engine import SwarmSafetyActionEngine


def test_safety_action_critical_separation_trigger():
    policy = SwarmSafetyPolicyCreate(
        name="Strict Policy",
        min_separation_m=10.0,
        warning_separation_m=15.0,
        critical_separation_m=5.0,
        cooldown_s=0.0,
    )
    engine = SwarmSafetyActionEngine(policy=policy)
    now = time.time()

    # Vehicles placed 3 meters apart (critical threshold = 5m)
    t1 = SwarmVehicleTelemetry(
        vehicle_id="v1", swarm_id="s1", timestamp_utc="2026-09-11T00:00:00Z",
        position=PositionVector(latitude=0.0, longitude=0.0, altitude_relative=10.0),
    )
    t2 = SwarmVehicleTelemetry(
        vehicle_id="v2", swarm_id="s1", timestamp_utc="2026-09-11T00:00:00Z",
        position=PositionVector(latitude=0.0, longitude=0.000027, altitude_relative=10.0), # approx 3m
    )

    snapshot = SwarmAggregationEngine.compute_swarm_snapshot(
        swarm_id="s1", snapshot_sequence=1, telemetry_map={"v1": t1, "v2": t2}
    )

    decisions = engine.evaluate_safety_policy(snapshot=snapshot, current_time_s=now)

    assert len(decisions) >= 1
    crit_dec = [d for d in decisions if d.condition == "CRITICAL_SEPARATION_BREACH"]
    assert len(crit_dec) == 1
    assert crit_dec[0].selected_action == SafetyActionType.INCREASE_SEPARATION
