"""Stage S11 Swarm Safety-Action Engine & Policy Evaluator.

Evaluates multi-vehicle swarm telemetry against configurable safety policies, generating
deterministic, auditable safety action decisions (WARN, HOLD, SLOW_DOWN, INCREASE_SEPARATION, REFORM, ISOLATE_VEHICLE, MARK_DISCONNECTED, ABORT_SWARM_MISSION).
"""

import time
import uuid
from typing import Dict, List, Optional
from app.schemas.swarm_safety import (
    SafetyActionType,
    SwarmSafetyActionDecision,
    SwarmSafetyPolicyCreate,
    SwarmSafetyPolicyResponse,
)
from app.schemas.swarm_telemetry import SwarmTelemetrySnapshot


class SwarmSafetyActionEngine:
    """Policy-driven deterministic safety action decision engine."""

    def __init__(self, policy: Optional[SwarmSafetyPolicyCreate] = None):
        self.policy = policy or SwarmSafetyPolicyCreate(name="Default Swarm Safety Policy")
        # Cooldown map: (event_key, vehicle_id) -> last_triggered_timestamp
        self._action_cooldowns: Dict[str, float] = {}

    def set_policy(self, policy: SwarmSafetyPolicyCreate) -> None:
        self.policy = policy

    def evaluate_safety_policy(
        self,
        snapshot: SwarmTelemetrySnapshot,
        leader_vehicle_id: Optional[str] = None,
        current_time_s: Optional[float] = None,
    ) -> List[SwarmSafetyActionDecision]:
        """Evaluate swarm telemetry snapshot against policy rules and produce safety action decisions.

        Returns:
            List of deterministic, auditable SwarmSafetyActionDecision instances.
        """
        now = current_time_s if current_time_s is not None else time.time()
        decisions: List[SwarmSafetyActionDecision] = []

        pol = self.policy
        cooldown_s = pol.cooldown_s

        # Helper to check debounce cooldown
        def _can_trigger(key: str) -> bool:
            last_ts = self._action_cooldowns.get(key, 0.0)
            if (now - last_ts) >= cooldown_s:
                self._action_cooldowns[key] = now
                return True
            return False

        # Helper to generate deterministic decision ID
        import hashlib
        def _make_dec_id(key: str) -> str:
            h = hashlib.sha256(f"{key}_{now}".encode("utf-8")).hexdigest()[:8]
            return f"dec-{h}"

        # 1. Check Spatial Separation Breaches (Pairwise)
        min_dist = snapshot.pairwise_separation_stats.min_distance_m
        pair = snapshot.pairwise_separation_stats.closest_pair

        if pair and min_dist > 0.0:
            v1, v2 = pair
            if min_dist < pol.critical_separation_m:
                key = f"sep_crit_{v1}_{v2}"
                if _can_trigger(key):
                    decisions.append(
                        SwarmSafetyActionDecision(
                            decision_id=_make_dec_id(key),
                            swarm_id=snapshot.swarm_id,
                            vehicle_id=v1,
                            target_vehicle_id=v2,
                            condition="CRITICAL_SEPARATION_BREACH",
                            severity="CRITICAL",
                            measured_value=min_dist,
                            threshold_value=pol.critical_separation_m,
                            selected_action=SafetyActionType.INCREASE_SEPARATION,
                            details={"message": f"Critical distance breach between {v1} and {v2}: {min_dist:.2f}m < {pol.critical_separation_m:.2f}m"},
                        )
                    )
            elif min_dist < pol.warning_separation_m:
                key = f"sep_warn_{v1}_{v2}"
                if _can_trigger(key):
                    decisions.append(
                        SwarmSafetyActionDecision(
                            decision_id=_make_dec_id(key),
                            swarm_id=snapshot.swarm_id,
                            vehicle_id=v1,
                            target_vehicle_id=v2,
                            condition="WARNING_SEPARATION_PROXIMITY",
                            severity="WARNING",
                            measured_value=min_dist,
                            threshold_value=pol.warning_separation_m,
                            selected_action=SafetyActionType.WARN,
                            details={"message": f"Separation warning proximity between {v1} and {v2}: {min_dist:.2f}m < {pol.warning_separation_m:.2f}m"},
                        )
                    )

        # 2. Check Formation Deviation
        max_dev = snapshot.formation_deviation_stats.max_error_m
        if max_dev > pol.formation_deviation_threshold_m:
            key = f"form_dev_{snapshot.swarm_id}"
            if _can_trigger(key):
                decisions.append(
                    SwarmSafetyActionDecision(
                        decision_id=_make_dec_id(key),
                        swarm_id=snapshot.swarm_id,
                        condition="FORMATION_DIVERGENCE",
                        severity="WARNING",
                        measured_value=max_dev,
                        threshold_value=pol.formation_deviation_threshold_m,
                        selected_action=SafetyActionType.REFORM,
                        details={"message": f"Formation deviation exceeded threshold: {max_dev:.2f}m > {pol.formation_deviation_threshold_m:.2f}m"},
                    )
                )

        # 3. Check Leader Telemetry Timeout
        if leader_vehicle_id:
            leader_tel = snapshot.vehicles_telemetry.get(leader_vehicle_id)
            if not leader_tel or leader_tel.telemetry_age_s > pol.leader_timeout_s:
                key = f"leader_loss_{leader_vehicle_id}"
                if _can_trigger(key):
                    decisions.append(
                        SwarmSafetyActionDecision(
                            decision_id=_make_dec_id(key),
                            swarm_id=snapshot.swarm_id,
                            vehicle_id=leader_vehicle_id,
                            condition="LEADER_TIMEOUT_LOST",
                            severity="CRITICAL",
                            measured_value=leader_tel.telemetry_age_s if leader_tel else 999.0,
                            threshold_value=pol.leader_timeout_s,
                            selected_action=SafetyActionType.HOLD,
                            details={"message": f"Leader vehicle {leader_vehicle_id} lost or telemetry timed out"},
                        )
                    )

        # 4. Check Vehicle Telemetry Staleness / Dropout
        for vid, vtel in snapshot.vehicles_telemetry.items():
            if vtel.telemetry_age_s > pol.telemetry_timeout_s:
                key = f"telemetry_stale_{vid}"
                if _can_trigger(key):
                    decisions.append(
                        SwarmSafetyActionDecision(
                            decision_id=_make_dec_id(key),
                            swarm_id=snapshot.swarm_id,
                            vehicle_id=vid,
                            condition="TELEMETRY_DROPOUT",
                            severity="WARNING",
                            measured_value=vtel.telemetry_age_s,
                            threshold_value=pol.telemetry_timeout_s,
                            selected_action=SafetyActionType.MARK_DISCONNECTED,
                            details={"message": f"Vehicle {vid} telemetry timed out ({vtel.telemetry_age_s:.1f}s)"},
                        )
                    )

        # 5. Check Communication Link Degradation
        min_qual = snapshot.communication_quality_summary.min_quality_percent
        if min_qual < pol.link_quality_threshold_percent:
            key = f"comm_deg_{snapshot.swarm_id}"
            if _can_trigger(key):
                decisions.append(
                    SwarmSafetyActionDecision(
                        decision_id=_make_dec_id(key),
                        swarm_id=snapshot.swarm_id,
                        condition="COMMUNICATION_LINK_DEGRADED",
                        severity="WARNING",
                        measured_value=min_qual,
                        threshold_value=pol.link_quality_threshold_percent,
                        selected_action=SafetyActionType.WARN,
                        details={"message": f"Communication quality degraded below threshold: {min_qual:.1f}% < {pol.link_quality_threshold_percent:.1f}%"},
                    )
                )

        return decisions
