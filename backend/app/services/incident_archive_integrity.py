"""Stage IM3-D Cloud Archive Integrity Verification & Reconciliation Service."""

from datetime import UTC, datetime
from hashlib import sha256
import logging
import time
from typing import Any
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.incident_retention import (
    IncidentArchive,
    IncidentArchiveIntegrityCheck,
    IntegrityStatus,
)
from app.services.archive_store_factory import get_archive_store
from app.services.audit import AuditService
from app.services.s3_archive_store import S3ArchiveStoreError, S3ObjectNotFoundError

logger = logging.getLogger(__name__)


class IncidentArchiveIntegrityService:
    def __init__(self, db: Session):
        self.db = db
        self.audit_service = AuditService(db)

    def verify_archive(self, archive_id: str, actor_id: str | None = None) -> IncidentArchiveIntegrityCheck:
        """Verify the integrity of a single archived incident record against its storage provider."""
        t0 = time.perf_counter()
        now = datetime.now(UTC).replace(tzinfo=None)

        archive = self.db.scalar(select(IncidentArchive).where(IncidentArchive.id == archive_id))
        if not archive:
            check = IncidentArchiveIntegrityCheck(
                id=str(uuid4()),
                archive_id=archive_id,
                archive_number=f"ARC-UNKNOWN-{archive_id[:8]}",
                status=IntegrityStatus.INVALID_ARCHIVE_METADATA,
                duration_ms=(time.perf_counter() - t0) * 1000.0,
                error_code="ARCHIVE_NOT_FOUND",
                error_message=f"Archive record {archive_id} not found in database",
                checked_at=now,
            )
            self.db.add(check)
            self.db.commit()
            return check

        provider_name = (archive.storage_provider or "LOCAL").upper()
        expected_checksum = archive.sha256_checksum
        expected_size = archive.file_size_bytes

        try:
            store = get_archive_store(provider_name)
        except Exception as exc:
            duration = (time.perf_counter() - t0) * 1000.0
            check = IncidentArchiveIntegrityCheck(
                id=str(uuid4()),
                archive_id=archive.id,
                archive_number=archive.archive_number,
                incident_id=archive.incident_id,
                storage_provider=provider_name,
                storage_location=archive.storage_location,
                status=IntegrityStatus.STORAGE_UNAVAILABLE,
                expected_checksum=expected_checksum,
                expected_size_bytes=expected_size,
                duration_ms=duration,
                error_code="PROVIDER_UNAVAILABLE",
                error_message=str(exc),
                checked_at=now,
            )
            self.db.add(check)
            self.db.commit()

            self.audit_service.record_event(
                event_type="INCIDENT_ARCHIVE_INTEGRITY_MISMATCH_DETECTED",
                action="VERIFY_ARCHIVE_INTEGRITY",
                result="FAILURE",
                actor_user_id=actor_id,
                target_type="incident_archive",
                target_id=archive.id,
                metadata={
                    "archive_number": archive.archive_number,
                    "storage_provider": provider_name,
                    "status": IntegrityStatus.STORAGE_UNAVAILABLE,
                    "error": str(exc),
                },
            )
            return check

        try:
            raw_payload = store.retrieve(archive.archive_number)
            observed_bytes = raw_payload.encode("utf-8") if isinstance(raw_payload, str) else raw_payload
            observed_size = len(observed_bytes)
            observed_checksum = sha256(observed_bytes).hexdigest()

            if observed_checksum == expected_checksum and observed_size == expected_size:
                status = IntegrityStatus.HEALTHY
                error_code = None
                error_message = None
            elif observed_checksum != expected_checksum:
                status = IntegrityStatus.CHECKSUM_MISMATCH
                error_code = "CHECKSUM_MISMATCH"
                error_message = f"Expected checksum {expected_checksum[:12]}..., observed {observed_checksum[:12]}..."
            else:
                status = IntegrityStatus.METADATA_MISMATCH
                error_code = "SIZE_MISMATCH"
                error_message = f"Expected size {expected_size} bytes, observed {observed_size} bytes"

        except (FileNotFoundError, S3ObjectNotFoundError, KeyError) as exc:
            observed_checksum = None
            observed_size = None
            status = IntegrityStatus.OBJECT_MISSING
            error_code = "OBJECT_MISSING"
            error_message = f"Payload object not found in storage: {exc}"
        except Exception as exc:
            observed_checksum = None
            observed_size = None
            status = IntegrityStatus.STORAGE_UNAVAILABLE
            error_code = "STORAGE_ERROR"
            error_message = f"Failed to retrieve payload from storage provider: {exc}"

        duration = (time.perf_counter() - t0) * 1000.0

        # Update verification timestamp on archive record
        archive.verified_at = now

        check = IncidentArchiveIntegrityCheck(
            id=str(uuid4()),
            archive_id=archive.id,
            archive_number=archive.archive_number,
            incident_id=archive.incident_id,
            storage_provider=provider_name,
            storage_location=archive.storage_location,
            status=status,
            expected_checksum=expected_checksum,
            observed_checksum=observed_checksum,
            expected_size_bytes=expected_size,
            observed_size_bytes=observed_size,
            duration_ms=duration,
            error_code=error_code,
            error_message=error_message,
            checked_at=now,
        )
        self.db.add(check)
        try:
            from app.core.telemetry import (
                ARCHIVE_INTEGRITY_CHECKS_TOTAL,
                ARCHIVE_INTEGRITY_FAILURES_TOTAL,
            )
            status_str = "PASS" if status == IntegrityStatus.HEALTHY else "FAIL"
            ARCHIVE_INTEGRITY_CHECKS_TOTAL.labels(provider=provider_name, status=status_str).inc()
            if status != IntegrityStatus.HEALTHY:
                ARCHIVE_INTEGRITY_FAILURES_TOTAL.labels(provider=provider_name).inc()
        except Exception:
            pass
        self.db.commit()

        audit_event_type = (
            "INCIDENT_ARCHIVE_INTEGRITY_CHECKED"
            if status == IntegrityStatus.HEALTHY
            else "INCIDENT_ARCHIVE_INTEGRITY_MISMATCH_DETECTED"
        )
        self.audit_service.record_event(
            event_type=audit_event_type,
            action="VERIFY_ARCHIVE_INTEGRITY",
            result="SUCCESS" if status == IntegrityStatus.HEALTHY else "FAILURE",
            actor_user_id=actor_id,
            target_type="incident_archive",
            target_id=archive.id,
            metadata={
                "archive_number": archive.archive_number,
                "storage_provider": provider_name,
                "status": status,
                "expected_checksum": expected_checksum,
                "observed_checksum": observed_checksum,
                "expected_size_bytes": expected_size,
                "observed_size_bytes": observed_size,
                "duration_ms": duration,
            },
        )

        return check

    def verify_archives(self, limit: int = 100, actor_id: str | None = None) -> list[IncidentArchiveIntegrityCheck]:
        """Execute bounded batch verification across pending/oldest archive records."""
        safe_limit = min(max(1, limit), 500)
        archives = list(
            self.db.scalars(
                select(IncidentArchive)
                .order_by(IncidentArchive.verified_at.asc().nullsfirst())
                .limit(safe_limit)
            )
        )

        results: list[IncidentArchiveIntegrityCheck] = []
        for arc in archives:
            res = self.verify_archive(arc.id, actor_id=actor_id)
            results.append(res)

        return results

    def detect_orphans(self, storage_provider: str = "LOCAL", actor_id: str | None = None) -> list[IncidentArchiveIntegrityCheck]:
        """Detect orphaned storage objects that have no corresponding database IncidentArchive record."""
        now = datetime.now(UTC).replace(tzinfo=None)
        provider_name = storage_provider.upper()
        orphans: list[IncidentArchiveIntegrityCheck] = []

        try:
            store = get_archive_store(provider_name)
        except Exception as exc:
            logger.warning("Provider %s unavailable for orphan detection: %s", provider_name, exc)
            return []

        # Local filesystem orphan detection
        if provider_name == "LOCAL" and hasattr(store, "base_dir"):
            base_dir = store.base_dir
            if base_dir.exists():
                db_archive_numbers = set(self.db.scalars(select(IncidentArchive.archive_number)))
                for file_path in base_dir.iterdir():
                    if file_path.is_file():
                        file_name = file_path.name
                        arc_num = file_path.stem
                        if arc_num not in db_archive_numbers:
                            bytes_content = file_path.read_bytes()
                            size = len(bytes_content)
                            checksum = sha256(bytes_content).hexdigest()

                            check = IncidentArchiveIntegrityCheck(
                                id=str(uuid4()),
                                archive_id=None,
                                archive_number=arc_num,
                                incident_id=None,
                                storage_provider="LOCAL",
                                storage_location=str(file_path),
                                status=IntegrityStatus.ORPHAN_OBJECT,
                                expected_checksum=None,
                                observed_checksum=checksum,
                                expected_size_bytes=None,
                                observed_size_bytes=size,
                                duration_ms=1.0,
                                error_code="ORPHAN_OBJECT",
                                error_message=f"File {file_name} exists in storage directory but has no database IncidentArchive record",
                                checked_at=now,
                            )
                            self.db.add(check)
                            orphans.append(check)

                            self.audit_service.record_event(
                                event_type="INCIDENT_ARCHIVE_ORPHAN_DETECTED",
                                action="DETECT_ORPHAN_ARCHIVES",
                                result="SUCCESS",
                                actor_user_id=actor_id,
                                target_type="storage_object",
                                target_id=arc_num,
                                metadata={
                                    "archive_number": arc_num,
                                    "storage_provider": "LOCAL",
                                    "observed_size_bytes": size,
                                },
                            )

            self.db.commit()

        return orphans

    def summarize_results(self) -> dict[str, Any]:
        """Aggregate verification summary stats for governance reporting."""
        total_checks = self.db.scalar(select(func.count(IncidentArchiveIntegrityCheck.id))) or 0
        healthy_count = self.db.scalar(
            select(func.count(IncidentArchiveIntegrityCheck.id)).where(IncidentArchiveIntegrityCheck.status == IntegrityStatus.HEALTHY)
        ) or 0
        missing_count = self.db.scalar(
            select(func.count(IncidentArchiveIntegrityCheck.id)).where(IncidentArchiveIntegrityCheck.status == IntegrityStatus.OBJECT_MISSING)
        ) or 0
        mismatch_count = self.db.scalar(
            select(func.count(IncidentArchiveIntegrityCheck.id)).where(
                IncidentArchiveIntegrityCheck.status.in_([IntegrityStatus.CHECKSUM_MISMATCH, IntegrityStatus.METADATA_MISMATCH])
            )
        ) or 0
        orphan_count = self.db.scalar(
            select(func.count(IncidentArchiveIntegrityCheck.id)).where(IncidentArchiveIntegrityCheck.status == IntegrityStatus.ORPHAN_OBJECT)
        ) or 0
        unavailable_count = self.db.scalar(
            select(func.count(IncidentArchiveIntegrityCheck.id)).where(IncidentArchiveIntegrityCheck.status == IntegrityStatus.STORAGE_UNAVAILABLE)
        ) or 0
        last_check_at = self.db.scalar(select(func.max(IncidentArchiveIntegrityCheck.checked_at)))

        return {
            "total_checks": total_checks,
            "healthy_count": healthy_count,
            "missing_count": missing_count,
            "mismatch_count": mismatch_count,
            "orphan_count": orphan_count,
            "unavailable_count": unavailable_count,
            "last_checked_at": last_check_at.isoformat() if last_check_at else None,
        }
