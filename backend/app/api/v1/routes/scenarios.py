"""Scenario management and execution REST API endpoints."""

import base64
from datetime import UTC, datetime
import json
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_any_permission, require_permission
from app.models.scenario import Scenario, ScenarioStatus
from app.models.sensor import SensorSourceClass
from app.models.user import User
from app.schemas.scenario import (
    ScenarioCreateRequest,
    ScenarioExecutionStatusResponse,
    ScenarioPage,
    ScenarioResponse,
    ScenarioStepRequest,
    ScenarioUpdateRequest,
)
from app.simulation.service import ScenarioExecutionService

router = APIRouter()


def _decode_cursor(value: str | None) -> tuple[datetime, str] | None:
    if not value:
        return None
    try:
        padded = value + "=" * ((4 - len(value) % 4) % 4)
        decoded = json.loads(base64.urlsafe_b64decode(padded.encode()).decode())
        timestamp = datetime.fromisoformat(decoded[0])
        scenario_id = str(decoded[1])
        if not (1 <= len(scenario_id) <= 64):
            raise ValueError
        return timestamp, scenario_id
    except (ValueError, TypeError, KeyError, IndexError, json.JSONDecodeError, UnicodeError):
        raise HTTPException(status_code=400, detail="Invalid scenario cursor") from None


def _encode_cursor(scenario: Scenario) -> str:
    return base64.urlsafe_b64encode(
        json.dumps([scenario.created_at.isoformat(), scenario.id], separators=(",", ":")).encode()
    ).decode().rstrip("=")


@router.get("/scenarios", response_model=ScenarioPage)
def list_scenarios(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("scenarios.read")),
    status: ScenarioStatus | None = Query(None),
    cursor: str | None = Query(None, max_length=256),
    limit: int = Query(50, ge=1, le=100),
):
    statement = select(Scenario)
    if status:
        statement = statement.where(Scenario.status == status)

    decoded = _decode_cursor(cursor)
    if decoded:
        statement = statement.where(
            or_(
                Scenario.created_at < decoded[0],
                and_(Scenario.created_at == decoded[0], Scenario.id < decoded[1]),
            )
        )

    scenarios = db.scalars(
        statement.order_by(Scenario.created_at.desc(), Scenario.id.desc()).limit(limit + 1)
    ).all()

    next_cursor = _encode_cursor(scenarios[limit - 1]) if len(scenarios) > limit else None
    return ScenarioPage(
        items=[ScenarioResponse.model_validate(s) for s in scenarios[:limit]],
        next_cursor=next_cursor,
    )


@router.post("/scenarios", response_model=ScenarioResponse, status_code=status.HTTP_201_CREATED)
def create_scenario(
    payload: ScenarioCreateRequest,
    db: Session = Depends(get_db),
    user: User = Depends(require_permission("scenarios.create")),
):
    now = datetime.now(UTC).replace(tzinfo=None)
    scenario = Scenario(
        id=str(uuid4()),
        name=payload.name,
        description=payload.description,
        status=ScenarioStatus.READY,
        created_by_user_id=user.id,
        source_class=SensorSourceClass.SIMULATION,
        configuration_metadata=payload.configuration.model_dump(mode="json"),
        created_at=now,
        updated_at=now,
    )
    db.add(scenario)
    db.commit()
    db.refresh(scenario)

    # Initialize execution session
    service = ScenarioExecutionService(db)
    service.prepare_scenario(scenario.id)
    return ScenarioResponse.model_validate(scenario)


@router.get("/scenarios/{scenario_id}", response_model=ScenarioResponse)
def get_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("scenarios.read")),
):
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    return ScenarioResponse.model_validate(scenario)


@router.put("/scenarios/{scenario_id}", response_model=ScenarioResponse)
def update_scenario(
    scenario_id: str,
    payload: ScenarioUpdateRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("scenarios.update")),
):
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    if payload.name is not None:
        scenario.name = payload.name
    if payload.description is not None:
        scenario.description = payload.description
    if payload.configuration is not None:
        scenario.configuration_metadata = payload.configuration.model_dump(mode="json")
    if payload.status is not None:
        scenario.status = payload.status

    scenario.updated_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    db.refresh(scenario)
    return ScenarioResponse.model_validate(scenario)


@router.delete("/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("scenarios.delete")),
):
    scenario = db.get(Scenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")

    db.delete(scenario)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/scenarios/{scenario_id}/prepare", response_model=ScenarioResponse)
def prepare_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.run", "scenarios.execute")),
):
    service = ScenarioExecutionService(db)
    try:
        scenario = service.prepare_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ScenarioResponse.model_validate(scenario)


@router.post("/scenarios/{scenario_id}/start", response_model=ScenarioExecutionStatusResponse)
def start_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.run", "scenarios.execute")),
):
    service = ScenarioExecutionService(db)
    try:
        return service.start_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scenarios/{scenario_id}/pause", response_model=ScenarioExecutionStatusResponse)
def pause_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.run", "scenarios.execute")),
):
    service = ScenarioExecutionService(db)
    try:
        return service.pause_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scenarios/{scenario_id}/resume", response_model=ScenarioExecutionStatusResponse)
def resume_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.run", "scenarios.execute")),
):
    service = ScenarioExecutionService(db)
    try:
        return service.resume_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scenarios/{scenario_id}/step", response_model=ScenarioExecutionStatusResponse)
def step_scenario(
    scenario_id: str,
    payload: ScenarioStepRequest,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.run", "scenarios.execute")),
):
    service = ScenarioExecutionService(db)
    try:
        return service.step(scenario_id, ticks=payload.ticks)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scenarios/{scenario_id}/stop", response_model=ScenarioExecutionStatusResponse)
def stop_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.run", "scenarios.execute")),
):
    service = ScenarioExecutionService(db)
    try:
        return service.stop_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scenarios/{scenario_id}/reset", response_model=ScenarioExecutionStatusResponse)
def reset_scenario(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_any_permission("scenarios.run", "scenarios.execute")),
):
    service = ScenarioExecutionService(db)
    try:
        return service.reset_scenario(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/scenarios/{scenario_id}/status", response_model=ScenarioExecutionStatusResponse)
def get_scenario_status(
    scenario_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("scenarios.read")),
):
    service = ScenarioExecutionService(db)
    try:
        return service.get_status(scenario_id)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
