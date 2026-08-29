"""Incident retention policy engine, cold storage archival service, and audit purge execution."""

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import os
from pathlib import Path
from typing import Any, Protocol
from uuid import uuid4

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models.incident import Incident, IncidentStatus
from app.models.incident_event import IncidentEvent
from app.models.incident_retention import (
    IncidentArchive,
    IncidentArchivalState,
    IncidentRetentionHold,
    IncidentRetentionPolicy,
)
from app.schemas.incidents import (
    ArchiveIncidentsRequest,
    ArchiveIncidentsResponse,
    ArchiveRecordMetadata,
    PurgeIncidentsRequest,
    PurgeIncidentsResponse,
    PurgePreviewRecord,
    PurgePreviewResponse,
    RetentionEvaluationRecord,
    RetentionEvaluationResponse,
    RetentionPolicyResponse,
    RetentionPolicyUpdateRequest,
)
from app.services.audit import AuditService
from app.services.incident_export import IncidentExportService
from app.services.pdf_generator import generate_incident_pdf_report


class IncidentArchiveStore(Protocol):
    """Cold storage store abstraction interface."""

    def archive(self, archive_number: str, payload_bytes: bytes, archive_format: str) -> str:
        ...

    def retrieve(self, archive_number: str) -> bytes:
        ...

    def verify(self, archive_number: str, expected_sha256: str) -> bool:
        ...

    def exists(self, archive_number: str) -> bool:
        ...

    def delete(self, archive_number: str) -> bool:
        ...


class LocalFileArchiveStore:
    """Safe local cold-storage adapter storing binary archive packages under data/archives/."""

    provider_name: str = "LOCAL"

    def __init__(self, base_dir: str = "data/archives"):
        self.base_dir = Path(base_dir)
        if not self.base_dir.exists():
            self.base_dir.mkdir(parents=True, exist_ok=True)

    def archive(self, archive_number: str, payload_bytes: bytes, archive_format: str) -> str:
        ext = "pdf" if archive_format.upper() == "PDF" else "json"
        file_path = self.base_dir / f"{archive_number}.{ext}"
        with open(file_path, "wb") as f:
            f.write(payload_bytes)
        return str(file_path.absolute())

    def retrieve(self, archive_number: str) -> bytes:
        for ext in ["pdf", "json", "pkg"]:
            file_path = self.base_dir / f"{archive_number}.{ext}"
            if file_path.exists():
                with open(file_path, "rb") as f:
                    return f.read()
        raise FileNotFoundError(f"Archive payload for {archive_number} not found in cold storage")

    def verify(self, archive_number: str, expected_sha256: str) -> bool:
        try:
            bytes_data = self.retrieve(archive_number)
            computed_sha = hashlib.sha256(bytes_data).hexdigest()
            return computed_sha == expected_sha256
        except Exception:
            return False

    def exists(self, archive_number: str) -> bool:
        for ext in ["pdf", "json", "pkg"]:
            if (self.base_dir / f"{archive_number}.{ext}").exists():
                return True
        return False

    def delete(self, archive_number: str) -> bool:
        for ext in ["pdf", "json", "pkg"]:
            file_path = self.base_dir / f"{archive_number}.{ext}"
            if file_path.exists():
                file_path.unlink()
                return True
        return False


class IncidentRetentionService:
    """Production retention policy evaluation, archival lifecycle, and safe purge execution engine."""

    def __init__(self, db: Session, store: IncidentArchiveStore | None = None):
        self.db = db
        if store is None:
            from app.services.archive_store_factory import get_archive_store
            store = get_archive_store()
        self.store = store

    def get_or_create_policy(self) -> IncidentRetentionPolicy:
        stmt = select(IncidentRetentionPolicy).where(IncidentRetentionPolicy.enabled.is_(True)).order_by(IncidentRetentionPolicy.created_at.asc())
        policy = self.db.scalar(stmt)
        if not policy:
            now = datetime.now(UTC).replace(tzinfo=None)
            policy = IncidentRetentionPolicy(
                id=str(uuid4()),
                policy_name="DEFAULT_POLICY",
                description="Default AeroGuard Compliance Retention Policy",
                enabled=True,
                incident_retention_days=90,
                export_retention_days=180,
                minimum_archive_age_days=30,
                minimum_purge_age_days=180,
                require_archive_before_purge=True,
                require_supervisor_approval=True,
                dry_run_by_default=True,
                created_at=now,
                updated_at=now,
            )
            self.db.add(policy)
            self.db.commit()
            self.db.refresh(policy)
        return policy

    def update_policy(self, actor_user_id: str, request: RetentionPolicyUpdateRequest) -> IncidentRetentionPolicy:
        policy = self.get_or_create_policy()
        now = datetime.now(UTC).replace(tzinfo=None)

        if request.incident_retention_days is not None:
            policy.incident_retention_days = request.incident_retention_days
        if request.export_retention_days is not None:
            policy.export_retention_days = request.export_retention_days
        if request.minimum_archive_age_days is not None:
            policy.minimum_archive_age_days = request.minimum_archive_age_days
        if request.minimum_purge_age_days is not None:
            policy.minimum_purge_age_days = request.minimum_purge_age_days
        if request.require_archive_before_purge is not None:
            policy.require_archive_before_purge = request.require_archive_before_purge
        if request.require_supervisor_approval is not None:
            policy.require_supervisor_approval = request.require_supervisor_approval
        if request.dry_run_by_default is not None:
            policy.dry_run_by_default = request.dry_run_by_default

        policy.updated_by = actor_user_id
        policy.updated_at = now
        self.db.commit()
        self.db.refresh(policy)

        AuditService(self.db).record_event(
            event_type="INCIDENT_RETENTION_POLICY_CHANGED",
            action="POLICY_UPDATE",
            result="SUCCESS",
            actor_user_id=actor_user_id,
            target_type="retention_policy",
            target_id=policy.id,
            metadata={"policy_name": policy.policy_name},
        )
        return policy

    def place_hold(self, actor_user_id: str, incident_id: str, reason: str) -> IncidentRetentionHold:
        inc = self.db.scalar(select(Incident).where(Incident.id == incident_id))
        if not inc:
            raise HTTPException(status_code=404, detail="Incident record not found")

        now = datetime.now(UTC).replace(tzinfo=None)
        hold = IncidentRetentionHold(
            id=str(uuid4()),
            incident_id=incident_id,
            reason=reason,
            active=True,
            placed_by=actor_user_id,
            placed_at=now,
        )
        self.db.add(hold)
        self.db.commit()
        self.db.refresh(hold)

        AuditService(self.db).record_event(
            event_type="INCIDENT_RETENTION_HOLD_PLACED",
            action="HOLD_PLACE",
            result="SUCCESS",
            actor_user_id=actor_user_id,
            target_type="incident",
            target_id=incident_id,
            metadata={"hold_id": hold.id, "reason": reason},
        )
        return hold

    def release_hold(self, actor_user_id: str, hold_id: str) -> IncidentRetentionHold:
        hold = self.db.scalar(select(IncidentRetentionHold).where(IncidentRetentionHold.id == hold_id))
        if not hold or not hold.active:
            raise HTTPException(status_code=404, detail="Active retention hold not found")

        now = datetime.now(UTC).replace(tzinfo=None)
        hold.active = False
        hold.released_by = actor_user_id
        hold.released_at = now
        self.db.commit()
        self.db.refresh(hold)

        AuditService(self.db).record_event(
            event_type="INCIDENT_RETENTION_HOLD_RELEASED",
            action="HOLD_RELEASE",
            result="SUCCESS",
            actor_user_id=actor_user_id,
            target_type="incident",
            target_id=hold.incident_id,
            metadata={"hold_id": hold.id},
        )
        return hold

    def evaluate_retention(self, dry_run: bool = True) -> RetentionEvaluationResponse:
        policy = self.get_or_create_policy()
        now = datetime.now(UTC).replace(tzinfo=None)

        incidents = list(self.db.scalars(select(Incident).options(selectinload(Incident.events)).order_by(Incident.created_at.asc())).all())

        # Load active holds mapping
        active_holds = self.db.scalars(
            select(IncidentRetentionHold).where(IncidentRetentionHold.active.is_(True))
        ).all()
        held_incident_ids = {h.incident_id for h in active_holds}

        # Load existing archives mapping
        archives = self.db.scalars(select(IncidentArchive)).all()
        archived_incident_ids = {a.incident_id for a in archives}

        records: list[RetentionEvaluationRecord] = []
        eligible_archive_cnt = 0
        already_archived_cnt = 0
        eligible_purge_cnt = 0
        blocked_hold_cnt = 0
        blocked_active_cnt = 0
        blocked_min_age_cnt = 0
        blocked_missing_archive_cnt = 0

        for inc in incidents:
            age_days = (now - inc.created_at).total_seconds() / 86400.0
            is_terminal = inc.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
            has_hold = inc.id in held_incident_ids
            is_archived = inc.id in archived_incident_ids or inc.archival_state == IncidentArchivalState.ARCHIVED

            if is_archived:
                already_archived_cnt += 1

            blocking_reasons = []

            # Rule 1 & 2: Terminal State Check
            if not is_terminal:
                blocking_reasons.append(f"Incident is in non-terminal state ({inc.status})")
                blocked_active_cnt += 1

            # Rule 5 & 6: Active Retention Hold Check
            if has_hold:
                blocking_reasons.append("Active compliance/legal retention hold placed on incident")
                blocked_hold_cnt += 1

            # Rule 3: Archive Age Check
            can_archive = is_terminal and not has_hold and age_days >= policy.minimum_archive_age_days and not is_archived

            if age_days < policy.minimum_archive_age_days and not is_archived:
                blocking_reasons.append(f"Age ({age_days:.1f}d) is below minimum archive threshold ({policy.minimum_archive_age_days}d)")
                blocked_min_age_cnt += 1

            if can_archive:
                eligible_archive_cnt += 1

            # Purge Eligibility Rules
            can_purge = False
            if is_terminal and not has_hold and age_days >= policy.minimum_purge_age_days:
                if policy.require_archive_before_purge and not is_archived:
                    blocking_reasons.append("Policy requires incident to be archived prior to purge")
                    blocked_missing_archive_cnt += 1
                else:
                    can_purge = True
                    eligible_purge_cnt += 1

            records.append(
                RetentionEvaluationRecord(
                    incident_id=inc.id,
                    incident_number=inc.incident_number,
                    status=inc.status,
                    archival_state=inc.archival_state,
                    age_days=round(age_days, 1),
                    is_terminal=is_terminal,
                    has_active_hold=has_hold,
                    eligible_for_archive=can_archive,
                    eligible_for_purge=can_purge,
                    blocking_reasons=blocking_reasons,
                )
            )

        AuditService(self.db).record_event(
            event_type="INCIDENT_ARCHIVE_ELIGIBILITY_EVALUATED",
            action="RETENTION_EVALUATE",
            result="SUCCESS",
            actor_user_id=None,
            target_type="retention_policy",
            target_id=policy.id,
            metadata={
                "total_evaluated": len(incidents),
                "eligible_archive": eligible_archive_cnt,
                "eligible_purge": eligible_purge_cnt,
            },
        )

        return RetentionEvaluationResponse(
            policy=RetentionPolicyResponse.model_validate(policy),
            evaluated_at=now,
            dry_run=dry_run,
            total_evaluated=len(incidents),
            eligible_for_archive=eligible_archive_cnt,
            already_archived=already_archived_cnt,
            eligible_for_purge=eligible_purge_cnt,
            blocked_by_hold=blocked_hold_cnt,
            blocked_by_active_status=blocked_active_cnt,
            blocked_by_minimum_age=blocked_min_age_cnt,
            blocked_by_missing_archive=blocked_missing_archive_cnt,
            sample_records=records[:50],
        )

    def archive_incidents(
        self,
        actor_user_id: str,
        request: ArchiveIncidentsRequest,
    ) -> ArchiveIncidentsResponse:
        policy = self.get_or_create_policy()
        now = datetime.now(UTC).replace(tzinfo=None)

        # Select incidents to archive
        stmt = select(Incident).options(selectinload(Incident.events))
        if request.incident_ids:
            stmt = stmt.where(Incident.id.in_(request.incident_ids))

        incidents = list(self.db.scalars(stmt).unique().all())
        if not incidents:
            return ArchiveIncidentsResponse(message="No matching incidents found for archival.", archived_count=0, archives=[])

        # Active holds
        active_holds = self.db.scalars(select(IncidentRetentionHold).where(IncidentRetentionHold.active.is_(True))).all()
        held_ids = {h.incident_id for h in active_holds}

        archived_records: list[ArchiveRecordMetadata] = []

        for inc in incidents:
            # Check eligibility
            if inc.status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                continue
            if inc.id in held_ids:
                continue

            # Check if already archived
            existing = self.db.scalar(select(IncidentArchive).where(IncidentArchive.incident_id == inc.id))
            if existing:
                archived_records.append(ArchiveRecordMetadata.model_validate(existing))
                continue

            # Serialize payload
            archive_format = request.archive_format.upper()
            if archive_format == "PDF":
                export_num = f"ARC-PDF-{inc.incident_number}"
                payload_bytes = generate_incident_pdf_report(export_num, actor_user_id, now, {}, [inc])
                payload_str = base64.b64encode(payload_bytes).decode("ascii")
            else:
                export_num = f"ARC-JSON-{inc.incident_number}"
                export_service = IncidentExportService(self.db)
                payload_str = export_service._generate_json_payload(export_num, actor_user_id, now, {}, [inc])
                payload_bytes = payload_str.encode("utf-8")

            sha256_checksum = hashlib.sha256(payload_bytes).hexdigest()
            file_size_bytes = len(payload_bytes)

            # Store payload via ArchiveStore abstraction
            storage_location = self.store.archive(export_num, payload_bytes, archive_format)
            provider_name = getattr(self.store, "provider_name", None) or ("S3" if "s3://" in str(storage_location) else "LOCAL")

            archive = IncidentArchive(
                id=str(uuid4()),
                archive_number=export_num,
                incident_id=inc.id,
                policy_id=policy.id,
                sha256_checksum=sha256_checksum,
                file_size_bytes=file_size_bytes,
                archive_format=archive_format,
                payload_data=payload_str,
                storage_provider=provider_name,
                storage_location=storage_location,
                archived_at=now,
                archived_by=actor_user_id,
                verified_at=now,
            )
            self.db.add(archive)

            # Update Incident Archival State
            inc.archival_state = IncidentArchivalState.ARCHIVED
            inc.archived_at = now

            archived_records.append(ArchiveRecordMetadata.model_validate(archive))

            AuditService(self.db).record_event(
                event_type="INCIDENT_ARCHIVED",
                action="ARCHIVE_EXECUTE",
                result="SUCCESS",
                actor_user_id=actor_user_id,
                target_type="incident",
                target_id=inc.id,
                metadata={
                    "archive_number": archive.archive_number,
                    "sha256_checksum": sha256_checksum,
                    "file_size_bytes": file_size_bytes,
                    "storage_provider": provider_name,
                },
            )

        self.db.commit()

        return ArchiveIncidentsResponse(
            message=f"Successfully archived {len(archived_records)} incident records.",
            archived_count=len(archived_records),
            archives=archived_records,
        )

    def purge_incidents(
        self,
        actor_user_id: str,
        request: PurgeIncidentsRequest,
    ) -> PurgeIncidentsResponse:
        policy = self.get_or_create_policy()
        now = datetime.now(UTC).replace(tzinfo=None)

        # Handle Dry-Run / Preview Mode (When confirm is False)
        if not request.confirm:
            eval_res = self.evaluate_retention(dry_run=True)
            preview_records = []

            for r in eval_res.sample_records:
                if request.incident_ids and r.incident_id not in request.incident_ids:
                    continue
                preview_records.append(
                    PurgePreviewRecord(
                        incident_id=r.incident_id,
                        incident_number=r.incident_number,
                        will_be_purged=r.eligible_for_purge,
                        blocking_reasons=r.blocking_reasons,
                    )
                )

            eligible_cnt = sum(1 for p in preview_records if p.will_be_purged)
            blocked_cnt = len(preview_records) - eligible_cnt

            return PurgeIncidentsResponse(
                message=f"Dry-run purge evaluation complete. {eligible_cnt} records eligible for purge.",
                dry_run=True,
                purged_count=0,
                purged_incident_ids=[],
            )

        # EXPLICIT PURGE EXECUTION (confirm === True)
        stmt = select(Incident).options(selectinload(Incident.events))
        if request.incident_ids:
            stmt = stmt.where(Incident.id.in_(request.incident_ids))

        incidents = list(self.db.scalars(stmt).unique().all())
        active_holds = self.db.scalars(select(IncidentRetentionHold).where(IncidentRetentionHold.active.is_(True))).all()
        held_ids = {h.incident_id for h in active_holds}

        purged_ids: list[str] = []

        for inc in incidents:
            age_days = (now - inc.created_at).total_seconds() / 86400.0
            is_terminal = inc.status in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED)
            has_hold = inc.id in held_ids
            archive = self.db.scalar(select(IncidentArchive).where(IncidentArchive.incident_id == inc.id))
            is_archived = archive is not None or inc.archival_state == IncidentArchivalState.ARCHIVED

            # Strict Safety Check Rules 1-10
            if not is_terminal:
                continue
            if has_hold:
                continue
            if age_days < policy.minimum_purge_age_days:
                continue
            if policy.require_archive_before_purge and not is_archived:
                continue

            # Verify Archive Integrity before purge if archive exists
            if archive:
                verified = self.store.verify(archive.archive_number, archive.sha256_checksum)
                if not verified:
                    AuditService(self.db).record_event(
                        event_type="INCIDENT_ARCHIVE_VERIFICATION_FAILED",
                        action="ARCHIVE_VERIFY",
                        result="FAILURE",
                        actor_user_id=actor_user_id,
                        target_type="incident",
                        target_id=inc.id,
                        metadata={"archive_number": archive.archive_number},
                    )
                    continue

            # Execute Deletion of Incident Events & Record
            for evt in getattr(inc, "events", []) or []:
                self.db.delete(evt)

            self.db.delete(inc)
            purged_ids.append(inc.id)

        self.db.commit()

        audit_evt = AuditService(self.db).record_event(
            event_type="INCIDENT_PURGED",
            action="PURGE_EXECUTE",
            result="SUCCESS",
            actor_user_id=actor_user_id,
            target_type="incident_retention",
            target_id=policy.id,
            metadata={
                "purged_count": len(purged_ids),
                "purged_incident_ids": purged_ids,
            },
        )

        return PurgeIncidentsResponse(
            message=f"Successfully purged {len(purged_ids)} incident records.",
            dry_run=False,
            purged_count=len(purged_ids),
            purged_incident_ids=purged_ids,
            audit_event_id=audit_evt.id if audit_evt else None,
        )
