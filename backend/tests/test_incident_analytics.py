"""Backend unit, integration, RBAC, and performance benchmark test suite for Incident Analytics (Stage IM1-G)."""

from datetime import UTC, datetime, timedelta
import time
from uuid import uuid4

from fastapi.testclient import TestClient
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
)
from app.models.incident_event import (
    DefensiveActionCategory,
    IncidentEvent,
    IncidentEventType,
)
from app.models.role import Role
from app.models.user import User
from app.models.track import Track, TrackState
from app.services.rbac import seed_rbac
from app.services.auth import create_user
from app.services.incident import IncidentService
from app.services.incident_analytics import IncidentAnalyticsService


def _create_test_track(db: Session, track_id: str = "TRK-101") -> Track:
    now = datetime.now(UTC).replace(tzinfo=None)
    trk = Track(
        id=track_id,
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.9,
        source_count=1,
    )
    db.add(trk)
    db.commit()
    return trk


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


# ---------------------------------------------------------------------------
# Unit & Integration Tests
# ---------------------------------------------------------------------------

def test_incident_analytics_empty_dataset(database: Session):
    """Verify safe handling of zero-incident database."""
    service = IncidentAnalyticsService(database)
    res = service.get_analytics()

    assert res.summary.total_incidents == 0
    assert res.summary.active_incidents == 0
    assert res.summary.critical_count == 0
    assert res.severity_distribution[IncidentSeverity.CRITICAL].count == 0
    assert res.severity_distribution[IncidentSeverity.CRITICAL].percentage == 0.0
    assert res.status_distribution[IncidentStatus.NEW].count == 0
    assert res.timing.median_acknowledgement_seconds is None
    assert res.correlations.uncorrelated == 0
    assert res.procedural_actions.total_actions == 0


def test_incident_analytics_summary_and_distributions(database: Session):
    """Verify summary counts and severity/status percentages with real records."""
    _create_test_track(database, "TRK-101")
    service = IncidentService(database)
    now = datetime.now(UTC).replace(tzinfo=None)

    # Incident 1: Critical, CLOSED
    inc1 = service.create_incident(
        title="Critical Swarm Breach",
        severity=IncidentSeverity.CRITICAL,
        primary_track_id="TRK-101",
    )
    service.acknowledge_incident(inc1.id)
    service.triage_incident(inc1.id, severity=IncidentSeverity.CRITICAL)
    service.resolve_incident(inc1.id, resolution_summary="Neutralized")
    service.close_incident(inc1.id)

    # Incident 2: Low, NEW
    inc2 = service.create_incident(
        title="Minor Sensor Drift",
        severity=IncidentSeverity.LOW,
    )

    database.commit()

    analytics_svc = IncidentAnalyticsService(database)
    res = analytics_svc.get_analytics()

    assert res.summary.total_incidents == 2
    assert res.summary.critical_count == 1
    assert res.summary.low_count == 1

    assert res.severity_distribution[IncidentSeverity.CRITICAL].count == 1
    assert res.severity_distribution[IncidentSeverity.CRITICAL].percentage == 50.0
    assert res.severity_distribution[IncidentSeverity.LOW].count == 1
    assert res.severity_distribution[IncidentSeverity.LOW].percentage == 50.0

    assert res.status_distribution[IncidentStatus.CLOSED].count == 1
    assert res.status_distribution[IncidentStatus.NEW].count == 1


def test_incident_analytics_lifecycle_timing(database: Session):
    """Verify exact lifecycle duration calculation without substituting fake zeroes for missing data."""
    now = datetime.now(UTC).replace(tzinfo=None)

    # Create manual incident with explicit timestamps
    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-TIME-001",
        title="Timed Lifecycle Incident",
        status=IncidentStatus.CLOSED,
        severity=IncidentSeverity.HIGH,
        source=IncidentSource.OPERATOR,
        created_at=now - timedelta(minutes=10),
        acknowledged_at=now - timedelta(minutes=8), # 120s ack time
        assigned_at=now - timedelta(minutes=7),      # 180s assign time
        resolved_at=now - timedelta(minutes=2),      # 480s resolve time
        closed_at=now,                               # 600s close time
        metadata_json={},
    )
    database.add(inc)
    database.commit()

    service = IncidentAnalyticsService(database)
    res = service.get_analytics()

    assert res.timing.median_acknowledgement_seconds == 120.0
    assert res.timing.p95_acknowledgement_seconds == 120.0
    assert res.timing.median_assignment_seconds == 180.0
    assert res.timing.median_resolution_seconds == 480.0
    assert res.timing.median_closure_seconds == 600.0
    assert res.timing.sample_counts["acknowledgement"] == 1


def test_incident_analytics_time_series_bucketing(database: Session):
    """Verify hourly, daily, and weekly time series trend bucketing."""
    base = datetime(2026, 8, 29, 10, 0, 0)

    inc1 = Incident(
        id=str(uuid4()),
        incident_number="INC-TS-101",
        title="TS Incident 1",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.MEDIUM,
        created_at=base,
        metadata_json={},
    )
    inc2 = Incident(
        id=str(uuid4()),
        incident_number="INC-TS-102",
        title="TS Incident 2",
        status=IncidentStatus.RESOLVED,
        severity=IncidentSeverity.HIGH,
        created_at=base + timedelta(hours=2),
        resolved_at=base + timedelta(hours=3),
        metadata_json={},
    )
    database.add_all([inc1, inc2])
    database.commit()

    service = IncidentAnalyticsService(database)

    # Hourly buckets
    res_hourly = service.get_analytics(bucket_size="hour")
    assert len(res_hourly.time_series) >= 2
    assert res_hourly.time_series[0].created_count >= 1

    # Daily buckets
    res_daily = service.get_analytics(bucket_size="day")
    assert len(res_daily.time_series) >= 1
    assert res_daily.time_series[0].bucket_start == "2026-08-29"
    assert res_daily.time_series[0].created_count == 2
    assert res_daily.time_series[0].resolved_count == 1


def test_incident_analytics_procedural_action_counts(database: Session):
    """Verify aggregation of logged procedural action categories."""
    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-ACT-001",
        title="Procedural Incident",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.HIGH,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={},
    )
    database.add(inc)
    database.commit()

    evt1 = IncidentEvent(
        id=str(uuid4()),
        incident_id=inc.id,
        sequence=1,
        event_type=IncidentEventType.ACTION_LOGGED,
        category=DefensiveActionCategory.SENSOR_REVIEW,
        timestamp=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={},
    )
    evt2 = IncidentEvent(
        id=str(uuid4()),
        incident_id=inc.id,
        sequence=2,
        event_type=IncidentEventType.ACTION_LOGGED,
        category=DefensiveActionCategory.SENSOR_REVIEW,
        timestamp=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={},
    )
    evt3 = IncidentEvent(
        id=str(uuid4()),
        incident_id=inc.id,
        sequence=3,
        event_type=IncidentEventType.ACTION_LOGGED,
        category=DefensiveActionCategory.SUPERVISOR_ESCALATION,
        timestamp=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={},
    )
    database.add_all([evt1, evt2, evt3])
    database.commit()

    service = IncidentAnalyticsService(database)
    res = service.get_analytics()

    assert res.procedural_actions.total_actions == 3
    assert res.procedural_actions.by_category["SENSOR_REVIEW"] == 2
    assert res.procedural_actions.by_category["SUPERVISOR_ESCALATION"] == 1


def test_incident_analytics_correlations(database: Session):
    """Verify correlation counting for tracks, groups, and uncorrelated incidents."""
    _create_test_track(database, "TRK-999")
    inc_track = Incident(
        id=str(uuid4()),
        incident_number="INC-COR-001",
        title="Track Correlated",
        primary_track_id="TRK-999",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.HIGH,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={},
    )
    inc_group = Incident(
        id=str(uuid4()),
        incident_number="INC-COR-002",
        title="Group Correlated",
        primary_group_id="GRP-888",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.HIGH,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={},
    )
    inc_uncorrelated = Incident(
        id=str(uuid4()),
        incident_number="INC-COR-003",
        title="Uncorrelated System Event",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.LOW,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={},
    )
    database.add_all([inc_track, inc_group, inc_uncorrelated])
    database.commit()

    service = IncidentAnalyticsService(database)
    res = service.get_analytics()

    assert res.correlations.with_primary_track == 1
    assert res.correlations.with_primary_group == 1
    assert res.correlations.uncorrelated == 1
    assert len(res.correlations.top_tracks) == 1
    assert res.correlations.top_tracks[0]["track_id"] == "TRK-999"


def test_incident_analytics_rbac_and_api_endpoints(client, database):
    """Verify REST endpoint GET /api/v1/incidents/analytics returns 200 for authorized users."""
    _create_test_user(database, "admin_user", "OPERATIONS_ADMIN")
    _login_client(client, "admin_user")

    response = client.get("/api/v1/incidents/analytics")

    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "timing" in data
    assert "severity_distribution" in data
    assert "status_distribution" in data
    assert "time_series" in data


def test_incident_analytics_unauthorized_and_unauthenticated(client):
    """Verify 401 unauthenticated requests to analytics endpoint."""
    response = client.get("/api/v1/incidents/analytics")
    assert response.status_code == 401


def test_incident_analytics_invalid_date_range(client, database):
    """Verify 400 error when start timestamp is after end timestamp."""
    _create_test_user(database, "admin_user_2", "OPERATIONS_ADMIN")
    _login_client(client, "admin_user_2")

    params = {
        "start": "2026-08-30T10:00:00Z",
        "end": "2026-08-20T10:00:00Z",
    }
    response = client.get("/api/v1/incidents/analytics", params=params)
    assert response.status_code == 400
    assert "start must not be after end" in str(response.json())


def test_incident_analytics_read_only_immutability(database: Session):
    """Verify analytics execution never mutates database state."""
    inc = Incident(
        id=str(uuid4()),
        incident_number="INC-IMMUT-001",
        title="Immutability Target",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.MEDIUM,
        created_at=datetime.now(UTC).replace(tzinfo=None),
        metadata_json={"custom": "value"},
    )
    database.add(inc)
    database.commit()

    service = IncidentAnalyticsService(database)
    res = service.get_analytics()

    database.refresh(inc)
    assert inc.status == IncidentStatus.NEW
    assert inc.metadata_json == {"custom": "value"}


# ---------------------------------------------------------------------------
# High-Density Performance Scaling Benchmarks (10,000 Records)
# ---------------------------------------------------------------------------

def test_incident_analytics_performance_scaling_benchmark(database: Session):
    """Benchmark SQL aggregation query execution over 10,000 synthetic incident records."""
    base_time = datetime(2026, 1, 1, 0, 0, 0)
    bulk_incidents = []

    for i in range(10000):
        sev = IncidentSeverity.CRITICAL if i % 10 == 0 else (IncidentSeverity.HIGH if i % 3 == 0 else IncidentSeverity.MEDIUM)
        st = IncidentStatus.CLOSED if i % 2 == 0 else IncidentStatus.NEW
        c_at = base_time + timedelta(minutes=i)
        r_at = c_at + timedelta(minutes=15) if st == IncidentStatus.CLOSED else None
        cl_at = c_at + timedelta(minutes=30) if st == IncidentStatus.CLOSED else None

        inc = Incident(
            id=str(uuid4()),
            incident_number=f"INC-BENCH-{i:05d}",
            title=f"Benchmark Incident #{i}",
            status=st,
            severity=sev,
            source=IncidentSource.OPERATOR,
            primary_track_id=None,
            created_at=c_at,
            resolved_at=r_at,
            closed_at=cl_at,
            metadata_json={},
        )
        bulk_incidents.append(inc)

    database.bulk_save_objects(bulk_incidents)
    database.commit()

    service = IncidentAnalyticsService(database)

    start_clk = time.perf_counter()
    res = service.get_analytics()
    elapsed_ms = (time.perf_counter() - start_clk) * 1000.0

    assert res.summary.total_incidents >= 10000
    assert res.summary.closed_incidents >= 5000
    print(f"\n[BENCHMARK] 10,000 Incidents Aggregation Execution Time: {elapsed_ms:.2f} ms")
    assert elapsed_ms < 500.0  # Must execute under 500ms
