"""Incident management REST API endpoints and RBAC enforcement."""

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.incident import (
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    InvalidIncidentTransitionError,
)
from app.models.incident_retention import IncidentArchive, IncidentArchiveIntegrityCheck
from app.models.user import User
from app.schemas.incidents import (
    AcknowledgeIncidentRequest,
    AddIncidentNoteRequest,
    ArchiveIncidentsRequest,
    ArchiveIncidentsResponse,
    AssignIncidentRequest,
    CloseIncidentRequest,
    CreateIncidentExportRequest,
    CreateIncidentRequest,
    DeEscalateIncidentRequest,
    EscalateIncidentRequest,
    IncidentAnalyticsResponse,
    IncidentEventResponse,
    IncidentExportMetadata,
    IncidentExportResponse,
    IncidentListResponse,
    IncidentResponse,
    IncidentTimelineResponse,
    IntegrityCheckResponse,
    IntegritySummaryResponse,
    IntegrityVerificationBatchResponse,
    LogDefensiveActionRequest,
    PresignedArchiveDownloadResponse,
    PurgeIncidentsRequest,
    PurgeIncidentsResponse,
    ResolveIncidentRequest,
    RetentionEvaluationResponse,
    RetentionHoldCreateRequest,
    RetentionHoldResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
    TriageIncidentRequest,
)
from app.services.archive_store_factory import get_archive_store, get_archive_store_health
from app.services.audit import AuditService
from app.services.incident import (
    IncidentNotFoundError,
    IncidentService,
    InvalidIncidentActionError,
)
from app.services.incident_analytics import IncidentAnalyticsService
from app.services.incident_archive_integrity import IncidentArchiveIntegrityService
from app.services.incident_export import IncidentExportService
from app.services.incident_retention import IncidentRetentionService

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


# ---------------------------------------------------------------------------
# Export Endpoints (IM2-A)
# ---------------------------------------------------------------------------

@router.post("/export", response_model=IncidentExportResponse, status_code=201)
def create_incident_export(
    payload: CreateIncidentExportRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.export")),
):
    """Request a deterministic JSON or CSV export of incident records."""
    service = IncidentExportService(db)
    export = service.create_export(actor_user_id=actor.id, request=payload)
    return IncidentExportResponse(
        metadata=IncidentExportMetadata.model_validate(export),
        payload=export.payload_data,
    )


@router.get("/export", response_model=list[IncidentExportMetadata])
def list_incident_exports(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.export")),
    limit: int = Query(50, ge=1, le=100, description="Max items to return"),
    offset: int = Query(0, ge=0, description="Items offset"),
):
    """Retrieve history of incident exports created by users."""
    service = IncidentExportService(db)
    items, _ = service.list_exports(limit=limit, offset=offset)
    return [IncidentExportMetadata.model_validate(item) for item in items]


@router.get("/export/{export_id}", response_model=IncidentExportResponse)
def get_incident_export(
    export_id: str,
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.export")),
):
    """Retrieve a specific incident export metadata and payload by ID or export number."""
    service = IncidentExportService(db)
    export = service.get_export_by_id(export_id)
    if not export:
        raise HTTPException(status_code=404, detail="Export not found")
    return IncidentExportResponse(
        metadata=IncidentExportMetadata.model_validate(export),
        payload=export.payload_data,
    )


@router.get("/retention/policy", response_model=RetentionPolicyResponse)
def get_retention_policy(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.retention.read")),
):
    """Retrieve current incident retention policy configuration."""
    service = IncidentRetentionService(db)
    return service.get_or_create_policy()


@router.put("/retention/policy", response_model=RetentionPolicyResponse)
def update_retention_policy(
    payload: RetentionPolicyUpdateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.purge")),
):
    """Update incident retention policy configuration (Requires privileged permission)."""
    service = IncidentRetentionService(db)
    return service.update_policy(actor.id, payload)


@router.get("/retention/evaluate", response_model=RetentionEvaluationResponse)
def evaluate_retention_governance(
    dry_run: bool = Query(True, description="Dry-run evaluation producing zero database mutations"),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.retention.read")),
):
    """Evaluate retention, archival, and purge eligibility (Read-only / Zero mutations)."""
    service = IncidentRetentionService(db)
    return service.evaluate_retention(dry_run=dry_run)


@router.get("/retention/storage/health")
def get_retention_storage_health(
    _: User = Depends(require_permission("incidents.retention.read")),
):
    """Retrieve non-destructive storage provider health status (LOCAL vs S3)."""
    return get_archive_store_health()


@router.post("/retention/holds", response_model=RetentionHoldResponse)
def place_retention_hold(
    payload: RetentionHoldCreateRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.archive")),
):
    """Place compliance/legal retention hold on an incident to block purge operations."""
    service = IncidentRetentionService(db)
    return service.place_hold(actor.id, payload.incident_id, payload.reason)


@router.delete("/retention/holds/{hold_id}", response_model=RetentionHoldResponse)
def release_retention_hold(
    hold_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.archive")),
):
    """Release active compliance/legal retention hold on an incident."""
    service = IncidentRetentionService(db)
    return service.release_hold(actor.id, hold_id)


@router.post("/retention/archive", response_model=ArchiveIncidentsResponse)
def archive_incidents(
    payload: ArchiveIncidentsRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.archive")),
):
    """Explicitly archive eligible incident records to cold storage."""
    service = IncidentRetentionService(db)
    return service.archive_incidents(actor.id, payload)


@router.get("/retention/archives/{archive_id}/download-url", response_model=PresignedArchiveDownloadResponse)
def get_archive_download_url(
    archive_id: str,
    expires_in_seconds: int = Query(300, ge=60, le=900, description="Expiration TTL in seconds (60s - 900s)"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.retention.read")),
):
    """Generate a short-lived presigned S3 download URL for an authorized incident archive."""
    archive = db.scalar(select(IncidentArchive).where(IncidentArchive.id == archive_id))
    if not archive:
        raise HTTPException(status_code=404, detail="Incident archive record not found")

    provider = (archive.storage_provider or "LOCAL").upper()
    if provider != "S3":
        raise HTTPException(
            status_code=400,
            detail=f"Presigned download URLs are only available for S3-backed archives. Current storage provider is {provider}.",
        )

    store = get_archive_store("S3")
    try:
        url = store.generate_presigned_url(archive.archive_number, expires_in_seconds=expires_in_seconds)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Failed to generate S3 presigned URL: {exc}") from exc

    now = datetime.now(UTC).replace(tzinfo=None)
    expires_at = now + timedelta(seconds=expires_in_seconds)
    archive.presigned_url_expires_at = expires_at
    db.commit()

    AuditService(db).record_event(
        event_type="INCIDENT_ARCHIVE_DOWNLOAD_URL_ISSUED",
        action="GENERATE_DOWNLOAD_URL",
        result="SUCCESS",
        actor_user_id=actor.id,
        target_type="incident_archive",
        target_id=archive.id,
        metadata={
            "archive_number": archive.archive_number,
            "storage_provider": provider,
            "expires_in_seconds": expires_in_seconds,
        },
    )

    return PresignedArchiveDownloadResponse(
        url=url,
        expires_at=expires_at,
        expires_in_seconds=expires_in_seconds,
        archive_id=archive.id,
        archive_number=archive.archive_number,
        storage_provider=provider,
    )


@router.get("/retention/integrity/summary", response_model=IntegritySummaryResponse)
def get_integrity_summary(
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.retention.read")),
):
    """Retrieve aggregated cold storage archive integrity summary statistics."""
    service = IncidentArchiveIntegrityService(db)
    return service.summarize_results()


@router.get("/retention/integrity", response_model=list[IntegrityCheckResponse])
def get_integrity_checks(
    status: str | None = Query(None, description="Filter by status (HEALTHY, OBJECT_MISSING, CHECKSUM_MISMATCH, etc.)"),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    _: User = Depends(require_permission("incidents.retention.read")),
):
    """Retrieve paginated audit history of archive integrity verification checks."""
    query = select(IncidentArchiveIntegrityCheck).order_by(IncidentArchiveIntegrityCheck.checked_at.desc())
    if status:
        query = query.where(IncidentArchiveIntegrityCheck.status == status.upper())
    return list(db.scalars(query.offset(offset).limit(limit)))


@router.post("/retention/integrity/check", response_model=IntegrityVerificationBatchResponse)
def trigger_batch_integrity_check(
    limit: int = Query(100, ge=1, le=500, description="Maximum number of archive records to verify"),
    detect_local_orphans: bool = Query(True, description="Detect orphaned files in local storage directory"),
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.retention.read")),
):
    """Execute bounded batch integrity verification across cold storage archives."""
    service = IncidentArchiveIntegrityService(db)
    checks = service.verify_archives(limit=limit, actor_id=actor.id)
    if detect_local_orphans:
        orphan_checks = service.detect_orphans(storage_provider="LOCAL", actor_id=actor.id)
        checks.extend(orphan_checks)

    return IntegrityVerificationBatchResponse(
        message=f"Verified {len(checks)} archive storage records successfully",
        verified_count=len(checks),
        checks=[IntegrityCheckResponse.model_validate(c) for c in checks],
    )


@router.post("/retention/archives/{archive_id}/verify", response_model=IntegrityCheckResponse)
def verify_single_archive_integrity(
    archive_id: str,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.retention.read")),
):
    """Verify integrity of a single archived incident record explicitly."""
    service = IncidentArchiveIntegrityService(db)
    check = service.verify_archive(archive_id, actor_id=actor.id)
    return check


@router.post("/retention/purge", response_model=PurgeIncidentsResponse)
def purge_incidents(
    payload: PurgeIncidentsRequest,
    db: Session = Depends(get_db),
    actor: User = Depends(require_permission("incidents.purge")),
):
    """Execute privileged retention purge operation (Requires explicit confirmation confirm=True)."""
    service = IncidentRetentionService(db)
    return service.purge_incidents(actor.id, payload)


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
