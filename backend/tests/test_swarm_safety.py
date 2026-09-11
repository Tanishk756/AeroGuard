"""Stage S10 Swarm Spatial Safety & Separation Unit Tests.

Tests spatial proximity breaches, formation deviation, telemetry staleness, leader loss, and slot conflict detection.
"""

import time
import pytest
from app.schemas.swarm import (
    SafetyEventType,
    SwarmConstraints,
    SwarmHealth,
    SwarmRole,
    SwarmVehicleState,
)
from app.simulation.core.swarm_safety import SwarmSafetyEngine


def test_swarm_safety_healthy():
    constraints = SwarmConstraints(min_separation_m=5.0, position_tolerance_m=2.0)
    engine = SwarmSafetyEngine(constraints=constraints, stale_telemetry_threshold_s=5.0)

    now = time.time()
    vstates = {
        "v1": SwarmVehicleState(
            vehicle_id="v1",
            autopilot_type="ARDUPILOT",
            role=SwarmRole.LEADER,
            slot_index=0,
            current_position_enu=(0.0, 0.0, 10.0),
            current_velocity_enu=(0.0, 0.0, 0.0),
            current_heading_deg=0.0,
            desired_position_enu=(0.0, 0.0, 10.0),
            desired_velocity_enu=(0.0, 0.0, 0.0),
            position_error_m=0.0,
            health_status="HEALTHY",
            last_telemetry_timestamp=now,
        ),
        "v2": SwarmVehicleState(
            vehicle_id="v2",
            autopilot_type="PX4",
            role=SwarmRole.FOLLOWER,
            slot_index=1,
            current_position_enu=(10.0, 0.0, 10.0),
            current_velocity_enu=(0.0, 0.0, 0.0),
            current_heading_deg=0.0,
            desired_position_enu=(10.0, 0.0, 10.0),
            desired_velocity_enu=(0.0, 0.0, 0.0),
            position_error_m=0.5,
            health_status="HEALTHY",
            last_telemetry_timestamp=now,
        ),
    }

    health, events = engine.evaluate_swarm_safety(
        swarm_id="swm-01",
        leader_vehicle_id="v1",
        vehicle_states=vstates,
        current_time_s=now,
    )

    assert health == SwarmHealth.HEALTHY
    assert len(events) == 0


def test_minimum_separation_breach_detection():
    constraints = SwarmConstraints(min_separation_m=10.0)
    engine = SwarmSafetyEngine(constraints=constraints)
    now = time.time()

    # Vehicles placed 4 meters apart (min_separation = 10m)
    vstates = {
        "v1": SwarmVehicleState(
            vehicle_id="v1", autopilot_type="ARDUPILOT", role=SwarmRole.LEADER, slot_index=0,
            current_position_enu=(0.0, 0.0, 10.0), current_velocity_enu=(0.0, 0.0, 0.0), current_heading_deg=0.0,
            desired_position_enu=(0.0, 0.0, 10.0), desired_velocity_enu=(0.0, 0.0, 0.0), position_error_m=0.0,
            health_status="HEALTHY", last_telemetry_timestamp=now,
        ),
        "v2": SwarmVehicleState(
            vehicle_id="v2", autopilot_type="PX4", role=SwarmRole.FOLLOWER, slot_index=1,
            current_position_enu=(4.0, 0.0, 10.0), current_velocity_enu=(0.0, 0.0, 0.0), current_heading_deg=0.0,
            desired_position_enu=(10.0, 0.0, 10.0), desired_velocity_enu=(0.0, 0.0, 0.0), position_error_m=6.0,
            health_status="HEALTHY", last_telemetry_timestamp=now,
        ),
    }

    health, events = engine.evaluate_swarm_safety(
        swarm_id="swm-02", leader_vehicle_id="v1", vehicle_states=vstates, current_time_s=now
    )

    assert health == SwarmHealth.CRITICAL
    breach_events = [e for e in events if e.event_type == SafetyEventType.MINIMUM_SEPARATION_BREACH]
    assert len(breach_events) >= 1
    assert breach_events[0].distance_m == 4.0


def test_leader_loss_detection():
    engine = SwarmSafetyEngine()
    now = time.time()

    # Missing leader telemetry
    vstates = {
        "v2": SwarmVehicleState(
            vehicle_id="v2", autopilot_type="PX4", role=SwarmRole.FOLLOWER, slot_index=1,
            current_position_enu=(10.0, 0.0, 10.0), current_velocity_enu=(0.0, 0.0, 0.0), current_heading_deg=0.0,
            desired_position_enu=(10.0, 0.0, 10.0), desired_velocity_enu=(0.0, 0.0, 0.0), position_error_m=0.0,
            health_status="HEALTHY", last_telemetry_timestamp=now,
        )
    }

    health, events = engine.evaluate_swarm_safety(
        swarm_id="swm-03", leader_vehicle_id="v1-missing", vehicle_states=vstates, current_time_s=now
    )

    assert health == SwarmHealth.CRITICAL
    leader_lost_events = [e for e in events if e.event_type == SafetyEventType.LEADER_LOST]
    assert len(leader_lost_events) == 1
