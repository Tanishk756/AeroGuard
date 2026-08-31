"""Stage S5 Simulation Failure Injection Engine (Motor Failure Foundation)."""

from typing import Dict, Any, List
from app.core.telemetry import SIMULATION_FAILURE_INJECTION_TOTAL


class SimulationFailureInjector:
    """Injects real-time hardware fault events into running simulation channels."""

    _active_faults: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def inject_motor_failure(cls, run_id: str, motor_index: int, severity: float = 1.0) -> Dict[str, Any]:
        SIMULATION_FAILURE_INJECTION_TOTAL.inc()

        fault_key = f"{run_id}_motor_{motor_index}"
        fault_record = {
            "run_id": run_id,
            "target": f"motor_{motor_index}",
            "fault_type": "MOTOR_FAILURE",
            "motor_index": motor_index,
            "severity": min(1.0, max(0.0, severity)),
            "active": True,
        }

        cls._active_faults[fault_key] = fault_record
        return fault_record

    @classmethod
    def get_active_faults(cls, run_id: str) -> List[Dict[str, Any]]:
        return [f for f in cls._active_faults.values() if f["run_id"] == run_id and f["active"]]

    @classmethod
    def clear_faults(cls, run_id: str) -> None:
        keys_to_remove = [k for k, f in cls._active_faults.items() if f["run_id"] == run_id]
        for k in keys_to_remove:
            del cls._active_faults[k]
