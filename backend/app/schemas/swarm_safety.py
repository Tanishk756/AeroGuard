"""Stage S11 Swarm Safety-Action Engine & Policy Pydantic Schemas."""

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SafetyActionType(str, Enum):
    WARN = "WARN"
    HOLD = "HOLD"
    SLOW_DOWN = "SLOW_DOWN"
    INCREASE_SEPARATION = "INCREASE_SEPARATION"
    REFORM = "REFORM"
    ISOLATE_VEHICLE = "ISOLATE_VEHICLE"
    MARK_DISCONNECTED = "MARK_DISCONNECTED"
    ABORT_SWARM_MISSION = "ABORT_SWARM_MISSION"


class SwarmSafetyPolicyCreate(BaseModel):
    name: str
    swarm_id: Optional[str] = None
    min_separation_m: float = Field(default=5.0, ge=1.0)
    warning_separation_m: float = Field(default=8.0, ge=1.0)
    critical_separation_m: float = Field(default=3.0, ge=0.5)
    telemetry_timeout_s: float = Field(default=5.0, ge=1.0)
    link_quality_threshold_percent: float = Field(default=50.0, ge=0.0, le=100.0)
    formation_deviation_threshold_m: float = Field(default=4.0, ge=0.5)
    leader_timeout_s: float = Field(default=5.0, ge=1.0)
    cooldown_s: float = Field(default=10.0, ge=0.0)
    action_escalation: Dict[str, Any] = Field(default_factory=dict)


class SwarmSafetyPolicyResponse(BaseModel):
    id: str
    swarm_id: Optional[str] = None
    name: str
    min_separation_m: float
    warning_separation_m: float
    critical_separation_m: float
    telemetry_timeout_s: float
    link_quality_threshold_percent: float
    formation_deviation_threshold_m: float
    leader_timeout_s: float
    cooldown_s: float
    action_escalation: Dict[str, Any]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class SwarmSafetyActionDecision(BaseModel):
    decision_id: str
    swarm_id: str
    vehicle_id: Optional[str] = None
    target_vehicle_id: Optional[str] = None
    condition: str
    severity: str  # INFO, WARNING, CRITICAL
    measured_value: Optional[float] = None
    threshold_value: Optional[float] = None
    selected_action: SafetyActionType
    policy_id: Optional[str] = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    details: Dict[str, Any] = Field(default_factory=dict)
