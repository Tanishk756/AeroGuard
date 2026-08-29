"""Integration tests for incident operational correlation (tracks, groups, alerts, intelligence events)."""

from datetime import UTC, datetime
import pytest
from sqlalchemy import select

from app.core.events import get_event_bus
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.incident import IncidentSeverity, IncidentSource
from app.models.role import Role
from app.models.track import Track, TrackState
from app.schemas.events import RealtimeChannel
from app.services.auth import create_user
from app.services.incident import IncidentService
from app.services.rbac import seed_rbac


@pytest.fixture(autouse=True)
def reset_bus():
    get_event_bus().reset()
    yield
    get_event_bus().reset()


def test_27_track_correlation_survives_rest_to_db_to_eventbus(client, database):
    """27. Verify that primary_track_id survives REST -> DB -> EventBus."""
    seed_rbac(database)
    op_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    op = create_user(database, "track_corr_op", "Track Corr Op", "tcorr@example.invalid", "test-password-123")
    op.roles.append(op_role)

    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        id="TRK-CORR-27",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.95,
    )
    database.add(track)
    database.commit()

    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    client.post("/api/v1/auth/login", json={"identifier": "track_corr_op", "password": "test-password-123"})
    res = client.post(
        "/api/v1/incidents",
        json={"title": "Track Correlated Incident", "primary_track_id": "TRK-CORR-27"},
    )
    assert res.status_code == 201

    evt = sub.queue.get_nowait()
    assert evt.payload["primary_track_id"] == "TRK-CORR-27"


def test_28_group_correlation_survives_rest_to_db_to_eventbus(client, database):
    """28. Verify that primary_group_id survives REST -> DB -> EventBus."""
    seed_rbac(database)
    op_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    op = create_user(database, "group_corr_op", "Group Corr Op", "gcorr@example.invalid", "test-password-123")
    op.roles.append(op_role)
    database.commit()

    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    client.post("/api/v1/auth/login", json={"identifier": "group_corr_op", "password": "test-password-123"})
    res = client.post(
        "/api/v1/incidents",
        json={"title": "Group Correlated Incident", "primary_group_id": "GRP-SWARM-28"},
    )
    assert res.status_code == 201

    evt = sub.queue.get_nowait()
    assert evt.payload["primary_group_id"] == "GRP-SWARM-28"


def test_29_alert_correlation_survives_rest_to_db_to_eventbus(client, database):
    """29. Verify that originating_alert_id survives REST -> DB -> EventBus."""
    seed_rbac(database)
    op_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    op = create_user(database, "alert_corr_op", "Alert Corr Op", "acorr@example.invalid", "test-password-123")
    op.roles.append(op_role)

    now = datetime.now(UTC).replace(tzinfo=None)
    alert = Alert(
        id="ALT-CORR-29",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        reason="Perimeter breach alert",
        created_at=now,
        updated_at=now,
    )
    database.add(alert)
    database.commit()

    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    client.post("/api/v1/auth/login", json={"identifier": "alert_corr_op", "password": "test-password-123"})
    res = client.post(
        "/api/v1/incidents",
        json={"title": "Alert Correlated Incident", "originating_alert_id": "ALT-CORR-29"},
    )
    assert res.status_code == 201

    evt = sub.queue.get_nowait()
    assert evt.payload["originating_alert_id"] == "ALT-CORR-29"


def test_30_intelligence_event_correlation_survives_rest_to_db_to_eventbus(client, database):
    """30. Verify that originating_intelligence_event_id survives REST -> DB -> EventBus."""
    seed_rbac(database)
    op_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    op = create_user(database, "intel_corr_op", "Intel Corr Op", "icorr@example.invalid", "test-password-123")
    op.roles.append(op_role)
    database.commit()

    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    client.post("/api/v1/auth/login", json={"identifier": "intel_corr_op", "password": "test-password-123"})
    res = client.post(
        "/api/v1/incidents",
        json={"title": "Intel Correlated Incident", "originating_intelligence_event_id": "INTEL-HIST-30"},
    )
    assert res.status_code == 201

    evt = sub.queue.get_nowait()
    assert evt.payload["originating_intelligence_event_id"] == "INTEL-HIST-30"


def test_31_absent_correlations_serialize_as_null_in_event_payload(database):
    """31. Verify that absent correlations serialize as null according to contract."""
    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    service.create_incident(
        title="Standalone Operator Incident",
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
    )
    database.commit()

    evt = sub.queue.get_nowait()
    assert evt.payload["primary_track_id"] is None
    assert evt.payload["primary_group_id"] is None
    assert evt.payload["originating_alert_id"] is None
    assert evt.payload["originating_intelligence_event_id"] is None
