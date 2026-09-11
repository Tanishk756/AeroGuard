"""Stage S10 Multi-Vehicle Swarm & Formation Control REST API Routes."""

import uuid
from typing import Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.hardware_registry import PersistentVehicle
from app.models.swarm import PersistentSwarm, PersistentSwarmMember
from app.schemas.swarm import (
    FormationConfiguration,
    FormationSlot,
    FormationType,
    SwarmConfiguration,
    SwarmConstraints,
    SwarmCreate,
    SwarmFormationSet,
    SwarmHealth,
    SwarmMemberAdd,
    SwarmMemberConfig,
    SwarmMemberResponse,
    SwarmResponse,
    SwarmRole,
    SwarmState,
    SwarmUpdate,
)
from app.simulation.core.swarm_engine import SwarmEngine

router = APIRouter(prefix="/simulation/swarms", tags=["Swarms"])

# Active in-memory SwarmEngine runtime cache: swarm_id -> SwarmEngine
_active_swarm_engines: Dict[str, SwarmEngine] = {}


def _get_or_create_engine(swarm: PersistentSwarm) -> SwarmEngine:
    if swarm.id in _active_swarm_engines:
        return _active_swarm_engines[swarm.id]

    members_config: List[SwarmMemberConfig] = []
    for member in swarm.members:
        members_config.append(
            SwarmMemberConfig(
                vehicle_id=member.vehicle_id,
                role=SwarmRole(member.role),
                slot_index=member.slot_index,
                autopilot_type="ARDUPILOT",  # Default autopilot type
                initial_position=(0.0, 0.0, 0.0),
                initial_heading_deg=0.0,
            )
        )

    slots_map: Dict[int, FormationSlot] = {}
    formation_config = FormationConfiguration(
        formation_type=FormationType(swarm.formation_type),
        spacing_m=swarm.formation_spacing_m,
        altitude_offset_m=0.0,
        slots=slots_map,
    )

    constraints = SwarmConstraints(min_separation_m=swarm.min_separation_m)

    config = SwarmConfiguration(
        swarm_id=swarm.id,
        name=swarm.name,
        description=swarm.description,
        leader_vehicle_id=swarm.leader_vehicle_id,
        formation=formation_config,
        members=members_config,
        constraints=constraints,
    )

    engine = SwarmEngine(config)
    _active_swarm_engines[swarm.id] = engine
    return engine


def _to_swarm_response(swarm: PersistentSwarm) -> SwarmResponse:
    member_responses = [
        SwarmMemberResponse(
            id=m.id,
            swarm_id=m.swarm_id,
            vehicle_id=m.vehicle_id,
            role=m.role,
            slot_index=m.slot_index,
            offset_x=m.offset_x,
            offset_y=m.offset_y,
            offset_z=m.offset_z,
        )
        for m in swarm.members
    ]
    return SwarmResponse(
        id=swarm.id,
        name=swarm.name,
        description=swarm.description,
        leader_vehicle_id=swarm.leader_vehicle_id,
        formation_type=swarm.formation_type,
        formation_spacing_m=swarm.formation_spacing_m,
        min_separation_m=swarm.min_separation_m,
        status=swarm.status,
        members=member_responses,
        created_at=swarm.created_at,
        updated_at=swarm.updated_at,
    )


@router.post("", response_model=SwarmResponse, status_code=status.HTTP_201_CREATED)
def create_swarm(payload: SwarmCreate, db: Session = Depends(get_db)):
    """POST /api/v1/simulation/swarms - Create a new multi-vehicle swarm."""
    swarm_id = f"swm-{uuid.uuid4().hex[:8]}"

    leader_id = payload.leader_vehicle_id
    if not leader_id and payload.member_vehicle_ids:
        leader_id = payload.member_vehicle_ids[0]

    swarm = PersistentSwarm(
        id=swarm_id,
        name=payload.name,
        description=payload.description,
        leader_vehicle_id=leader_id,
        formation_type=payload.formation_type.value,
        formation_spacing_m=payload.formation_spacing_m,
        min_separation_m=payload.min_separation_m,
        status="IDLE",
    )
    db.add(swarm)
    db.commit()

    for idx, vid in enumerate(payload.member_vehicle_ids):
        role = "LEADER" if vid == leader_id else "FOLLOWER"
        member = PersistentSwarmMember(
            id=f"smem-{uuid.uuid4().hex[:8]}",
            swarm_id=swarm.id,
            vehicle_id=vid,
            role=role,
            slot_index=idx,
        )
        db.add(member)

    db.commit()
    db.refresh(swarm)
    return _to_swarm_response(swarm)


@router.get("", response_model=List[SwarmResponse])
def list_swarms(db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms - List all registered swarms."""
    swarms = db.scalars(select(PersistentSwarm)).all()
    return [_to_swarm_response(s) for s in swarms]


@router.get("/{swarm_id}", response_model=SwarmResponse)
def get_swarm(swarm_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms/{id} - Get swarm configuration by ID."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")
    return _to_swarm_response(swarm)


@router.put("/{swarm_id}", response_model=SwarmResponse)
def update_swarm(swarm_id: str, payload: SwarmUpdate, db: Session = Depends(get_db)):
    """PUT /api/v1/simulation/swarms/{id} - Update swarm parameters."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    if payload.name is not None:
        swarm.name = payload.name
    if payload.description is not None:
        swarm.description = payload.description
    if payload.leader_vehicle_id is not None:
        swarm.leader_vehicle_id = payload.leader_vehicle_id
    if payload.formation_type is not None:
        swarm.formation_type = payload.formation_type.value
    if payload.formation_spacing_m is not None:
        swarm.formation_spacing_m = payload.formation_spacing_m
    if payload.min_separation_m is not None:
        swarm.min_separation_m = payload.min_separation_m
    if payload.status is not None:
        swarm.status = payload.status

    db.commit()
    db.refresh(swarm)

    # Invalidate engine cache
    if swarm_id in _active_swarm_engines:
        del _active_swarm_engines[swarm_id]

    return _to_swarm_response(swarm)


@router.delete("/{swarm_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_swarm(swarm_id: str, db: Session = Depends(get_db)):
    """DELETE /api/v1/simulation/swarms/{id} - Delete swarm."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    db.delete(swarm)
    db.commit()

    if swarm_id in _active_swarm_engines:
        del _active_swarm_engines[swarm_id]


@router.post("/{swarm_id}/vehicles", response_model=SwarmResponse)
def add_swarm_member(swarm_id: str, payload: SwarmMemberAdd, db: Session = Depends(get_db)):
    """POST /api/v1/simulation/swarms/{id}/vehicles - Add a vehicle member to the swarm."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    # Check vehicle existence
    vehicle = db.get(PersistentVehicle, payload.vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{payload.vehicle_id}' not found")

    existing_member = next((m for m in swarm.members if m.vehicle_id == payload.vehicle_id), None)
    if existing_member:
        raise HTTPException(status_code=400, detail=f"Vehicle '{payload.vehicle_id}' is already in swarm '{swarm_id}'")

    slot_idx = payload.slot_index if payload.slot_index is not None else len(swarm.members)
    role_val = payload.role.value if payload.role else "FOLLOWER"

    member = PersistentSwarmMember(
        id=f"smem-{uuid.uuid4().hex[:8]}",
        swarm_id=swarm.id,
        vehicle_id=payload.vehicle_id,
        role=role_val,
        slot_index=slot_idx,
    )
    db.add(member)
    db.commit()
    db.refresh(swarm)

    if swarm_id in _active_swarm_engines:
        del _active_swarm_engines[swarm_id]

    return _to_swarm_response(swarm)


@router.delete("/{swarm_id}/vehicles/{vehicle_id}", response_model=SwarmResponse)
def remove_swarm_member(swarm_id: str, vehicle_id: str, db: Session = Depends(get_db)):
    """DELETE /api/v1/simulation/swarms/{id}/vehicles/{vehicle_id} - Remove vehicle member from swarm."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    member = next((m for m in swarm.members if m.vehicle_id == vehicle_id), None)
    if not member:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' is not in swarm '{swarm_id}'")

    db.delete(member)
    db.commit()
    db.refresh(swarm)

    if swarm_id in _active_swarm_engines:
        del _active_swarm_engines[swarm_id]

    return _to_swarm_response(swarm)


@router.post("/{swarm_id}/formation", response_model=SwarmResponse)
def set_swarm_formation(swarm_id: str, payload: SwarmFormationSet, db: Session = Depends(get_db)):
    """POST /api/v1/simulation/swarms/{id}/formation - Set formation parameters."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    swarm.formation_type = payload.formation_type.value
    swarm.formation_spacing_m = payload.formation_spacing_m
    db.commit()
    db.refresh(swarm)

    if swarm_id in _active_swarm_engines:
        del _active_swarm_engines[swarm_id]

    return _to_swarm_response(swarm)


@router.get("/{swarm_id}/state", response_model=SwarmState)
def get_swarm_state(swarm_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms/{id}/state - Get current real-time swarm telemetry and target state."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    engine = _get_or_create_engine(swarm)
    return engine.step()


@router.get("/{swarm_id}/health")
def get_swarm_health(swarm_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/simulation/swarms/{id}/health - Get aggregated health status and safety events."""
    swarm = db.get(PersistentSwarm, swarm_id)
    if not swarm:
        raise HTTPException(status_code=404, detail=f"Swarm '{swarm_id}' not found")

    engine = _get_or_create_engine(swarm)
    state = engine.step()
    return {
        "swarm_id": swarm_id,
        "health": state.health.value,
        "active_vehicle_count": len(state.vehicle_states),
        "safety_event_count": len(state.safety_events),
        "safety_events": [e.model_dump() for e in state.safety_events],
    }
