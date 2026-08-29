"""Incident management REST API endpoints and RBAC enforcement."""

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.incident import (
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    InvalidIncidentTransitionError,
)
from app.models.user import User
from app.schemas.incidents import (
    AcknowledgeIncidentRequest,
    AddIncidentNoteRequest,
    AssignIncidentRequest,
    CloseIncidentRequest,
    CreateIncidentRequest,
    DeEscalateIncidentRequest,
    EscalateIncidentRequest,
    IncidentAnalyticsResponse,
    IncidentEventResponse,
    IncidentListResponse,
    IncidentResponse,
    IncidentTimelineResponse,
    LogDefensiveActionRequest,
    ResolveIncidentRequest,
    TriageIncidentRequest,
)
from app.services.incident import (
    IncidentNotFoundError,
    IncidentService,
    InvalidIncidentActionError,
)
from app.services.incident_analytics import IncidentAnalyticsService

router = APIRouter(prefix="/incidents", tags=["incidents"])


@router.post("", response_model=IncidentResponse, status_code=201)
def create_incident(
    payload: CreateIncidentRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.create")),
):
    """Create a new defensive operational incident (initial state NEW)."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.create_incident(
            title=payload.title,
            description=payload.description,
            severity=payload.severity,
            source=payload.source,
            primary_track_id=payload.primary_track_id,
            primary_group_id=payload.primary_group_id,
            originating_alert_id=payload.originating_alert_id,
            originating_intelligence_event_id=payload.originating_intelligence_event_id,
            created_by=actor.id,
            metadata=payload.metadata,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.read")),
    status: IncidentStatus | None = Query(None, description="Filter by status"),
    severity: IncidentSeverity | None = Query(None, description="Filter by severity"),
    assigned_to: str | None = Query(None, max_length=64, description="Filter by assignee"),
    primary_track_id: str | None = Query(None, max_length=64, description="Filter by primary track ID"),
    primary_group_id: str | None = Query(None, max_length=64, description="Filter by swarm/group ID"),
    created_from: datetime | None = Query(None, description="Filter created on or after timestamp"),
    created_to: datetime | None = Query(None, description="Filter created on or before timestamp"),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Items offset"),
):
    """List operational incidents with query filtering and deterministic ordering."""
    if created_from and created_to and created_from > created_to:
        raise HTTPException(status_code=400, detail="created_from must not be after created_to")

    service = IncidentService(db)
    items = service.list_incidents(
        status=status,
        severity=severity,
        assigned_to=assigned_to,
        primary_track_id=primary_track_id,
        primary_group_id=primary_group_id,
        created_from=created_from,
        created_to=created_to,
        limit=limit,
        offset=offset,
    )
    return IncidentListResponse(
        items=[IncidentResponse.model_validate(i) for i in items],
        limit=limit,
        offset=offset,
    )


@router.get("/analytics", response_model=IncidentAnalyticsResponse)
def get_incident_analytics(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.read")),
    start: datetime | None = Query(None, description="Start timestamp of analytics window"),
    end: datetime | None = Query(None, description="End timestamp of analytics window"),
    severity: IncidentSeverity | None = Query(None, description="Filter by severity"),
    status: IncidentStatus | None = Query(None, description="Filter by status"),
    assigned_to: str | None = Query(None, max_length=64, description="Filter by assignee user ID"),
    primary_track_id: str | None = Query(None, max_length=64, description="Filter by primary track ID"),
    primary_group_id: str | None = Query(None, max_length=64, description="Filter by primary group ID"),
    bucket_size: str = Query("day", description="Time series bucket size (hour, day, week)"),
):
    """Retrieve descriptive operational analytics, lifecycle metrics, and trends for incidents."""
    if start and end and start > end:
        raise HTTPException(status_code=400, detail="start must not be after end")

    service = IncidentAnalyticsService(db)
    try:
        return service.get_analytics(
            start_time=start,
            end_time=end,
            severity=severity,
            status=status,
            assigned_to=assigned_to,
            primary_track_id=primary_track_id,
            primary_group_id=primary_group_id,
            bucket_size=bucket_size,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc


@router.get("/{incident_id}", response_model=IncidentResponse)
def get_incident(
    incident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.read")),
):
    """Retrieve detailed state for a specific incident."""
    service = IncidentService(db)
    try:
        return service.get_incident(incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Incident not found") from exc


@router.get("/{incident_id}/timeline", response_model=IncidentTimelineResponse)
def get_incident_timeline(
    incident_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.read")),
):
    """Retrieve the immutable chronological event timeline for an incident."""
    service = IncidentService(db)
    try:
        events = service.get_timeline(incident_id)
        return IncidentTimelineResponse(
            incident_id=incident_id,
            events=[IncidentEventResponse.model_validate(e) for e in events],
            total_count=len(events),
        )
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail="Incident not found") from exc


@router.post("/{incident_id}/acknowledge", response_model=IncidentResponse)
def acknowledge_incident(
    incident_id: str,
    request: Request,
    payload: AcknowledgeIncidentRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.triage")),
):
    """Transition incident status from NEW to ACKNOWLEDGED."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.acknowledge_incident(
            incident_id=incident_id,
            actor_user_id=actor.id,
            message=payload.message if payload else None,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/assign", response_model=IncidentResponse)
def assign_incident(
    incident_id: str,
    payload: AssignIncidentRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.assign")),
):
    """Assign or reassign an incident to a designated user."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.assign_incident(
            incident_id=incident_id,
            assigned_to=payload.assigned_to,
            actor_user_id=actor.id,
            message=payload.message,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/triage", response_model=IncidentResponse)
def triage_incident(
    incident_id: str,
    request: Request,
    payload: TriageIncidentRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.triage")),
):
    """Transition incident status to TRIAGED and record assessment."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.triage_incident(
            incident_id=incident_id,
            actor_user_id=actor.id,
            severity=payload.severity if payload else None,
            notes=payload.notes if payload else None,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/escalate", response_model=IncidentResponse)
def escalate_incident(
    incident_id: str,
    request: Request,
    payload: EscalateIncidentRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.triage")),
):
    """Escalate incident from TRIAGED to ESCALATED status."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.escalate_incident(
            incident_id=incident_id,
            actor_user_id=actor.id,
            reason=payload.reason if payload else None,
            severity=payload.severity if payload else None,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/de-escalate", response_model=IncidentResponse)
def de_escalate_incident(
    incident_id: str,
    request: Request,
    payload: DeEscalateIncidentRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.triage")),
):
    """De-escalate incident from ESCALATED back to TRIAGED or ACKNOWLEDGED."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.de_escalate_incident(
            incident_id=incident_id,
            target_status=payload.target_status if payload else IncidentStatus.TRIAGED,
            actor_user_id=actor.id,
            reason=payload.reason if payload else None,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/resolve", response_model=IncidentResponse)
def resolve_incident(
    incident_id: str,
    request: Request,
    payload: ResolveIncidentRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.manage")),
):
    """Transition incident to RESOLVED status."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.resolve_incident(
            incident_id=incident_id,
            actor_user_id=actor.id,
            resolution_summary=payload.resolution_summary if payload else None,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/close", response_model=IncidentResponse)
def close_incident(
    incident_id: str,
    request: Request,
    payload: CloseIncidentRequest | None = None,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.close")),
):
    """Transition incident to terminal CLOSED status."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        incident = service.close_incident(
            incident_id=incident_id,
            actor_user_id=actor.id,
            closure_notes=payload.closure_notes if payload else None,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(incident)
        return incident
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentTransitionError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/notes", response_model=IncidentEventResponse, status_code=201)
def add_incident_note(
    incident_id: str,
    payload: AddIncidentNoteRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.manage")),
):
    """Append an operator note to the incident timeline."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        event = service.add_note(
            incident_id=incident_id,
            message=payload.message,
            actor_user_id=actor.id,
            metadata=payload.metadata,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(event)
        return event
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise


@router.post("/{incident_id}/actions", response_model=IncidentEventResponse, status_code=201)
def log_defensive_action(
    incident_id: str,
    payload: LogDefensiveActionRequest,
    request: Request,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.manage")),
):
    """Log a procedural defensive action to the incident timeline."""
    service = IncidentService(db)
    correlation_id = getattr(request.state, "correlation_id", None)
    try:
        event = service.log_defensive_action(
            incident_id=incident_id,
            category=payload.category,
            message=payload.message,
            actor_user_id=actor.id,
            metadata=payload.metadata,
            correlation_id=correlation_id,
        )
        db.commit()
        db.refresh(event)
        return event
    except IncidentNotFoundError as exc:
        db.rollback()
        raise HTTPException(status_code=404, detail="Incident not found") from exc
    except InvalidIncidentActionError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except Exception:
        db.rollback()
        raise
