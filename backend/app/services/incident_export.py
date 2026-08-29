"""Incident export and compliance archival serialization service."""

import base64
import csv
from datetime import UTC, datetime, timedelta
import hashlib
import io
import json
from typing import Any
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.incident_event import DefensiveActionCategory, IncidentEvent, IncidentEventType
from app.models.incident_export import IncidentExport, IncidentExportFormat, IncidentExportStatus
from app.schemas.incidents import CreateIncidentExportRequest
from app.services.audit import AuditService
from app.services.pdf_generator import generate_incident_pdf_report


def format_iso_timestamp(dt: datetime | None) -> str | None:
    if dt is None:
        return None
    return dt.replace(tzinfo=None).isoformat() + "Z"


class IncidentExportService:
    def __init__(self, db: Session):
        self.db = db

    def create_export(
        self,
        actor_user_id: str,
        request: CreateIncidentExportRequest,
    ) -> IncidentExport:
        now = datetime.now(UTC).replace(tzinfo=None)

        # 1. Validate date bounds
        if request.start and request.end and request.start > request.end:
            raise HTTPException(status_code=400, detail="start must not be after end")

        if request.start and request.end:
            duration = request.end - request.start
            if duration > timedelta(days=365):
                raise HTTPException(status_code=422, detail="Date range cannot exceed 365 days")

        # 2. Build filtered SQLAlchemy query over Incidents
        stmt = (
            select(Incident)
            .options(selectinload(Incident.events))
            .order_by(Incident.created_at.asc(), Incident.id.asc())
        )

        if request.start:
            stmt = stmt.where(Incident.created_at >= request.start.replace(tzinfo=None))
        if request.end:
            stmt = stmt.where(Incident.created_at <= request.end.replace(tzinfo=None))
        if request.severity:
            stmt = stmt.where(Incident.severity == request.severity)
        if request.status:
            stmt = stmt.where(Incident.status == request.status)
        if request.assigned_to:
            stmt = stmt.where(Incident.assigned_to == request.assigned_to)
        if request.primary_track_id:
            stmt = stmt.where(Incident.primary_track_id == request.primary_track_id)
        if request.primary_group_id:
            stmt = stmt.where(Incident.primary_group_id == request.primary_group_id)

        incidents = list(self.db.scalars(stmt).unique().all())

        # 3. Generate unique export number
        date_str = now.strftime("%Y%m%d")
        rand_suffix = uuid4().hex[:8].upper()
        export_number = f"EXP-{date_str}-{rand_suffix}"

        filter_params_dict = {
            "format": request.format,
            "start": format_iso_timestamp(request.start),
            "end": format_iso_timestamp(request.end),
            "severity": request.severity,
            "status": request.status,
            "assigned_to": request.assigned_to,
            "primary_track_id": request.primary_track_id,
            "primary_group_id": request.primary_group_id,
        }

        # 4. Serialize payload
        if request.format == IncidentExportFormat.JSON:
            payload_str = self._generate_json_payload(
                export_number=export_number,
                requested_by=actor_user_id,
                generated_at=now,
                filter_params=filter_params_dict,
                incidents=incidents,
            )
            payload_bytes = payload_str.encode("utf-8")
        elif request.format == IncidentExportFormat.CSV:
            payload_str = self._generate_csv_payload(
                export_number=export_number,
                incidents=incidents,
            )
            payload_bytes = payload_str.encode("utf-8")
        elif request.format == IncidentExportFormat.PDF:
            pdf_bytes = generate_incident_pdf_report(
                export_number=export_number,
                requested_by=actor_user_id,
                generated_at=now,
                filter_params=filter_params_dict,
                incidents=incidents,
            )
            payload_bytes = pdf_bytes
            payload_str = base64.b64encode(pdf_bytes).decode("ascii")
        else:
            raise HTTPException(status_code=400, detail=f"Unsupported export format: {request.format}")

        # 5. Compute exact payload size & SHA-256 checksum over exact document bytes
        sha256_checksum = hashlib.sha256(payload_bytes).hexdigest()
        file_size_bytes = len(payload_bytes)

        # 6. Persist IncidentExport metadata & payload
        export = IncidentExport(
            id=str(uuid4()),
            export_number=export_number,
            requested_by=actor_user_id,
            format=request.format,
            status=IncidentExportStatus.COMPLETED,
            record_count=len(incidents),
            file_size_bytes=file_size_bytes,
            sha256_checksum=sha256_checksum,
            created_at=now,
            completed_at=now,
            filter_params_json=filter_params_dict,
            payload_data=payload_str,
        )

        # 7. Record Stage E Audit Event
        AuditService(self.db).record_event(
            event_type="INCIDENT_EXPORT_CREATED",
            action="EXPORT_CREATED",
            result="SUCCESS",
            actor_user_id=actor_user_id,
            target_type="incident_export",
            target_id=export.id,
            metadata={
                "export_number": export.export_number,
                "format": export.format,
                "record_count": export.record_count,
                "file_size_bytes": export.file_size_bytes,
                "sha256_checksum": export.sha256_checksum,
            },
        )

        self.db.add(export)
        self.db.commit()
        self.db.refresh(export)

        return export

    def get_export_by_id(self, export_id: str) -> IncidentExport | None:
        stmt = select(IncidentExport).where(
            (IncidentExport.id == export_id) | (IncidentExport.export_number == export_id)
        )
        return self.db.scalar(stmt)

    def list_exports(
        self,
        requested_by: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[IncidentExport], int]:
        stmt = select(IncidentExport)
        count_stmt = select(func.count(IncidentExport.id))

        if requested_by:
            stmt = stmt.where(IncidentExport.requested_by == requested_by)
            count_stmt = count_stmt.where(IncidentExport.requested_by == requested_by)

        total = self.db.scalar(count_stmt) or 0
        stmt = stmt.order_by(IncidentExport.created_at.desc(), IncidentExport.id.desc()).offset(offset).limit(limit)
        items = list(self.db.scalars(stmt).all())

        return items, total

    def _generate_json_payload(
        self,
        export_number: str,
        requested_by: str,
        generated_at: datetime,
        filter_params: dict[str, Any],
        incidents: list[Incident],
    ) -> str:
        serialized_incidents = []
        for inc in incidents:
            events = getattr(inc, "events", []) or []
            sorted_events = sorted(events, key=lambda e: (e.sequence, e.timestamp))
            events_data = []
            for evt in sorted_events:
                events_data.append({
                    "actor_user_id": evt.actor_user_id,
                    "category": evt.category,
                    "event_type": evt.event_type,
                    "id": evt.id,
                    "message": evt.message,
                    "metadata": evt.metadata_json or {},
                    "new_status": evt.new_status,
                    "previous_status": evt.previous_status,
                    "sequence": evt.sequence,
                    "timestamp": format_iso_timestamp(evt.timestamp),
                })

            serialized_incidents.append({
                "acknowledged_at": format_iso_timestamp(getattr(inc, "acknowledged_at", None)),
                "assigned_at": format_iso_timestamp(getattr(inc, "assigned_at", None)),
                "assigned_to": inc.assigned_to,
                "closed_at": format_iso_timestamp(getattr(inc, "closed_at", None)),
                "created_at": format_iso_timestamp(inc.created_at),
                "description": inc.description,
                "events": events_data,
                "id": inc.id,
                "incident_number": inc.incident_number,
                "metadata": inc.metadata_json or {},
                "originating_alert_id": inc.originating_alert_id,
                "originating_intelligence_event_id": inc.originating_intelligence_event_id,
                "primary_group_id": inc.primary_group_id,
                "primary_track_id": inc.primary_track_id,
                "resolved_at": format_iso_timestamp(getattr(inc, "resolved_at", None)),
                "severity": inc.severity,
                "source": inc.source,
                "status": inc.status,
                "title": inc.title,
                "updated_at": format_iso_timestamp(inc.updated_at),
            })

        payload_obj = {
            "incidents": serialized_incidents,
            "metadata": {
                "export_number": export_number,
                "filter_params": filter_params,
                "format": "JSON",
                "generated_at": format_iso_timestamp(generated_at),
                "record_count": len(incidents),
                "requested_by": requested_by,
            },
        }

        # Deterministic sorting of keys and utf-8 string formatting
        return json.dumps(payload_obj, indent=2, sort_keys=True, ensure_ascii=False)

    def _generate_csv_payload(
        self,
        export_number: str,
        incidents: list[Incident],
    ) -> str:
        output = io.StringIO()
        writer = csv.writer(output, quoting=csv.QUOTE_MINIMAL, lineterminator="\r\n")

        headers = [
            "export_number",
            "incident_number",
            "id",
            "title",
            "status",
            "severity",
            "source",
            "primary_track_id",
            "primary_group_id",
            "assigned_to",
            "created_at",
            "acknowledged_at",
            "assigned_at",
            "resolved_at",
            "closed_at",
            "total_events",
            "logged_actions_count",
        ]
        writer.writerow(headers)

        for inc in incidents:
            events = getattr(inc, "events", []) or []
            events_count = len(events)
            actions_count = sum(1 for e in events if getattr(e, "event_type", None) == IncidentEventType.ACTION_LOGGED) if events_count > 0 else 0

            writer.writerow([
                export_number,
                inc.incident_number,
                inc.id,
                inc.title,
                inc.status,
                inc.severity,
                inc.source,
                inc.primary_track_id or "",
                inc.primary_group_id or "",
                inc.assigned_to or "",
                format_iso_timestamp(inc.created_at) or "",
                format_iso_timestamp(getattr(inc, "acknowledged_at", None)) or "",
                format_iso_timestamp(getattr(inc, "assigned_at", None)) or "",
                format_iso_timestamp(getattr(inc, "resolved_at", None)) or "",
                format_iso_timestamp(getattr(inc, "closed_at", None)) or "",
                events_count,
                actions_count,
            ])

        return output.getvalue()
