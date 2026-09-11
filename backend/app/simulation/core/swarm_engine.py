"""Stage S10 Multi-Vehicle Swarm & Formation Control Engine.

Core engine managing swarm configurations, membership, formation geometries, state tracking,
control intent generation, safety monitoring, and multi-autopilot orchestration.
"""

import time
from typing import Dict, List, Optional, Tuple
from app.schemas.simulation_platform import VehicleState
from app.schemas.swarm import (
    FormationConfiguration,
    FormationSlot,
    FormationType,
    SafetyEvent,
    SwarmConfiguration,
    SwarmConstraints,
    SwarmHealth,
    SwarmMemberConfig,
    SwarmRole,
    SwarmState,
    SwarmVehicleState,
    VehicleDesiredState,
)
from app.simulation.core.formation_controller import FormationController
from app.simulation.core.formation_geometry import FormationGeometry
from app.simulation.core.swarm_safety import SwarmSafetyEngine


class SwarmEngine:
    """Multi-vehicle swarm state and formation control engine."""

    def __init__(self, swarm_config: SwarmConfiguration):
        self.config = swarm_config
        self.controller = FormationController(gain_p=1.0, constraints=swarm_config.constraints)
        self.safety_engine = SwarmSafetyEngine(constraints=swarm_config.constraints)

        # Active telemetry state cache per vehicle: vehicle_id -> VehicleState (from S9)
        self._raw_telemetry: Dict[str, VehicleState] = {}
        # Last received timestamp per vehicle
        self._telemetry_timestamps: Dict[str, float] = {}

        # Re-generate formation slots upon creation
        self.update_formation(
            formation_type=self.config.formation.formation_type,
            spacing_m=self.config.formation.spacing_m,
            altitude_offset_m=self.config.formation.altitude_offset_m,
        )

    def register_member(
        self,
        vehicle_id: str,
        role: SwarmRole = SwarmRole.FOLLOWER,
        autopilot_type: str = "ARDUPILOT",
        initial_position: Tuple[float, float, float] = (0.0, 0.0, 0.0),
        initial_heading_deg: float = 0.0,
    ) -> SwarmMemberConfig:
        """Register a vehicle member into the swarm."""
        existing = next((m for m in self.config.members if m.vehicle_id == vehicle_id), None)
        if existing:
            existing.role = role
            existing.autopilot_type = autopilot_type
            return existing

        slot_idx = len(self.config.members)
        if role == SwarmRole.LEADER or (slot_idx == 0 and not self.config.leader_vehicle_id):
            role = SwarmRole.LEADER
            self.config.leader_vehicle_id = vehicle_id

        member = SwarmMemberConfig(
            vehicle_id=vehicle_id,
            role=role,
            slot_index=slot_idx,
            autopilot_type=autopilot_type,
            initial_position=initial_position,
            initial_heading_deg=initial_heading_deg,
        )
        self.config.members.append(member)

        # Refresh slots
        self.update_formation(
            formation_type=self.config.formation.formation_type,
            spacing_m=self.config.formation.spacing_m,
            altitude_offset_m=self.config.formation.altitude_offset_m,
        )
        return member

    def remove_member(self, vehicle_id: str) -> bool:
        """Remove a vehicle member from the swarm."""
        orig_len = len(self.config.members)
        self.config.members = [m for m in self.config.members if m.vehicle_id != vehicle_id]
        if vehicle_id in self._raw_telemetry:
            del self._raw_telemetry[vehicle_id]
        if vehicle_id in self._telemetry_timestamps:
            del self._telemetry_timestamps[vehicle_id]

        if self.config.leader_vehicle_id == vehicle_id:
            self.config.leader_vehicle_id = self.config.members[0].vehicle_id if self.config.members else None
            if self.config.members:
                self.config.members[0].role = SwarmRole.LEADER

        # Re-index slot indices
        for i, m in enumerate(self.config.members):
            m.slot_index = i

        self.update_formation(
            formation_type=self.config.formation.formation_type,
            spacing_m=self.config.formation.spacing_m,
            altitude_offset_m=self.config.formation.altitude_offset_m,
        )
        return len(self.config.members) < orig_len

    def set_leader(self, vehicle_id: str) -> bool:
        """Designate a specific vehicle as the swarm leader."""
        member = next((m for m in self.config.members if m.vehicle_id == vehicle_id), None)
        if not member:
            return False

        for m in self.config.members:
            m.role = SwarmRole.FOLLOWER

        member.role = SwarmRole.LEADER
        self.config.leader_vehicle_id = vehicle_id

        # Move new leader to slot index 0 if needed
        self.config.members.remove(member)
        self.config.members.insert(0, member)
        for i, m in enumerate(self.config.members):
            m.slot_index = i

        self.update_formation(
            formation_type=self.config.formation.formation_type,
            spacing_m=self.config.formation.spacing_m,
            altitude_offset_m=self.config.formation.altitude_offset_m,
        )
        return True

    def update_formation(
        self,
        formation_type: FormationType,
        spacing_m: float = 10.0,
        altitude_offset_m: float = 0.0,
    ) -> FormationConfiguration:
        """Update formation type, spacing, and altitude offset."""
        self.config.formation.formation_type = formation_type
        self.config.formation.spacing_m = spacing_m
        self.config.formation.altitude_offset_m = altitude_offset_m

        generated_slots = FormationGeometry.generate_slots(
            formation_type=formation_type,
            num_vehicles=len(self.config.members),
            spacing_m=spacing_m,
            altitude_offset_m=altitude_offset_m,
        )
        self.config.formation.slots = generated_slots
        return self.config.formation

    def update_vehicle_telemetry(self, vehicle_state: VehicleState, current_time_s: Optional[float] = None) -> None:
        """Update normalized telemetry for a vehicle member."""
        vid = vehicle_state.vehicle_id
        self._raw_telemetry[vid] = vehicle_state
        self._telemetry_timestamps[vid] = current_time_s if current_time_s is not None else time.time()

    def step(self, current_time_s: Optional[float] = None) -> SwarmState:
        """Execute deterministic state update step for the swarm.

        1. Extract Leader current state (or default reference).
        2. Calculate target slot position and velocity for each follower.
        3. Run FormationController for followers.
        4. Run SwarmSafetyEngine for spatial safety evaluation.
        5. Return updated SwarmState.
        """
        now = current_time_s if current_time_s is not None else time.time()

        # Leader state extraction
        leader_id = self.config.leader_vehicle_id
        leader_pos_enu = (0.0, 0.0, 10.0)
        leader_vel_enu = (0.0, 0.0, 0.0)
        leader_heading = 0.0

        if leader_id and leader_id in self._raw_telemetry:
            l_state = self._raw_telemetry[leader_id]
            # Convert lat/lon or relative altitude into ENU relative reference
            # For local simulation, velocity vector (vx, vy, vz) is directly ENU
            leader_pos_enu = (
                l_state.position.longitude * 111320.0,  # approximate local meter projection if needed or raw ENU
                l_state.position.latitude * 111320.0,
                l_state.position.altitude_relative,
            )
            leader_vel_enu = (l_state.velocity.vx, l_state.velocity.vy, l_state.velocity.vz)
            leader_heading = l_state.attitude.yaw_deg

        swarm_vehicle_states: Dict[str, SwarmVehicleState] = {}
        desired_states: Dict[str, VehicleDesiredState] = {}

        slots = self.config.formation.slots

        for member in self.config.members:
            vid = member.vehicle_id
            slot = slots.get(member.slot_index, FormationSlot(slot_index=member.slot_index))

            # Current vehicle state telemetry
            if vid in self._raw_telemetry:
                v_raw = self._raw_telemetry[vid]
                c_pos = (
                    v_raw.position.longitude * 111320.0,
                    v_raw.position.latitude * 111320.0,
                    v_raw.position.altitude_relative,
                )
                c_vel = (v_raw.velocity.vx, v_raw.velocity.vy, v_raw.velocity.vz)
                c_head = v_raw.attitude.yaw_deg
                last_ts = self._telemetry_timestamps.get(vid, now)
            else:
                c_pos = member.initial_position
                c_vel = (0.0, 0.0, 0.0)
                c_head = member.initial_heading_deg
                last_ts = now - 10.0  # Treat missing initial telemetry as stale

            # Desired state calculation
            if member.role == SwarmRole.LEADER:
                d_pos = c_pos
                d_vel = leader_vel_enu
                desired_state = VehicleDesiredState(
                    vehicle_id=vid,
                    target_position_enu=d_pos,
                    target_velocity_enu=d_vel,
                    target_heading_deg=leader_heading,
                    position_error_m=0.0,
                )
            else:
                d_pos = FormationGeometry.calculate_desired_slot_position(
                    leader_position_enu=leader_pos_enu,
                    leader_heading_deg=leader_heading,
                    slot=slot,
                )
                desired_state = self.controller.compute_follower_target(
                    vehicle_id=vid,
                    current_position_enu=c_pos,
                    desired_position_enu=d_pos,
                    leader_velocity_enu=leader_vel_enu,
                    leader_heading_deg=leader_heading,
                )

            desired_states[vid] = desired_state

            # Vehicle status
            v_health = "HEALTHY"
            if desired_state.position_error_m > (2.0 * self.config.constraints.position_tolerance_m):
                v_health = "DEGRADED"
            if (now - last_ts) > self.safety_engine.stale_telemetry_threshold_s:
                v_health = "DISCONNECTED"

            swarm_vehicle_states[vid] = SwarmVehicleState(
                vehicle_id=vid,
                autopilot_type=member.autopilot_type,
                role=member.role,
                slot_index=member.slot_index,
                current_position_enu=c_pos,
                current_velocity_enu=c_vel,
                current_heading_deg=c_head,
                desired_position_enu=desired_state.target_position_enu,
                desired_velocity_enu=desired_state.target_velocity_enu,
                position_error_m=desired_state.position_error_m,
                health_status=v_health,
                last_telemetry_timestamp=last_ts,
            )

        # Safety evaluation
        aggregated_health, safety_events = self.safety_engine.evaluate_swarm_safety(
            swarm_id=self.config.swarm_id,
            leader_vehicle_id=self.config.leader_vehicle_id,
            vehicle_states=swarm_vehicle_states,
            current_time_s=now,
        )

        return SwarmState(
            swarm_id=self.config.swarm_id,
            leader_vehicle_id=self.config.leader_vehicle_id,
            formation_type=self.config.formation.formation_type,
            health=aggregated_health,
            vehicle_states=swarm_vehicle_states,
            desired_states=desired_states,
            safety_events=safety_events,
        )
