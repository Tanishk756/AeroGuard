"""Integration tests for incident realtime streaming over authenticated /ws/operational WebSocket."""

from datetime import UTC, datetime
import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.core.events import get_event_bus
from app.models.incident import IncidentSeverity
from app.models.role import Role
from app.models.track import Track, TrackState
from app.models.user import User, UserStatus
from app.schemas.events import RealtimeChannel, RealtimeEventType
from app.services.auth import create_session, create_user
from app.services.incident import IncidentService
from app.services.rbac import seed_rbac

settings = get_settings()


@pytest.fixture(autouse=True)
def reset_bus():
    get_event_bus().reset()
    yield
    get_event_bus().reset()


@pytest.fixture
def rt_setup(database):
    """Seed RBAC and create users for operator, viewer, and tracked assets."""
    seed_rbac(database)

    # 1. Operator (has incidents.read, incidents.create, incidents.manage, etc.)
    op_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    operator = create_user(database, "op_streamer", "Operator Streamer", "op@example.invalid", "test-password-123")
    operator.roles.append(op_role)

    # 2. Viewer (has incidents.read, tracks.read, alerts.read)
    viewer_role = database.scalar(select(Role).where(Role.name == "VIEWER"))
    viewer = create_user(database, "viewer_streamer", "Viewer Streamer", "view@example.invalid", "test-password-123")
    viewer.roles.append(viewer_role)

    # 3. Track asset
    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        id="TRK-WS-100",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.92,
    )
    database.add(track)

    database.commit()
    return {
        "operator": operator,
        "viewer": viewer,
        "track": track,
    }


def test_authenticated_websocket_receives_incident_creation_and_lifecycle(client, database, rt_setup):
    """Verify that an authenticated WebSocket subscriber receives incident lifecycle events in realtime."""
    operator = rt_setup["operator"]
    _, session_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: session_secret},
    ) as ws:
        # Initial heartbeat greeting
        greeting = ws.receive_json()
        assert greeting["event_type"] == "system.heartbeat"
        assert greeting["payload"]["status"] == "connected"

        # Create incident via REST API
        login_res = client.post("/api/v1/auth/login", json={"identifier": "op_streamer", "password": "test-password-123"})
        assert login_res.status_code == 200

        create_res = client.post(
            "/api/v1/incidents",
            json={
                "title": "WebSocket Streamed Incident",
                "severity": "HIGH",
                "primary_track_id": "TRK-WS-100",
            },
        )
        assert create_res.status_code == 201
        inc_data = create_res.json()
        inc_id = inc_data["id"]

        # Receive incident.created event
        evt_created = ws.receive_json()
        assert evt_created["event_type"] == "incident.created"
        assert evt_created["channel"] == "operational"
        assert evt_created["payload"]["incident_id"] == inc_id
        assert evt_created["payload"]["severity"] == "HIGH"
        assert evt_created["payload"]["primary_track_id"] == "TRK-WS-100"
        assert evt_created["payload"]["incident_event_sequence"] == 1

        # Acknowledge incident via REST
        ack_res = client.post(f"/api/v1/incidents/{inc_id}/acknowledge", json={"message": "Acknowledged on console"})
        assert ack_res.status_code == 200

        # Receive incident.acknowledged event
        evt_ack = ws.receive_json()
        assert evt_ack["event_type"] == "incident.acknowledged"
        assert evt_ack["payload"]["incident_id"] == inc_id
        assert evt_ack["payload"]["status"] == "ACKNOWLEDGED"
        assert evt_ack["payload"]["previous_status"] == "NEW"
        assert evt_ack["payload"]["incident_event_sequence"] == 2

        # Add Note via REST
        note_res = client.post(f"/api/v1/incidents/{inc_id}/notes", json={"message": "Visual contact confirmed"})
        assert note_res.status_code == 201

        # Receive incident.note_added event
        evt_note = ws.receive_json()
        assert evt_note["event_type"] == "incident.note_added"
        assert evt_note["payload"]["message"] == "Visual contact confirmed"
        assert evt_note["payload"]["incident_event_sequence"] == 3

        # Log Defensive Action via REST
        action_res = client.post(
            f"/api/v1/incidents/{inc_id}/actions",
            json={"category": "SENSOR_REVIEW", "message": "Radar track correlation reviewed"},
        )
        assert action_res.status_code == 201

        # Receive incident.action_logged event
        evt_action = ws.receive_json()
        assert evt_action["event_type"] == "incident.action_logged"
        assert evt_action["payload"]["category"] == "SENSOR_REVIEW"
        assert evt_action["payload"]["incident_event_sequence"] == 4


def test_concurrent_existing_telemetry_unaffected_by_incidents(client, database, rt_setup):
    """Verify that existing AI, track, and alert events stream alongside incident events without interference."""
    operator = rt_setup["operator"]
    _, session_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: session_secret},
    ) as ws:
        # Heartbeat greeting
        greeting = ws.receive_json()
        assert greeting["event_type"] == "system.heartbeat"

        event_bus = get_event_bus()

        # Publish an AI summary event
        event_bus.publish(
            event_type=RealtimeEventType.AI_SUMMARY,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"cluster_count": 3, "threat_level": "MODERATE"},
        )

        # Publish an incident event
        event_bus.publish(
            event_type=RealtimeEventType.INCIDENT_CREATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"incident_number": "INC-CONCURRENT-1", "severity": "MEDIUM"},
        )

        # Publish an alert event
        event_bus.publish(
            event_type=RealtimeEventType.ALERT_CREATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"alert_id": "ALT-1", "type": "GEOFENCE_BREACH"},
        )

        # Receive all 3 in order
        msg1 = ws.receive_json()
        assert msg1["event_type"] == "ai.summary"

        msg2 = ws.receive_json()
        assert msg2["event_type"] == "incident.created"
        assert msg2["payload"]["incident_number"] == "INC-CONCURRENT-1"

        msg3 = ws.receive_json()
        assert msg3["event_type"] == "alert.created"


def test_websocket_ping_pong_heartbeat(client, database, rt_setup):
    """Verify WebSocket client ping-pong heartbeat exchange."""
    operator = rt_setup["operator"]
    _, session_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: session_secret},
    ) as ws:
        ws.receive_json()  # greeting

        # Send client ping
        ws.send_json({"type": "ping", "timestamp": "2026-08-29T08:00:00Z"})

        # Receive pong response
        pong = ws.receive_json()
        assert pong["event_type"] == "system.heartbeat"
        assert pong["payload"]["type"] == "pong"
        assert pong["payload"]["client_time"] == "2026-08-29T08:00:00Z"
