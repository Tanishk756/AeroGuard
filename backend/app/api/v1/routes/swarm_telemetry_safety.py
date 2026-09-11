"""Stage S11 Swarm Telemetry & Safety-Action REST & Streaming API Routes."""

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.swarm import PersistentSwarm
from app.models.swarm_safety import PersistentSwarmSafetyEvent, PersistentSwarmSafetyPolicy
from app.schemas.swarm_safety import (
    SwarmSafetyActionDecision,
    SwarmSafetyPolicyCreate,
    SwarmSafetyPolicyResponse,
)
from app.schemas.swarm_telemetry import (
    SwarmTelemetrySnapshot,
    SwarmVehicleTelemetry,
)
from app.simulation.core.swarm_aggregation import SwarmAggregationEngine
from app.simulation.core.swarm_safety_action_engine import SwarmSafetyActionEngine
from app.simulation.core.swarm_telemetry_fusion import SwarmTelemetryFusionEngine

router = APIRouter(prefix="/simulation/swarms", tags=["Swarm Telemetry & Safety"])

# In-memory fusion & safety action engines per swarm
_fusion_engines: Dict[str, SwarmTelemetryFusionEngine] = {}
_safety_action_engines: Dict[str, SwarmSafetyActionEngine] = {}


def _get_fusion_engine(swarm_id: str) -> SwarmTelemetryFusionEngine:
    if swarm_id not in _fusion_engines:
        _fusion_engines[swarm_id] = SwarmTelemetryFusionEngine()
    return _fusion_engines[swarm_id]


def _get_safety_action_engine(swarm_id: str) -> SwarmSafetyActionEngine:
    if swarm_id not in _safety_action_engines:
        _safety_action_engines[swarm_id] = SwarmSafetyActionEngine()
    return _safety_action_engines[swarm_id]


@router.get("/{swarm_id}/telemetry/snapshot", response_model=SwarmTelemetrySnapshot)
def get_swarm_telemetry_snapshot(swarm_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms/{id}/telemetry/snapshot - Get real-time fused telemetry snapshot."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    fusion = _get_fusion_engine(swarm_id)
    active_tel = fusion.get_active_telemetry_map()
    return SwarmAggregationEngine.compute_swarm_snapshot(
        swarm_id=swarm_id,
        snapshot_sequence=1,
        telemetry_map=active_tel,
    )


@router.get("/{swarm_id}/vehicles/{vehicle_id}/telemetry", response_model=SwarmVehicleTelemetry)
def get_swarm_vehicle_telemetry(swarm_id: str, vehicle_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms/{id}/vehicles/{vehicle_id}/telemetry - Get latest telemetry for a single member."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    fusion = _get_fusion_engine(swarm_id)
    tel = fusion.get_latest_vehicle_telemetry(vehicle_id)
    if not tel:
        raise HTTPException(status_code=404, detail=f"No telemetry found for vehicle '{vehicle_id}' in swarm '{swarm_id}'")
    return tel


@router.get("/{swarm_id}/safety/policies", response_model=List[SwarmSafetyPolicyResponse])
def list_swarm_safety_policies(swarm_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms/{id}/safety/policies - List safety policies for swarm."""
    policies = db.scalars(
        select(PersistentSwarmSafetyPolicy).where(
            (PersistentSwarmSafetyPolicy.swarm_id == swarm_id) | (PersistentSwarmSafetyPolicy.swarm_id.is_(None))
        )
    ).all()
    return [SwarmSafetyPolicyResponse.model_validate(p) for p in policies]


@router.post("/{swarm_id}/safety/policies", response_model=SwarmSafetyPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_swarm_safety_policy(swarm_id: str, payload: SwarmSafetyPolicyCreate, db: Session = Depends(get_db)):
    """POST /api/v1/simulation/swarms/{id}/safety/policies - Create a new safety policy."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    policy_id = f"spol-{uuid.uuid4().hex[:8]}"
    pol = PersistentSwarmSafetyPolicy(
        id=policy_id,
        swarm_id=swarm_id,
        name=payload.name,
        min_separation_m=payload.min_separation_m,
        warning_separation_m=payload.warning_separation_m,
        critical_separation_m=payload.critical_separation_m,
        telemetry_timeout_s=payload.telemetry_timeout_s,
        link_quality_threshold_percent=payload.link_quality_threshold_percent,
        formation_deviation_threshold_m=payload.formation_deviation_threshold_m,
        leader_timeout_s=payload.leader_timeout_s,
        cooldown_s=payload.cooldown_s,
        action_escalation=payload.action_escalation,
    )

    db.add(pol)
    db.commit()
    db.refresh(pol)

    # Update in-memory engine policy
    action_engine = _get_safety_action_engine(swarm_id)
    action_engine.set_policy(payload)

    return SwarmSafetyPolicyResponse.model_validate(pol)


@router.get("/{swarm_id}/safety/events")
def list_swarm_safety_events(swarm_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms/{id}/safety/events - Get auditable safety decision event log."""
    events = db.scalars(
        select(PersistentSwarmSafetyEvent)
        .where(PersistentSwarmSafetyEvent.swarm_id == swarm_id)
        .order_by(PersistentSwarmSafetyEvent.timestamp.desc())
    ).all()
    return [
        {
            "id": e.id,
            "swarm_id": e.swarm_id,
            "vehicle_id": e.vehicle_id,
            "target_vehicle_id": e.target_vehicle_id,
            "event_type": e.event_type,
            "severity": e.severity,
            "measured_value": e.measured_value,
            "threshold_value": e.threshold_value,
            "executed_action": e.executed_action,
            "timestamp": e.timestamp.isoformat(),
            "details": e.details_json,
        }
        for e in events
    ]


@router.post("/{swarm_id}/safety/eval", response_model=List[SwarmSafetyActionDecision])
def evaluate_swarm_safety_policy(swarm_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/simulation/swarms/{id}/safety/eval - Trigger explicit safety policy evaluation."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    fusion = _get_fusion_engine(swarm_id)
    action_engine = _get_safety_action_engine(swarm_id)

    telemetry_map = fusion.get_active_telemetry_map()
    snapshot = SwarmAggregationEngine.compute_swarm_snapshot(
        swarm_id=swarm_id, snapshot_sequence=1, telemetry_map=telemetry_map
    )

    decisions = action_engine.evaluate_safety_policy(
        snapshot=snapshot, leader_vehicle_id=swarm.leader_vehicle_id
    )

    # Persist auditable decisions to DB
    for d in decisions:
        event_entity = PersistentSwarmSafetyEvent(
            id=d.decision_id,
            swarm_id=swarm_id,
            vehicle_id=d.vehicle_id,
            target_vehicle_id=d.target_vehicle_id,
            event_type=d.condition,
            severity=d.severity,
            measured_value=d.measured_value,
            threshold_value=d.threshold_value,
            executed_action=d.selected_action.value,
            details_json=d.details,
            timestamp=d.timestamp,
        )
        db.add(event_entity)

    if decisions:
        db.commit()

    return decisions
