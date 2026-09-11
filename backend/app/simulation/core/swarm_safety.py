"""Stage S10 Swarm Spatial Safety & Separation Engine.

Implements real-time monitoring of spatial separation, formation deviation, telemetry freshness,
slot conflicts, and leader loss across multi-vehicle swarms.
"""

import math
import time
from typing import Dict, List, Optional, Tuple
from app.schemas.swarm import (
    SafetyEvent,
    SafetyEventType,
    SwarmConstraints,
    SwarmHealth,
    SwarmRole,
    SwarmVehicleState,
)


class SwarmSafetyEngine:
    """Safety and separation monitoring engine for multi-vehicle swarms."""

    def __init__(
        self,
        constraints: Optional[SwarmConstraints] = None,
        stale_telemetry_threshold_s: float = 5.0,
    ):
        self.constraints = constraints or SwarmConstraints()
        self.stale_telemetry_threshold_s = stale_telemetry_threshold_s

    def evaluate_swarm_safety(
        self,
        swarm_id: str,
        leader_vehicle_id: Optional[str],
        vehicle_states: Dict[str, SwarmVehicleState],
        current_time_s: Optional[float] = None,
    ) -> Tuple[SwarmHealth, List[SafetyEvent]]:
        """Evaluate spatial safety and telemetry status for a swarm.

        Returns:
            Tuple of (Aggregated SwarmHealth, List of SafetyEvent instances).
        """
        now = current_time_s if current_time_s is not None else time.time()
        from datetime import datetime, timezone
        event_dt = datetime.fromtimestamp(now, tz=timezone.utc)
        events: List[SafetyEvent] = []

        if not vehicle_states:
            return (SwarmHealth.DISCONNECTED, [
                SafetyEvent(
                    event_type=SafetyEventType.VEHICLE_DISCONNECTED,
                    severity="CRITICAL",
                    vehicle_id="SWARM_GLOBAL",
                    timestamp=event_dt,
                    message=f"Swarm {swarm_id} contains no registered active vehicle states.",
                )
            ])

        # 1. Leader Loss / Check
        leader_present = False
        if leader_vehicle_id and leader_vehicle_id in vehicle_states:
            leader_state = vehicle_states[leader_vehicle_id]
            if (now - leader_state.last_telemetry_timestamp) <= self.stale_telemetry_threshold_s:
                leader_present = True
            else:
                events.append(
                    SafetyEvent(
                        event_type=SafetyEventType.LEADER_LOST,
                        severity="CRITICAL",
                        vehicle_id=leader_vehicle_id,
                        timestamp=event_dt,
                        message=f"Leader vehicle {leader_vehicle_id} telemetry is stale ({now - leader_state.last_telemetry_timestamp:.1f}s).",
                    )
                )
        elif leader_vehicle_id:
            events.append(
                SafetyEvent(
                    event_type=SafetyEventType.LEADER_LOST,
                    severity="CRITICAL",
                    vehicle_id=leader_vehicle_id,
                    timestamp=event_dt,
                    message=f"Designated leader vehicle {leader_vehicle_id} not found in active vehicle states.",
                )
            )

        # 2. Slot Conflict Check
        slot_map: Dict[int, List[str]] = {}
        for vid, vstate in vehicle_states.items():
            slot_map.setdefault(vstate.slot_index, []).append(vid)

        for slot_idx, vids in slot_map.items():
            if len(vids) > 1:
                events.append(
                    SafetyEvent(
                        event_type=SafetyEventType.SLOT_CONFLICT,
                        severity="WARNING",
                        vehicle_id=vids[0],
                        target_vehicle_id=vids[1],
                        timestamp=event_dt,
                        message=f"Slot conflict: vehicles {vids} are both assigned slot {slot_idx}.",
                    )
                )

        # 3. Telemetry Freshness & Formation Deviation per vehicle
        disconnected_count = 0
        min_sep = self.constraints.min_separation_m
        pos_tol = self.constraints.position_tolerance_m

        for vid, vstate in vehicle_states.items():
            time_diff = now - vstate.last_telemetry_timestamp
            if time_diff > self.stale_telemetry_threshold_s:
                disconnected_count += 1
                events.append(
                    SafetyEvent(
                        event_type=SafetyEventType.VEHICLE_DISCONNECTED,
                        severity="WARNING" if vstate.role != SwarmRole.LEADER else "CRITICAL",
                        vehicle_id=vid,
                        timestamp=event_dt,
                        message=f"Vehicle {vid} disconnected. Stale telemetry ({time_diff:.1f}s).",
                    )
                )

            # Formation deviation check for followers
            if vstate.role == SwarmRole.FOLLOWER and vstate.position_error_m > (2.0 * pos_tol):
                events.append(
                    SafetyEvent(
                        event_type=SafetyEventType.FORMATION_DEVIATION,
                        severity="WARNING",
                        vehicle_id=vid,
                        distance_m=vstate.position_error_m,
                        threshold_m=2.0 * pos_tol,
                        timestamp=event_dt,
                        message=f"Vehicle {vid} deviated from formation slot by {vstate.position_error_m:.2f}m (threshold: {2.0 * pos_tol:.2f}m).",
                    )
                )

        # 4. Pairwise Spatial Separation Check
        vlist = list(vehicle_states.values())
        n = len(vlist)
        min_sep_breach = False

        for i in range(n):
            for j in range(i + 1, n):
                v1 = vlist[i]
                v2 = vlist[j]

                dx = v1.current_position_enu[0] - v2.current_position_enu[0]
                dy = v1.current_position_enu[1] - v2.current_position_enu[1]
                dz = v1.current_position_enu[2] - v2.current_position_enu[2]

                dist = math.sqrt(dx * dx + dy * dy + dz * dz)

                if dist < min_sep:
                    min_sep_breach = True
                    events.append(
                        SafetyEvent(
                            event_type=SafetyEventType.MINIMUM_SEPARATION_BREACH,
                            severity="CRITICAL",
                            vehicle_id=v1.vehicle_id,
                            target_vehicle_id=v2.vehicle_id,
                            distance_m=dist,
                            threshold_m=min_sep,
                            timestamp=event_dt,
                            message=f"Minimum separation breach between {v1.vehicle_id} and {v2.vehicle_id}: {dist:.2f}m < {min_sep:.2f}m.",
                        )
                    )

        # 5. Determine Aggregated Swarm Health
        total_vehicles = len(vehicle_states)
        if disconnected_count >= max(1, total_vehicles // 2):
            health = SwarmHealth.DISCONNECTED
        elif min_sep_breach or (leader_vehicle_id and not leader_present):
            health = SwarmHealth.CRITICAL
        elif any(e.severity == "WARNING" for e in events):
            health = SwarmHealth.DEGRADED
        else:
            health = SwarmHealth.HEALTHY

        return (health, events)
