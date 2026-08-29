"""Stage IM2-C Incident PDF Report Generation Unit, Integration, RBAC, Structural & Benchmark Tests."""

import base64
from datetime import UTC, datetime, timedelta
import hashlib
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.incident import Incident, IncidentSeverity, IncidentSource, IncidentStatus
from app.models.incident_event import DefensiveActionCategory, IncidentEvent, IncidentEventType
from app.models.incident_export import IncidentExport, IncidentExportFormat, IncidentExportStatus
from app.models.role import Role
from app.models.track import Track, TrackState
from app.models.user import User
from app.schemas.incidents import CreateIncidentExportRequest
from app.services.auth import create_user
from app.services.incident_export import IncidentExportService
from app.services.pdf_generator import generate_incident_pdf_report
from app.services.rbac import seed_rbac


def _create_test_user(db: Session, username: str, role_name: str) -> User:
    seed_rbac(db)
    user = create_user(db, username, username.title(), f"{username}@test.invalid", "test-password-123")
    role = db.scalar(select(Role).where(Role.name == role_name))
    if role:
        user.roles.append(role)
        db.commit()
    return user


def _login_client(client: TestClient, username: str):
    res = client.post("/api/v1/auth/login", json={"identifier": username, "password": "test-password-123"})
    assert res.status_code == 200


def _seed_sample_pdf_incidents(db: Session, actor_id: str) -> list[Incident]:
    now = datetime.now(UTC).replace(tzinfo=None)

    track = Track(
        id="TRK-808",
        state=TrackState.ACTIVE,
        classification="HOSTILE",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=150.0,
        velocity=25.0,
        heading=90.0,
        confidence=0.95,
        source_count=1,
        first_seen_at=now - timedelta(hours=6),
        last_seen_at=now,
    )
    db.add(track)

    inc1 = Incident(
        id=str(uuid4()),
        incident_number="INC-PDF-001",
        title="Critical Radar Anomaly & Perimeter Breach",
        description="Observed high-speed target near Sector 7 geofence perimeter.",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.CRITICAL,
        source=IncidentSource.INTELLIGENCE,
        primary_track_id="TRK-808",
        primary_group_id="GRP-909",
        created_at=now - timedelta(hours=6),
        acknowledged_at=now - timedelta(hours=5, minutes=50),
        resolved_at=now - timedelta(hours=1),
        closed_at=now,
        metadata_json={"tags": ["pdf", "critical"]},
    )
    evt1 = IncidentEvent(
        id=str(uuid4()),
        incident_id=inc1.id,
        sequence=1,
        event_type=IncidentEventType.CREATED,
        timestamp=inc1.created_at,
        new_status=IncidentStatus.NEW,
        metadata_json={},
    )
    evt2 = IncidentEvent(
        id=str(uuid4()),
        incident_id=inc1.id,
        sequence=2,
        event_type=IncidentEventType.ACTION_LOGGED,
        category=DefensiveActionCategory.SENSOR_REVIEW,
        timestamp=inc1.created_at + timedelta(minutes=15),
        message="Correlated primary track TRK-808 with multi-sensor fusion feeds.",
        metadata_json={},
    )

    inc2 = Incident(
        id=str(uuid4()),
        incident_number="INC-PDF-002",
        title="Low Severity Operator Note",
        description="Routine perimeter check.",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
        created_by=actor_id,
        created_at=now - timedelta(hours=2),
        metadata_json={},
    )

    db.add_all([inc1, inc2, evt1, evt2])
    db.commit()
    return [inc1, inc2]


# ---------------------------------------------------------------------------
# PDF Serialization & Structural Validation Tests
# ---------------------------------------------------------------------------

def _extract_pdf_text_bytes(pdf_bytes: bytes) -> bytes:
    import zlib
    chunks = []
    idx = 0
    while True:
        s_idx = pdf_bytes.find(b"stream", idx)
        if s_idx == -1:
            break
        start = s_idx + 6
        if pdf_bytes[start : start + 2] == b"\r\n":
            start += 2
        elif pdf_bytes[start : start + 1] == b"\n":
            start += 1

        e_idx = pdf_bytes.find(b"endstream", start)
        if e_idx == -1:
            break
        compressed = pdf_bytes[start:e_idx].strip()
        try:
            chunks.append(zlib.decompress(compressed))
        except Exception:
            chunks.append(compressed)
        idx = e_idx + 9
    return b"\n".join(chunks)


def test_pdf_export_creation_and_header_signature(database: Session):
    """Verify PDF export creation produces valid %PDF byte signature."""
    actor = _create_test_user(database, "pdf_user_1", "OPERATIONS_ADMIN")
    _seed_sample_pdf_incidents(database, actor.id)

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.PDF)
    export = service.create_export(actor.id, req)

    assert export.status == IncidentExportStatus.COMPLETED
    assert export.format == IncidentExportFormat.PDF
    assert export.record_count == 2
    assert export.payload_data is not None

    # Base64 decode string back to binary PDF bytes
    pdf_bytes = base64.b64decode(export.payload_data)

    # 1. Structural Checks: Valid %PDF file header, catalog, page objects, & EOF marker
    assert pdf_bytes.startswith(b"%PDF")
    assert b"/Type /Catalog" in pdf_bytes
    assert b"/Type /Page" in pdf_bytes
    assert b"ReportLab" in pdf_bytes
    assert pdf_bytes.rstrip().endswith(b"%%EOF")
    assert export.file_size_bytes == len(pdf_bytes)

    # 2. Checksum Check: SHA-256 over exact document bytes
    expected_checksum = hashlib.sha256(pdf_bytes).hexdigest()
    assert export.sha256_checksum == expected_checksum


def test_pdf_export_filtering(database: Session):
    """Verify PDF export filtering by severity and status."""
    actor = _create_test_user(database, "pdf_user_2", "OPERATIONS_ADMIN")
    _seed_sample_pdf_incidents(database, actor.id)

    service = IncidentExportService(database)

    # 1. Filter CRITICAL severity (1 matching incident)
    req_crit = CreateIncidentExportRequest(format=IncidentExportFormat.PDF, severity=IncidentSeverity.CRITICAL)
    exp_crit = service.create_export(actor.id, req_crit)
    assert exp_crit.record_count == 1

    pdf_bytes_crit = base64.b64decode(exp_crit.payload_data)
    assert pdf_bytes_crit.startswith(b"%PDF")
    assert exp_crit.sha256_checksum == hashlib.sha256(pdf_bytes_crit).hexdigest()

    # 2. Filter LOW severity (1 matching incident)
    req_low = CreateIncidentExportRequest(format=IncidentExportFormat.PDF, severity=IncidentSeverity.LOW)
    exp_low = service.create_export(actor.id, req_low)
    assert exp_low.record_count == 1

    pdf_bytes_low = base64.b64decode(exp_low.payload_data)
    assert pdf_bytes_low.startswith(b"%PDF")
    assert exp_low.sha256_checksum == hashlib.sha256(pdf_bytes_low).hexdigest()


def test_pdf_export_empty_dataset_handling(database: Session):
    """Verify PDF generation over zero records creates a valid PDF document."""
    actor = _create_test_user(database, "pdf_user_3", "OPERATIONS_ADMIN")

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.PDF)
    export = service.create_export(actor.id, req)

    assert export.status == IncidentExportStatus.COMPLETED
    assert export.record_count == 0

    pdf_bytes = base64.b64decode(export.payload_data)
    assert pdf_bytes.startswith(b"%PDF")
    assert export.sha256_checksum == hashlib.sha256(pdf_bytes).hexdigest()


def test_pdf_export_audit_event(database: Session):
    """Verify Stage E AuditEvent recording for PDF exports."""
    actor = _create_test_user(database, "pdf_user_4", "OPERATIONS_ADMIN")
    _seed_sample_pdf_incidents(database, actor.id)

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.PDF)
    export = service.create_export(actor.id, req)

    audit_stmt = select(AuditEvent).where(
        AuditEvent.event_type == "INCIDENT_EXPORT_CREATED",
        AuditEvent.target_id == export.id,
    )
    audit_evt = database.scalar(audit_stmt)
    assert audit_evt is not None
    assert audit_evt.event_metadata["format"] == "PDF"


def test_pdf_export_read_only_immutability(database: Session):
    """Verify PDF generation never mutates underlying incident state."""
    actor = _create_test_user(database, "pdf_user_5", "OPERATIONS_ADMIN")
    incidents = _seed_sample_pdf_incidents(database, actor.id)

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.PDF)
    service.create_export(actor.id, req)

    database.refresh(incidents[0])
    assert incidents[0].status == IncidentStatus.CLOSED
    assert incidents[0].severity == IncidentSeverity.CRITICAL


# ---------------------------------------------------------------------------
# REST API & RBAC Endpoint Tests
# ---------------------------------------------------------------------------

def test_rest_pdf_export_success(client, database):
    """Verify POST /api/v1/incidents/export with format=PDF returns 201 for OPERATIONS_ADMIN."""
    actor = _create_test_user(database, "pdf_ops_admin", "OPERATIONS_ADMIN")
    _login_client(client, "pdf_ops_admin")
    _seed_sample_pdf_incidents(database, actor.id)

    response = client.post("/api/v1/incidents/export", json={"format": "PDF"})
    assert response.status_code == 201

    data = response.json()
    assert data["metadata"]["format"] == "PDF"
    assert data["metadata"]["requested_by"] == actor.id
    assert data["payload"] is not None

    # Base64 decode payload & verify header
    pdf_bytes = base64.b64decode(data["payload"])
    assert pdf_bytes.startswith(b"%PDF")


def test_rest_pdf_export_unauthorized(client, database):
    """Verify 403 Forbidden when requesting PDF export without incidents.export permission."""
    _create_test_user(database, "pdf_viewer_user", "VIEWER")
    _login_client(client, "pdf_viewer_user")

    res = client.post("/api/v1/incidents/export", json={"format": "PDF"})
    assert res.status_code == 403


# ---------------------------------------------------------------------------
# Performance Scaling Benchmarks (10, 100, 1,000 Incidents)
# ---------------------------------------------------------------------------

def test_pdf_export_performance_scaling_benchmark(database: Session):
    """Benchmark PDF report rendering across 10, 100, and 1,000 incident records."""
    actor = _create_test_user(database, "pdf_bench_user", "OPERATIONS_ADMIN")
    base_time = datetime(2026, 1, 1, 0, 0, 0)

    # 1. 10 Incidents Benchmark
    incidents_10 = []
    for i in range(10):
        inc = Incident(
            id=str(uuid4()),
            incident_number=f"INC-PDF-10-{i:03d}",
            title=f"10-Count PDF Incident #{i}",
            status=IncidentStatus.NEW,
            severity=IncidentSeverity.HIGH,
            source=IncidentSource.OPERATOR,
            created_at=base_time + timedelta(minutes=i),
            metadata_json={},
        )
        incidents_10.append(inc)

    start_10 = time.perf_counter()
    pdf_bytes_10 = generate_incident_pdf_report("EXP-BENCH-10", actor.id, base_time, {}, incidents_10)
    elapsed_10_ms = (time.perf_counter() - start_10) * 1000.0

    assert pdf_bytes_10.startswith(b"%PDF")
    print(f"\n[BENCHMARK] 10 Incidents PDF Render Time: {elapsed_10_ms:.2f} ms ({len(pdf_bytes_10)} bytes)")
    assert elapsed_10_ms < 500.0

    # 2. 100 Incidents Benchmark
    incidents_100 = []
    for i in range(100):
        inc = Incident(
            id=str(uuid4()),
            incident_number=f"INC-PDF-100-{i:03d}",
            title=f"100-Count PDF Incident #{i}",
            status=IncidentStatus.CLOSED if i % 2 == 0 else IncidentStatus.NEW,
            severity=IncidentSeverity.CRITICAL if i % 5 == 0 else IncidentSeverity.MEDIUM,
            source=IncidentSource.SYSTEM,
            created_at=base_time + timedelta(minutes=i),
            metadata_json={},
        )
        incidents_100.append(inc)

    start_100 = time.perf_counter()
    pdf_bytes_100 = generate_incident_pdf_report("EXP-BENCH-100", actor.id, base_time, {}, incidents_100)
    elapsed_100_ms = (time.perf_counter() - start_100) * 1000.0

    assert pdf_bytes_100.startswith(b"%PDF")
    print(f"[BENCHMARK] 100 Incidents PDF Render Time: {elapsed_100_ms:.2f} ms ({len(pdf_bytes_100)} bytes)")
    assert elapsed_100_ms < 2000.0

    # 3. 1,000 Incidents Benchmark
    incidents_1000 = []
    for i in range(1000):
        inc = Incident(
            id=str(uuid4()),
            incident_number=f"INC-PDF-1000-{i:04d}",
            title=f"1,000-Count PDF Incident #{i}",
            status=IncidentStatus.CLOSED if i % 2 == 0 else IncidentStatus.NEW,
            severity=IncidentSeverity.CRITICAL if i % 10 == 0 else IncidentSeverity.MEDIUM,
            source=IncidentSource.OPERATOR,
            created_at=base_time + timedelta(minutes=i),
            metadata_json={},
        )
        incidents_1000.append(inc)

    start_1000 = time.perf_counter()
    pdf_bytes_1000 = generate_incident_pdf_report("EXP-BENCH-1000", actor.id, base_time, {}, incidents_1000)
    elapsed_1000_ms = (time.perf_counter() - start_1000) * 1000.0

    assert pdf_bytes_1000.startswith(b"%PDF")
    print(f"[BENCHMARK] 1,000 Incidents PDF Render Time: {elapsed_1000_ms:.2f} ms ({len(pdf_bytes_1000)} bytes)")
    assert elapsed_1000_ms < 10000.0
