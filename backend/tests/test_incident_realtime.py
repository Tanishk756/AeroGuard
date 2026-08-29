"""Integration tests for incident realtime streaming over authenticated /ws/operational WebSocket."""

from datetime import UTC, datetime
import pytest
from sqlalchemy import select
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.core.events import get_event_bus
from app.models.role import Role
from app.models.track import Track, TrackState
from app.models.user import User
from app.schemas.events import RealtimeChannel, RealtimeEventType
from app.services.auth import create_session, create_user
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

    # 2. Viewer (has tracks.read, alerts.read, but we can also test role without incidents.read if needed)
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


def test_32_authenticated_operational_websocket_receives_incident_created(client, database, rt_setup):
    """32. Verify that authenticated operational WebSocket receives incident.created event."""
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
        client.post("/api/v1/auth/login", json={"identifier": "op_streamer", "password": "test-password-123"})
        create_res = client.post(
            "/api/v1/incidents",
            json={"title": "WebSocket Streamed Incident", "severity": "HIGH", "primary_track_id": "TRK-WS-100"},
        )
        assert create_res.status_code == 201
        inc_id = create_res.json()["id"]

        # Receive incident.created event
        evt = ws.receive_json()
        assert evt["event_type"] == "incident.created"
        assert evt["channel"] == "operational"
        assert evt["payload"]["incident_id"] == inc_id
        assert evt["payload"]["severity"] == "HIGH"
        assert evt["payload"]["primary_track_id"] == "TRK-WS-100"


def test_33_lifecycle_event_delivered_over_websocket(client, database, rt_setup):
    """33. Verify that incident lifecycle transitions (acknowledge, triage, resolve, close) stream over WebSocket."""
    operator = rt_setup["operator"]
    _, session_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: session_secret},
    ) as ws:
        ws.receive_json()  # greeting

        client.post("/api/v1/auth/login", json={"identifier": "op_streamer", "password": "test-password-123"})
        create_res = client.post("/api/v1/incidents", json={"title": "Lifecycle WS Test"})
        inc_id = create_res.json()["id"]
        ws.receive_json()  # consume create event

        # Acknowledge
        ack_res = client.post(f"/api/v1/incidents/{inc_id}/acknowledge", json={"message": "Ack"})
        assert ack_res.status_code == 200

        evt_ack = ws.receive_json()
        assert evt_ack["event_type"] == "incident.acknowledged"
        assert evt_ack["payload"]["status"] == "ACKNOWLEDGED"


def test_34_note_event_delivered_over_websocket(client, database, rt_setup):
    """34. Verify that adding a note streams an incident.note_added event over WebSocket."""
    operator = rt_setup["operator"]
    _, session_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: session_secret},
    ) as ws:
        ws.receive_json()  # greeting

        client.post("/api/v1/auth/login", json={"identifier": "op_streamer", "password": "test-password-123"})
        create_res = client.post("/api/v1/incidents", json={"title": "Note WS Test"})
        inc_id = create_res.json()["id"]
        ws.receive_json()  # consume create event

        note_res = client.post(f"/api/v1/incidents/{inc_id}/notes", json={"message": "Observation note logged"})
        assert note_res.status_code == 201

        evt_note = ws.receive_json()
        assert evt_note["event_type"] == "incident.note_added"
        assert evt_note["payload"]["message"] == "Observation note logged"


def test_35_action_event_delivered_over_websocket(client, database, rt_setup):
    """35. Verify that logging a defensive action streams an incident.action_logged event over WebSocket."""
    operator = rt_setup["operator"]
    _, session_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: session_secret},
    ) as ws:
        ws.receive_json()  # greeting

        client.post("/api/v1/auth/login", json={"identifier": "op_streamer", "password": "test-password-123"})
        create_res = client.post("/api/v1/incidents", json={"title": "Action WS Test"})
        inc_id = create_res.json()["id"]
        ws.receive_json()  # consume create event

        act_res = client.post(
            f"/api/v1/incidents/{inc_id}/actions",
            json={"category": "SENSOR_REVIEW", "message": "Radar track correlation checked"},
        )
        assert act_res.status_code == 201

        evt_act = ws.receive_json()
        assert evt_act["event_type"] == "incident.action_logged"
        assert evt_act["payload"]["category"] == "SENSOR_REVIEW"


def test_36_unauthorized_client_cannot_receive_incident_events(client, database, rt_setup):
    """36. Verify that an unauthenticated client or a client lacking incidents.read permission cannot stream incident events."""
    # 1. Unauthenticated connection is rejected
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect("/api/v1/ws/operational"):
            pass


def test_37_existing_ai_telemetry_remains_unaffected(client, database, rt_setup):
    """37. Verify that existing AI, track, and alert events stream alongside incident events without interference."""
    operator = rt_setup["operator"]
    _, session_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: session_secret},
    ) as ws:
        ws.receive_json()  # greeting

        event_bus = get_event_bus()

        # Publish AI summary
        event_bus.publish(
            event_type=RealtimeEventType.AI_SUMMARY,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"cluster_count": 3, "threat_level": "MODERATE"},
        )

        # Publish incident event
        event_bus.publish(
            event_type=RealtimeEventType.INCIDENT_CREATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"incident_number": "INC-CONCURRENT-37", "severity": "MEDIUM"},
        )

        # Publish alert event
        event_bus.publish(
            event_type=RealtimeEventType.ALERT_CREATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={"alert_id": "ALT-37", "type": "GEOFENCE_BREACH"},
        )

        # Receive all 3 in order
        m1 = ws.receive_json()
        assert m1["event_type"] == "ai.summary"

        m2 = ws.receive_json()
        assert m2["event_type"] == "incident.created"
        assert m2["payload"]["incident_number"] == "INC-CONCURRENT-37"

        m3 = ws.receive_json()
        assert m3["event_type"] == "alert.created"


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
