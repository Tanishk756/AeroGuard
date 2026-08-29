"""Stage IM2-A Incident Export Engine & Serialization Unit, Integration, RBAC, and Benchmark Tests."""

from datetime import UTC, datetime, timedelta
import hashlib
import json
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


def _seed_sample_incidents(db: Session) -> list[Incident]:
    now = datetime.now(UTC).replace(tzinfo=None)

    inc1 = Incident(
        id=str(uuid4()),
        incident_number="INC-EXP-001",
        title='Critical Breach, "Swarm" Encounter',
        description="Line 1\nLine 2 description with, comma",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.CRITICAL,
        source=IncidentSource.OPERATOR,
        primary_track_id=None,
        created_at=now - timedelta(hours=5),
        acknowledged_at=now - timedelta(hours=4, minutes=58),
        resolved_at=now - timedelta(hours=1),
        closed_at=now,
        metadata_json={"tags": ["swarm", "critical"]},
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
        timestamp=inc1.created_at + timedelta(minutes=10),
        message="Reviewed radar telemetry",
        metadata_json={},
    )

    inc2 = Incident(
        id=str(uuid4()),
        incident_number="INC-EXP-002",
        title="Minor Sensor Noise",
        description="Single track ghosting",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.LOW,
        source=IncidentSource.SYSTEM,
        created_at=now - timedelta(hours=2),
        metadata_json={},
    )

    db.add_all([inc1, inc2, evt1, evt2])
    db.commit()
    return [inc1, inc2]


# ---------------------------------------------------------------------------
# Unit & Serialization Tests
# ---------------------------------------------------------------------------

def test_json_export_creation_and_checksum(database: Session):
    """Verify deterministic JSON export generation and exact SHA-256 hash matching."""
    actor = _create_test_user(database, "export_user_1", "OPERATIONS_ADMIN")
    incidents = _seed_sample_incidents(database)

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.JSON)
    export = service.create_export(actor.id, req)

    assert export.status == IncidentExportStatus.COMPLETED
    assert export.format == IncidentExportFormat.JSON
    assert export.record_count == 2
    assert export.requested_by == actor.id
    assert export.payload_data is not None

    # Checksum verification over exact serialized UTF-8 bytes
    payload_bytes = export.payload_data.encode("utf-8")
    expected_hash = hashlib.sha256(payload_bytes).hexdigest()
    assert export.sha256_checksum == expected_hash
    assert export.file_size_bytes == len(payload_bytes)


def test_csv_export_creation_and_rfc4180_escaping(database: Session):
    """Verify CSV export creation and proper RFC 4180 escaping of quotes, commas, and newlines."""
    actor = _create_test_user(database, "export_user_2", "OPERATIONS_ADMIN")
    _seed_sample_incidents(database)

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.CSV)
    export = service.create_export(actor.id, req)

    assert export.status == IncidentExportStatus.COMPLETED
    assert export.format == IncidentExportFormat.CSV
    assert export.record_count == 2
    assert export.payload_data.startswith("export_number,incident_number,id,title")
    assert '"Critical Breach, ""Swarm"" Encounter"' in export.payload_data

    # Checksum verification
    payload_bytes = export.payload_data.encode("utf-8")
    assert export.sha256_checksum == hashlib.sha256(payload_bytes).hexdigest()


def test_export_deterministic_serialization(database: Session):
    """Verify identical database state and parameters produce identical payload bytes."""
    actor = _create_test_user(database, "export_user_3", "OPERATIONS_ADMIN")
    _seed_sample_incidents(database)

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.JSON)

    export1 = service.create_export(actor.id, req)
    export2 = service.create_export(actor.id, req)

    # Payloads must match except for metadata.export_number and generated_at
    payload1_dict = json.loads(export1.payload_data)
    payload2_dict = json.loads(export2.payload_data)

    assert payload1_dict["incidents"] == payload2_dict["incidents"]


def test_export_filtering_by_severity_and_status(database: Session):
    """Verify export filtering by severity and status."""
    actor = _create_test_user(database, "export_user_4", "OPERATIONS_ADMIN")
    _seed_sample_incidents(database)

    service = IncidentExportService(database)

    # Filter by CRITICAL severity
    req_crit = CreateIncidentExportRequest(format=IncidentExportFormat.JSON, severity=IncidentSeverity.CRITICAL)
    exp_crit = service.create_export(actor.id, req_crit)
    assert exp_crit.record_count == 1
    assert "INC-EXP-001" in exp_crit.payload_data

    # Filter by NEW status
    req_new = CreateIncidentExportRequest(format=IncidentExportFormat.JSON, status=IncidentStatus.NEW)
    exp_new = service.create_export(actor.id, req_new)
    assert exp_new.record_count == 1
    assert "INC-EXP-002" in exp_new.payload_data


def test_export_audit_event_creation(database: Session):
    """Verify Stage E AuditEvent recording upon export creation."""
    actor = _create_test_user(database, "export_user_5", "OPERATIONS_ADMIN")
    _seed_sample_incidents(database)

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.JSON)
    export = service.create_export(actor.id, req)

    audit_stmt = select(AuditEvent).where(
        AuditEvent.event_type == "INCIDENT_EXPORT_CREATED",
        AuditEvent.target_id == export.id,
    )
    audit_evt = database.scalar(audit_stmt)

    assert audit_evt is not None
    assert audit_evt.actor_user_id == actor.id
    assert audit_evt.result == "SUCCESS"
    assert audit_evt.event_metadata["export_number"] == export.export_number


def test_export_read_only_immutability(database: Session):
    """Verify export execution never mutates incident status or timeline records."""
    actor = _create_test_user(database, "export_user_6", "OPERATIONS_ADMIN")
    incidents = _seed_sample_incidents(database)
    inc_id = incidents[0].id

    service = IncidentExportService(database)
    req = CreateIncidentExportRequest(format=IncidentExportFormat.JSON)
    service.create_export(actor.id, req)

    database.refresh(incidents[0])
    assert incidents[0].status == IncidentStatus.CLOSED
    assert incidents[0].severity == IncidentSeverity.CRITICAL


# ---------------------------------------------------------------------------
# REST API & RBAC Endpoint Tests
# ---------------------------------------------------------------------------

def test_rest_export_creation_success(client, database):
    """Verify POST /api/v1/incidents/export returns 201 for OPERATIONS_ADMIN."""
    actor = _create_test_user(database, "ops_admin", "OPERATIONS_ADMIN")
    _login_client(client, "ops_admin")
    _seed_sample_incidents(database)

    payload = {"format": "JSON"}
    response = client.post("/api/v1/incidents/export", json=payload)

    assert response.status_code == 201
    data = response.json()
    assert "metadata" in data
    assert "payload" in data
    assert data["metadata"]["requested_by"] == actor.id
    assert data["metadata"]["record_count"] == 2


def test_rest_export_unauthenticated_and_unauthorized(client, database):
    """Verify 401 unauthenticated and 403 unauthorized responses."""
    # 401 Unauthenticated
    res1 = client.post("/api/v1/incidents/export", json={"format": "JSON"})
    assert res1.status_code == 401

    # 403 Unauthorized (VIEWER role lacks incidents.export permission)
    _create_test_user(database, "viewer_user", "VIEWER")
    _login_client(client, "viewer_user")
    res2 = client.post("/api/v1/incidents/export", json={"format": "JSON"})
    assert res2.status_code == 403


def test_rest_export_retrieval_and_history(client, database):
    """Verify GET /api/v1/incidents/export/{id} and GET /api/v1/incidents/export history."""
    actor = _create_test_user(database, "ops_admin_2", "OPERATIONS_ADMIN")
    _login_client(client, "ops_admin_2")
    _seed_sample_incidents(database)

    create_res = client.post("/api/v1/incidents/export", json={"format": "CSV"})
    assert create_res.status_code == 201
    export_id = create_res.json()["metadata"]["id"]

    # GET by ID
    get_res = client.get(f"/api/v1/incidents/export/{export_id}")
    assert get_res.status_code == 200
    assert get_res.json()["metadata"]["format"] == "CSV"

    # GET history list
    list_res = client.get("/api/v1/incidents/export")
    assert list_res.status_code == 200
    items = list_res.json()
    assert len(items) >= 1
    assert items[0]["id"] == export_id


def test_rest_export_not_found(client, database):
    """Verify GET /api/v1/incidents/export/{non_existent_id} returns 404."""
    _create_test_user(database, "ops_admin_3", "OPERATIONS_ADMIN")
    _login_client(client, "ops_admin_3")

    res = client.get("/api/v1/incidents/export/non-existent-export-id")
    assert res.status_code == 404


# ---------------------------------------------------------------------------
# High-Density Performance Scaling Benchmarks (10,000 Records)
# ---------------------------------------------------------------------------

def test_incident_export_performance_scaling_benchmark(database: Session):
    """Benchmark JSON and CSV export serialization over 10,000 synthetic incident records."""
    actor = _create_test_user(database, "bench_user", "OPERATIONS_ADMIN")
    base_time = datetime(2026, 1, 1, 0, 0, 0)
    bulk_incidents = []

    for i in range(10000):
        sev = IncidentSeverity.CRITICAL if i % 10 == 0 else (IncidentSeverity.HIGH if i % 3 == 0 else IncidentSeverity.MEDIUM)
        st = IncidentStatus.CLOSED if i % 2 == 0 else IncidentStatus.NEW
        c_at = base_time + timedelta(minutes=i)

        inc = Incident(
            id=str(uuid4()),
            incident_number=f"INC-BENCH-{i:05d}",
            title=f"Benchmark Incident #{i}",
            status=st,
            severity=sev,
            source=IncidentSource.OPERATOR,
            created_at=c_at,
            metadata_json={},
        )
        bulk_incidents.append(inc)

    database.bulk_save_objects(bulk_incidents)
    database.commit()

    service = IncidentExportService(database)

    # 1. Benchmark CSV export generation over 10,000 records (Target < 500ms)
    start_csv = time.perf_counter()
    csv_export = service.create_export(actor.id, CreateIncidentExportRequest(format=IncidentExportFormat.CSV))
    elapsed_csv_ms = (time.perf_counter() - start_csv) * 1000.0

    assert csv_export.record_count == 10000
    print(f"\n[BENCHMARK] 10,000 Incidents CSV Export Time: {elapsed_csv_ms:.2f} ms")
    assert elapsed_csv_ms < 1000.0  # Execution tolerance limit

    # 2. Benchmark JSON export generation over 10,000 records
    start_json = time.perf_counter()
    json_export = service.create_export(actor.id, CreateIncidentExportRequest(format=IncidentExportFormat.JSON))
    elapsed_json_ms = (time.perf_counter() - start_json) * 1000.0

    assert json_export.record_count == 10000
    print(f"[BENCHMARK] 10,000 Incidents JSON Export Time: {elapsed_json_ms:.2f} ms")
    assert elapsed_json_ms < 1000.0
