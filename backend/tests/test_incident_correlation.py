"""Integration tests for incident operational correlation (tracks, groups, alerts, intelligence events)."""

from datetime import UTC, datetime
import pytest
from sqlalchemy import select

from app.core.events import get_event_bus
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.incident import IncidentSeverity, IncidentSource
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


def test_track_and_alert_correlation_survives_to_eventbus(database):
    """Verify that primary_track_id and originating_alert_id survive DB persistence and are present in EventBus payload."""
    event_bus = get_event_bus()
    subscription = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    now = datetime.now(UTC).replace(tzinfo=None)

    # Persist referenced Track, Alert, and User rows for FK integrity
    track = Track(
        id="TRK-CORR-101",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.98,
    )
    alert = Alert(
        id="ALT-CORR-202",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.CRITICAL,
        status=AlertStatus.OPEN,
        reason="Perimeter breach by quadcopter",
        created_at=now,
        updated_at=now,
    )
    actor = create_user(database, "corr_operator", "Correlation Operator", "corr@example.invalid", "test-password-123")
    database.add_all([track, alert])
    database.commit()

    # Create Incident with full correlations
    service = IncidentService(database)
    incident = service.create_incident(
        title="Correlated Multi-Sensor Threat Incident",
        severity=IncidentSeverity.CRITICAL,
        source=IncidentSource.ALERT,
        primary_track_id="TRK-CORR-101",
        primary_group_id="GRP-SWARM-99",
        originating_alert_id="ALT-CORR-202",
        originating_intelligence_event_id="intel-snapshot-7744",
        created_by=actor.id,
    )
    database.commit()

    # Verify database model
    assert incident.primary_track_id == "TRK-CORR-101"
    assert incident.primary_group_id == "GRP-SWARM-99"
    assert incident.originating_alert_id == "ALT-CORR-202"
    assert incident.originating_intelligence_event_id == "intel-snapshot-7744"

    # Verify EventBus envelope and payload
    assert subscription.queue.qsize() == 1
    envelope = subscription.queue.get_nowait()

    payload = envelope.payload
    assert payload["incident_id"] == incident.id
    assert payload["primary_track_id"] == "TRK-CORR-101"
    assert payload["primary_group_id"] == "GRP-SWARM-99"
    assert payload["originating_alert_id"] == "ALT-CORR-202"
    assert payload["originating_intelligence_event_id"] == "intel-snapshot-7744"


def test_absent_correlations_serialize_as_null_in_event_payload(database):
    """Verify that standalone incidents without correlations serialize optional fields as None/null."""
    event_bus = get_event_bus()
    subscription = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    service = IncidentService(database)
    incident = service.create_incident(
        title="Standalone Operator Incident",
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
    )
    database.commit()

    envelope = subscription.queue.get_nowait()
    payload = envelope.payload

    assert payload["primary_track_id"] is None
    assert payload["primary_group_id"] is None
    assert payload["originating_alert_id"] is None
    assert payload["originating_intelligence_event_id"] is None
    assert payload["assigned_to"] is None
    assert payload["previous_assignee"] is None


def test_rest_api_correlations_round_trip(client, database):
    """Verify that correlations passed via REST API survive validation, database write, and EventBus emission."""
    seed_rbac(database)
    from app.models.role import Role
    op_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    op = create_user(database, "api_corr_op", "API Corr Op", "apicorr@example.invalid", "test-password-123")
    op.roles.append(op_role)

    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        id="TRK-API-999",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.91,
    )
    database.add(track)
    database.commit()

    event_bus = get_event_bus()
    sub = event_bus.subscribe(channel=RealtimeChannel.OPERATIONAL)

    # Login
    login = client.post("/api/v1/auth/login", json={"identifier": "api_corr_op", "password": "test-password-123"})
    assert login.status_code == 200

    create_res = client.post(
        "/api/v1/incidents",
        json={
            "title": "REST Correlated Incident",
            "severity": "HIGH",
            "primary_track_id": "TRK-API-999",
            "primary_group_id": "GRP-SWARM-1",
            "originating_intelligence_event_id": "INTEL-HIST-55",
        },
    )
    assert create_res.status_code == 201
    created_id = create_res.json()["id"]

    # Verify EventBus dispatch from REST transaction commit
    assert sub.queue.qsize() == 1
    evt = sub.queue.get_nowait()
    assert evt.payload["incident_id"] == created_id
    assert evt.payload["primary_track_id"] == "TRK-API-999"
    assert evt.payload["primary_group_id"] == "GRP-SWARM-1"
    assert evt.payload["originating_intelligence_event_id"] == "INTEL-HIST-55"
