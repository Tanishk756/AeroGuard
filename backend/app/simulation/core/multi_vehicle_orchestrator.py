"""Stage S12 Multi-Vehicle Simulation Orchestrator.

Central deterministic orchestrator connecting Scenario, Physics, Digital Twin Sensors,
Autopilot Abstraction (S9), Mission Execution (S7), Swarm Engine (S10),
Telemetry Fusion & Safety Engine (S11), and Snapshot Recording (S12).
"""

import math
import uuid
from typing import Any, Dict, List, Optional

from app.schemas.simulation_platform import VehicleState
from app.schemas.simulation_snapshot import SimulationSnapshot
from app.schemas.swarm import (
    FormationType,
    SafetyEvent,
    SwarmConfiguration,
    SwarmRole,
    SwarmState,
)
from app.schemas.swarm_safety import SwarmSafetyPolicyCreate
from app.schemas.swarm_telemetry import SwarmTelemetrySnapshot
from app.simulation.core.deterministic_sensor_sim import DeterministicSensorConfig, DeterministicSensorSim
from app.simulation.core.simulation_clock import ClockMode, SimulationClock
from app.simulation.core.simulation_recorder import SimulationRecorder
from app.simulation.core.swarm_engine import SwarmEngine
from app.simulation.core.swarm_safety_action_engine import SwarmSafetyActionEngine
from app.simulation.core.swarm_telemetry_fusion import SwarmTelemetryFusionEngine


class VehicleSimulationInstance:
    """Internal simulation record for a single vehicle in the orchestrator."""

    def __init__(
        self,
        vehicle_id: str,
        autopilot_type: str = "ARDUPILOT",
        initial_pos: tuple = (0.0, 0.0, 0.0),
        initial_yaw: float = 0.0,
    ):
        self.vehicle_id: str = vehicle_id
        self.autopilot_type: str = autopilot_type
        # State vectors
        self.x: float = initial_pos[0]
        self.y: float = initial_pos[1]
        self.z: float = initial_pos[2]
        self.vx: float = 0.0
        self.vy: float = 0.0
        self.vz: float = 0.0
        self.roll: float = 0.0
        self.pitch: float = 0.0
        self.yaw: float = initial_yaw
        # Mission / desired target state
        self.target_x: float = initial_pos[0]
        self.target_y: float = initial_pos[1]
        self.target_z: float = initial_pos[2]
        self.mission_waypoints: List[Dict[str, float]] = []
        self.current_waypoint_idx: int = 0

    def update_kinematics(self, dt: float, max_speed: float = 12.0) -> None:
        """Simple deterministic proportional kinematic integration toward target."""
        dx = self.target_x - self.x
        dy = self.target_y - self.y
        dz = self.target_z - self.z
        dist = math.sqrt(dx * dx + dy * dy + dz * dz)

        if dist > 0.1:
            speed = min(max_speed, dist * 1.5)
            self.vx = (dx / dist) * speed
            self.vy = (dy / dist) * speed
            self.vz = (dz / dist) * speed

            self.x += self.vx * dt
            self.y += self.vy * dt
            self.z += self.vz * dt
            self.yaw = math.degrees(math.atan2(dy, dx))
        else:
            self.vx = 0.0
            self.vy = 0.0
            self.vz = 0.0

    def get_vehicle_state(self, sim_time_seconds: float = 0.0) -> VehicleState:
        """Convert to canonical VehicleState schema."""
        from datetime import datetime, timezone
        from app.schemas.simulation_platform import (
            AttitudeVector,
            BatteryState,
            GPSState,
            LinkStatus,
            PositionVector,
            VelocityVector,
        )
        sim_dt = datetime.fromtimestamp(sim_time_seconds, tz=timezone.utc).isoformat()
        return VehicleState(
            timestamp_utc=sim_dt,
            sim_time_seconds=sim_time_seconds,
            vehicle_id=self.vehicle_id,
            autopilot_type=self.autopilot_type,
            connected=True,
            armed=True,
            flight_mode="AUTO",
            position=PositionVector(
                latitude=37.7749 + (self.y / 111111.0),
                longitude=-122.4194 + (self.x / (111111.0 * math.cos(math.radians(37.7749)))),
                altitude_msl=10.0 + self.z,
                altitude_relative=self.z,
            ),
            velocity=VelocityVector(
                vx=round(self.vx, 3),
                vy=round(self.vy, 3),
                vz=round(self.vz, 3),
                ground_speed=round(math.sqrt(self.vx * self.vx + self.vy * self.vy), 3),
            ),
            attitude=AttitudeVector(
                roll_deg=round(self.roll, 2),
                pitch_deg=round(self.pitch, 2),
                yaw_deg=round(self.yaw, 2),
            ),
            battery=BatteryState(voltage_v=15.2, remaining_percent=92.0),
            gps=GPSState(fix_type=3, satellites_visible=14),
            link_status=LinkStatus(rssi_dbm=-60, packet_loss_percent=0.0, latency_ms=10.0),
        )


class MultiVehicleSimulationOrchestrator:
    """Master Orchestrator managing deterministic multi-vehicle simulation execution."""

    def __init__(
        self,
        scenario_id: str = "default_scenario",
        swarm_id: str = "swarm-s12",
        dt_seconds: float = 0.1,
        random_seed: int = 42,
    ):
        self.scenario_id: str = scenario_id
        self.swarm_id: str = swarm_id
        self.clock: SimulationClock = SimulationClock(
            dt_seconds=dt_seconds,
            mode=ClockMode.DETERMINISTIC,
            random_seed=random_seed,
        )
        self.sensor_sim: DeterministicSensorSim = DeterministicSensorSim(
            config=DeterministicSensorConfig(seed=random_seed)
        )
        self.recorder: SimulationRecorder = SimulationRecorder(
            recording_id=f"rec-{uuid.uuid4().hex[:8]}",
            scenario_id=scenario_id,
            dt_seconds=dt_seconds,
        )

        # Swarm & Safety engines
        swarm_cfg = SwarmConfiguration(
            swarm_id=swarm_id,
            name="S12 Multi-Vehicle Swarm",
            leader_vehicle_id=None,
        )
        self.swarm_engine: SwarmEngine = SwarmEngine(swarm_config=swarm_cfg)
        self.safety_action_engine: SwarmSafetyActionEngine = SwarmSafetyActionEngine(
            policy=SwarmSafetyPolicyCreate(name="S12 Safety Policy")
        )
        self.telemetry_fusion: SwarmTelemetryFusionEngine = SwarmTelemetryFusionEngine()
        from app.simulation.core.swarm_aggregation import SwarmAggregationEngine
        self.swarm_aggregation_engine = SwarmAggregationEngine

        self.vehicles: Dict[str, VehicleSimulationInstance] = {}
        self.is_initialized: bool = False

    def add_vehicle(
        self,
        vehicle_id: str,
        autopilot_type: str = "ARDUPILOT",
        initial_pos: tuple = (0.0, 0.0, 0.0),
        role: SwarmRole = SwarmRole.FOLLOWER,
    ) -> VehicleSimulationInstance:
        """Register a new vehicle into orchestrator and swarm."""
        inst = VehicleSimulationInstance(
            vehicle_id=vehicle_id,
            autopilot_type=autopilot_type,
            initial_pos=initial_pos,
        )
        self.vehicles[vehicle_id] = inst
        self.swarm_engine.register_member(
            vehicle_id=vehicle_id,
            role=role,
            autopilot_type=autopilot_type,
            initial_position=initial_pos,
        )
        return inst

    def assign_waypoints(self, vehicle_id: str, waypoints: List[Dict[str, float]]) -> bool:
        """Assign mission waypoints to a specific vehicle."""
        if vehicle_id not in self.vehicles:
            return False
        v = self.vehicles[vehicle_id]
        v.mission_waypoints = waypoints
        v.current_waypoint_idx = 0
        if waypoints:
            v.target_x = waypoints[0].get("x", v.x)
            v.target_y = waypoints[0].get("y", v.y)
            v.target_z = waypoints[0].get("z", v.z)
        return True

    def initialize_swarm(
        self,
        vehicle_ids: List[str],
        formation_type: FormationType = FormationType.V_FORMATION,
        spacing_m: float = 10.0,
    ) -> None:
        """Configure multi-vehicle swarm with leader and formation geometry."""
        self.vehicles.clear()
        for idx, vid in enumerate(vehicle_ids):
            role = SwarmRole.LEADER if idx == 0 else SwarmRole.FOLLOWER
            autopilot = "ARDUPILOT" if idx % 2 == 0 else "PX4"
            pos = (idx * 5.0, 0.0, 10.0)
            self.add_vehicle(vehicle_id=vid, autopilot_type=autopilot, initial_pos=pos, role=role)

        self.swarm_engine.update_formation(formation_type=formation_type, spacing_m=spacing_m)
    def start(self) -> None:
        """Start simulation clock and execution."""
        self.clock.start()

    def pause(self) -> None:
        """Pause simulation execution."""
        self.clock.pause()

    def step(self, count: int = 1) -> SimulationSnapshot:
        """Execute explicit deterministic steps."""
        snap = None
        for _ in range(count):
            snap = self._tick_internal()
        return snap or self.get_latest_snapshot()

    def _tick_internal(self) -> SimulationSnapshot:
        """Subsystem tick update pipeline following explicit phase ordering:

        1. Advance Canonical Simulation Clock -> t_sim
        2. Execute Kinematics & Physics Update per vehicle
        3. Execute Mission Progress & Waypoints
        4. Execute S10 Swarm Engine formation logic
        5. Execute S8/S12 Deterministic Sensor Sim
        6. Execute S11 Swarm Telemetry Fusion
        7. Execute S11 Swarm Safety Action Engine
        8. Build versioned SimulationSnapshot & record
        """
        sim_time = self.clock.tick()
        dt = self.clock.dt_seconds

        # 1 & 2. Physics & Kinematics update
        for vid, vinst in self.vehicles.items():
            vinst.update_kinematics(dt=dt)

        # 3. Mission waypoint progression
        mission_progress = {}
        for vid, vinst in self.vehicles.items():
            if vinst.mission_waypoints:
                dx = vinst.target_x - vinst.x
                dy = vinst.target_y - vinst.y
                dz = vinst.target_z - vinst.z
                if math.sqrt(dx * dx + dy * dy + dz * dz) < 1.0:
                    if vinst.current_waypoint_idx < len(vinst.mission_waypoints) - 1:
                        vinst.current_waypoint_idx += 1
                        wp = vinst.mission_waypoints[vinst.current_waypoint_idx]
                        vinst.target_x = wp.get("x", vinst.x)
                        vinst.target_y = wp.get("y", vinst.y)
                        vinst.target_z = wp.get("z", vinst.z)

                mission_progress[vid] = {
                    "current_index": vinst.current_waypoint_idx,
                    "total_waypoints": len(vinst.mission_waypoints),
                    "completed": vinst.current_waypoint_idx >= len(vinst.mission_waypoints) - 1,
                }

        # 4. Swarm Engine update
        vehicle_states = {vid: vinst.get_vehicle_state(sim_time_seconds=sim_time) for vid, vinst in self.vehicles.items()}
        for vs in vehicle_states.values():
            self.swarm_engine.update_vehicle_telemetry(vs, current_time_s=sim_time)
        swarm_state = self.swarm_engine.step(current_time_s=sim_time)

        # 5. Deterministic Sensor Simulation
        for vid, vs in vehicle_states.items():
            self.sensor_sim.generate_gps_sample(vid, sim_time, vs)
            self.sensor_sim.generate_imu_sample(vid, sim_time, vs)

        # 6. Telemetry Fusion
        fused_telemetry_map = {}
        for vid, vs in vehicle_states.items():
            autopilot_type = self.vehicles[vid].autopilot_type if vid in self.vehicles else "ARDUPILOT"
            norm_vt = self.telemetry_fusion.ingest_vehicle_state(
                swarm_id=self.swarm_id,
                vehicle_state=vs,
                autopilot_type=autopilot_type,
                current_time_s=sim_time,
            )
            fused_telemetry_map[vid] = norm_vt

        telemetry_snap = self.swarm_aggregation_engine.compute_swarm_snapshot(
            swarm_id=self.swarm_id,
            snapshot_sequence=self.clock.tick_count,
            telemetry_map=fused_telemetry_map,
            current_time_s=sim_time,
        )

        # 7. Safety Action Engine
        safety_decisions = self.safety_action_engine.evaluate_safety_policy(
            snapshot=telemetry_snap,
            leader_vehicle_id=self.swarm_engine.config.leader_vehicle_id,
            current_time_s=sim_time,
        )

        safety_events = swarm_state.safety_events

        # 8. Create canonical snapshot
        from datetime import datetime, timezone
        snap_dt = datetime.fromtimestamp(sim_time, tz=timezone.utc).isoformat()
        snapshot = SimulationSnapshot(
            snapshot_id=f"snap-{self.clock.tick_count:06d}",
            version=1,
            sim_time_seconds=sim_time,
            tick_count=self.clock.tick_count,
            timestamp_utc=snap_dt,
            vehicles_state=vehicle_states,
            swarm_state=swarm_state,
            telemetry_snapshot=telemetry_snap,
            safety_events=safety_events,
            safety_decisions=safety_decisions,
            mission_progress=mission_progress,
        )

        self.recorder.record_snapshot(snapshot)
        return snapshot

    def get_latest_snapshot(self) -> SimulationSnapshot:
        """Retrieve latest snapshot or generate zero snapshot."""
        if self.recorder.snapshots:
            return self.recorder.snapshots[-1]
        return SimulationSnapshot(
            snapshot_id="snap-000000",
            version=1,
            sim_time_seconds=self.clock.sim_time_seconds,
            tick_count=self.clock.tick_count,
            vehicles_state={vid: v.get_vehicle_state(sim_time_seconds=self.clock.sim_time_seconds) for vid, v in self.vehicles.items()},
        )
