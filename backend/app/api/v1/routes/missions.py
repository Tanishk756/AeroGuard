"""Stage S7 Mission Management & Execution REST API and WebSocket Routes."""

import json
import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.mission import PersistentMission, PersistentMissionItem
from app.schemas.mission import (
    MissionCreate,
    MissionResponse,
    MissionItemSpec,
    CompiledMission,
    MissionValidationDiagnostic,
    MissionProgress,
)
from app.simulation.core.mission_validator import MissionValidationEngine
from app.simulation.core.mission_compiler import MissionCompiler
from app.services.mission_execution import MissionExecutionService
from app.core.telemetry import MISSIONS_CREATED_TOTAL

router = APIRouter(prefix="/missions", tags=["Missions"])


def _to_mission_response(mission: PersistentMission) -> MissionResponse:
    items = [
        MissionItemSpec(
            id=item.id,
            sequence=item.sequence,
            command_type=item.command_type,
            latitude=item.latitude,
            longitude=item.longitude,
            altitude_m=item.altitude_m,
            acceptance_radius_m=item.acceptance_radius_m,
            loiter_duration_s=item.loiter_duration_s,
            params=item.params_json,
        )
        for item in mission.items
    ]
    return MissionResponse(
        id=mission.id,
        project_id=mission.project_id,
        vehicle_id=mission.vehicle_id,
        scenario_id=mission.scenario_id,
        name=mission.name,
        description=mission.description,
        version=mission.version,
        status=mission.status,
        items=items,
        created_at=mission.created_at.isoformat(),
        updated_at=mission.updated_at.isoformat(),
    )


@router.post("", response_model=MissionResponse, status_code=status.HTTP_201_CREATED)
def create_mission(payload: MissionCreate, db: Session = Depends(get_db)):
    """POST /api/v1/missions - Create a new first-class versioned flight mission."""
    diag = MissionValidationEngine.validate_mission_payload(payload, db)
    if not diag.valid:
        raise HTTPException(status_code=400, detail={"message": "Mission validation failed", "errors": diag.errors})

    MISSIONS_CREATED_TOTAL.inc()
    mission_id = f"msn-{uuid.uuid4().hex[:8]}"
    mission = PersistentMission(
        id=mission_id,
        project_id=payload.project_id,
        vehicle_id=payload.vehicle_id,
        scenario_id=payload.scenario_id,
        name=payload.name,
        description=payload.description,
        version=1,
        status="CREATED",
    )
    db.add(mission)
    db.commit()

    for item in payload.items:
        item_entity = PersistentMissionItem(
            id=f"mitem-{uuid.uuid4().hex[:8]}",
            mission_id=mission.id,
            sequence=item.sequence,
            command_type=item.command_type,
            latitude=item.latitude,
            longitude=item.longitude,
            altitude_m=item.altitude_m,
            acceptance_radius_m=item.acceptance_radius_m,
            loiter_duration_s=item.loiter_duration_s,
            params_json=item.params,
        )
        db.add(item_entity)

    db.commit()
    db.refresh(mission)
    return _to_mission_response(mission)


@router.get("", response_model=List[MissionResponse])
def list_missions(db: Session = Depends(get_db)):
    """GET /api/v1/missions - List all registered flight missions."""
    missions = db.scalars(select(PersistentMission)).all()
    return [_to_mission_response(m) for m in missions]


@router.get("/{mission_id}", response_model=MissionResponse)
def get_mission(mission_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/missions/{id} - Get mission details by ID."""
    mission = db.get(PersistentMission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")
    return _to_mission_response(mission)


@router.post("/{mission_id}/validate", response_model=MissionValidationDiagnostic)
def validate_mission(mission_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/missions/{id}/validate - Validate mission specification."""
    return MissionExecutionService.prepare_and_validate(mission_id, db)


@router.post("/{mission_id}/compile", response_model=CompiledMission)
def compile_mission(mission_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/missions/{id}/compile - Compile canonical mission into cryptographic representation."""
    mission = db.get(PersistentMission, mission_id)
    if not mission:
        raise HTTPException(status_code=404, detail=f"Mission '{mission_id}' not found")

    items_spec = [
        MissionItemSpec(
            sequence=item.sequence,
            command_type=item.command_type,
            latitude=item.latitude,
            longitude=item.longitude,
            altitude_m=item.altitude_m,
            acceptance_radius_m=item.acceptance_radius_m,
            loiter_duration_s=item.loiter_duration_s,
        )
        for item in mission.items
    ]
    return MissionCompiler.compile_mission(
        mission_id=mission.id,
        version=mission.version,
        vehicle_id=mission.vehicle_id,
        scenario_id=mission.scenario_id,
        items=items_spec,
    )


@router.post("/{mission_id}/upload", response_model=MissionResponse)
def upload_mission(mission_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/missions/{id}/upload - Upload mission items to SITL vehicle."""
    success = MissionExecutionService.upload_mission(mission_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to upload mission to SITL vehicle")
    mission = db.get(PersistentMission, mission_id)
    return _to_mission_response(mission)


@router.post("/{mission_id}/start", response_model=MissionResponse)
def start_mission(mission_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/missions/{id}/start - Start mission execution in SITL."""
    success = MissionExecutionService.start_mission(mission_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to start mission execution")
    mission = db.get(PersistentMission, mission_id)
    return _to_mission_response(mission)


@router.post("/{mission_id}/pause", response_model=MissionResponse)
def pause_mission(mission_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/missions/{id}/pause - Pause mission execution."""
    success = MissionExecutionService.pause_mission(mission_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to pause mission")
    mission = db.get(PersistentMission, mission_id)
    return _to_mission_response(mission)


@router.post("/{mission_id}/resume", response_model=MissionResponse)
def resume_mission(mission_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/missions/{id}/resume - Resume mission execution."""
    success = MissionExecutionService.resume_mission(mission_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to resume mission")
    mission = db.get(PersistentMission, mission_id)
    return _to_mission_response(mission)


@router.post("/{mission_id}/abort", response_model=MissionResponse)
def abort_mission(mission_id: str, db: Session = Depends(get_db)):
    """POST /api/v1/missions/{id}/abort - Abort mission execution."""
    success = MissionExecutionService.abort_mission(mission_id, db)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to abort mission")
    mission = db.get(PersistentMission, mission_id)
    return _to_mission_response(mission)


@router.get("/{mission_id}/status", response_model=MissionProgress)
def get_mission_status(mission_id: str):
    """GET /api/v1/missions/{id}/status - Get authoritative telemetry-derived mission progress."""
    prog = MissionExecutionService.get_progress(mission_id)
    if not prog:
        return MissionProgress(
            mission_id=mission_id,
            mission_status="UNKNOWN",
            current_item_index=1,
            completed_items=0,
            total_items=0,
            progress_percentage=0.0,
            distance_to_target_m=0.0,
            mission_elapsed_time_s=0.0,
        )
    return prog


@router.websocket("/{mission_id}/stream")
async def stream_mission_progress(websocket: WebSocket, mission_id: str):
    """WebSocket stream for real-time mission execution progress."""
    await websocket.accept()
    try:
        while True:
            prog = MissionExecutionService.get_progress(mission_id)
            if prog:
                await websocket.send_json({
                    "schema_version": "1.0.0-s7",
                    "timestamp": "2026-08-31T00:00:00Z",
                    "mission_id": mission_id,
                    "event_type": "mission.progress",
                    "mission_state": prog.model_dump(),
                })
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
