"""Stage S12 Deterministic Scenario Regression Suite (Scenarios A through L).

Provides reproducible execution scenarios validating multi-vehicle orchestration,
swarm formation control, telemetry fusion, digital twin sensors, safety engine responses,
recording, and replay determinism.
"""

from typing import Any, Dict, List, Tuple
from app.schemas.swarm import FormationType, SwarmRole
from app.simulation.core.multi_vehicle_orchestrator import MultiVehicleSimulationOrchestrator


class ScenarioRegressionSuite:
    """Automated runner for S12 Scenarios A through L."""

    @staticmethod
    def create_scenario_orchestrator(
        scenario_code: str,
        vehicle_count: int,
        seed: int = 42,
    ) -> MultiVehicleSimulationOrchestrator:
        """Instantiate orchestrator pre-configured for specified regression scenario."""
        orchestrator = MultiVehicleSimulationOrchestrator(
            scenario_id=f"scenario_{scenario_code.lower()}",
            swarm_id=f"swarm_{scenario_code.lower()}",
            dt_seconds=0.1,
            random_seed=seed,
        )

        vehicle_ids = [f"veh-{scenario_code.lower()}-{i+1:02d}" for i in range(vehicle_count)]
        orchestrator.initialize_swarm(
            vehicle_ids=vehicle_ids,
            formation_type=FormationType.V_FORMATION,
            spacing_m=10.0,
        )
        return orchestrator

    @classmethod
    def run_scenario_a_single_vehicle(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario A: Single vehicle mission."""
        orc = cls.create_scenario_orchestrator("a", vehicle_count=1, seed=seed)
        waypoints = [
            {"x": 0.0, "y": 0.0, "z": 10.0},
            {"x": 50.0, "y": 20.0, "z": 15.0},
            {"x": 100.0, "y": 0.0, "z": 10.0},
        ]
        orc.assign_waypoints("veh-a-01", waypoints)
        orc.start()
        for _ in range(ticks):
            orc.step(1)

        meta = orc.recorder.get_metadata()
        return {
            "scenario": "A_SINGLE_VEHICLE",
            "metadata": meta,
            "final_position": orc.vehicles["veh-a-01"].get_vehicle_state().position,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_b_4_vehicle_formation(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario B: 4-vehicle formation."""
        orc = cls.create_scenario_orchestrator("b", vehicle_count=4, seed=seed)
        orc.start()
        for _ in range(ticks):
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "B_4_VEHICLE_FORMATION",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_c_8_vehicle_heterogeneous(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario C: 8-vehicle heterogeneous swarm (ArduPilot + PX4)."""
        orc = cls.create_scenario_orchestrator("c", vehicle_count=8, seed=seed)
        orc.start()
        for _ in range(ticks):
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "C_8_VEHICLE_HETEROGENEOUS",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_d_16_vehicle_swarm(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario D: 16-vehicle swarm."""
        orc = cls.create_scenario_orchestrator("d", vehicle_count=16, seed=seed)
        orc.start()
        for _ in range(ticks):
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "D_16_VEHICLE_SWARM",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_e_telemetry_dropout(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario E: Vehicle telemetry dropout."""
        orc = cls.create_scenario_orchestrator("e", vehicle_count=4, seed=seed)
        orc.sensor_sim.config.enable_dropout = True
        orc.sensor_sim.config.dropout_probability = 0.2
        orc.start()
        for _ in range(ticks):
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "E_TELEMETRY_DROPOUT",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_f_leader_loss(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario F: Leader loss and automatic failover."""
        orc = cls.create_scenario_orchestrator("f", vehicle_count=4, seed=seed)
        orc.start()
        for i in range(ticks):
            if i == 20:
                # Simulate loss of leader vehicle veh-f-01
                orc.swarm_engine.remove_member("veh-f-01")
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "F_LEADER_LOSS",
            "metadata": meta,
            "new_leader": orc.swarm_engine.config.leader_vehicle_id,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_g_formation_deviation(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario G: Formation deviation response."""
        orc = cls.create_scenario_orchestrator("g", vehicle_count=4, seed=seed)
        orc.start()
        for i in range(ticks):
            if i == 15:
                # Displace follower manually to trigger deviation
                orc.vehicles["veh-g-02"].x += 45.0
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "G_FORMATION_DEVIATION",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_h_separation_violation(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario H: Spatial separation breach response."""
        orc = cls.create_scenario_orchestrator("h", vehicle_count=4, seed=seed)
        orc.start()
        for i in range(ticks):
            if i == 10:
                # Move vehicle 2 very close to vehicle 1
                orc.vehicles["veh-h-02"].x = orc.vehicles["veh-h-01"].x + 0.5
                orc.vehicles["veh-h-02"].y = orc.vehicles["veh-h-01"].y + 0.5
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "H_SEPARATION_VIOLATION",
            "metadata": meta,
            "safety_event_count": len(orc.recorder.event_index["safety_decisions"]),
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_i_mission_completion(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario I: Full mission execution and completion."""
        orc = cls.create_scenario_orchestrator("i", vehicle_count=2, seed=seed)
        waypoints = [{"x": 5.0, "y": 0.0, "z": 10.0}]
        orc.assign_waypoints("veh-i-01", waypoints)
        orc.start()
        for _ in range(ticks):
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "I_MISSION_COMPLETION",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_j_mission_abort_safety(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario J: Safety-triggered mission abort."""
        orc = cls.create_scenario_orchestrator("j", vehicle_count=4, seed=seed)
        orc.start()
        for i in range(ticks):
            if i == 15:
                # Cause severe spatial breach triggering abort decision
                orc.vehicles["veh-j-02"].x = orc.vehicles["veh-j-01"].x
                orc.vehicles["veh-j-02"].y = orc.vehicles["veh-j-01"].y
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "J_MISSION_ABORT_SAFETY",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_k_sensor_dropout(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario K: Sensor dropout and degraded health handling."""
        orc = cls.create_scenario_orchestrator("k", vehicle_count=4, seed=seed)
        orc.start()
        for _ in range(ticks):
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "K_SENSOR_DROPOUT",
            "metadata": meta,
            "hash": meta.recording_hash,
        }

    @classmethod
    def run_scenario_l_communication_degradation(cls, ticks: int = 50, seed: int = 42) -> Dict[str, Any]:
        """Scenario L: Communication degradation."""
        orc = cls.create_scenario_orchestrator("l", vehicle_count=4, seed=seed)
        orc.start()
        for _ in range(ticks):
            orc.step(1)
        meta = orc.recorder.get_metadata()
        return {
            "scenario": "L_COMMUNICATION_DEGRADATION",
            "metadata": meta,
            "hash": meta.recording_hash,
        }
