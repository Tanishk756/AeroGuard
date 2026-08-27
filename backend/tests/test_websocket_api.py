"""Integration tests for authenticated operational and simulation WebSocket streaming channels."""

from datetime import UTC, datetime, timedelta
import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.config import get_settings
from app.core.events import get_event_bus
from app.models.detection import Detection
from app.models.role import Role
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.session import Session as AuthSession
from app.models.user import User, UserStatus
from app.schemas.events import RealtimeChannel, RealtimeEventType
from app.services.auth import create_session, create_user
from app.services.rbac import seed_rbac
from app.tracking.service import TrackingService

settings = get_settings()


@pytest.fixture(autouse=True)
def reset_event_bus():
    get_event_bus().reset()
    yield
    get_event_bus().reset()


@pytest.fixture
def auth_setup(database):
    """Seed RBAC and create users with operator and viewer roles."""
    seed_rbac(database)
    from sqlalchemy import select

    operator_role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    operator = create_user(database, "op-user", "Operator User", "op@example.invalid", "securepassword123")
    operator.roles.append(operator_role)

    unauthorized_user = create_user(database, "no-role-user", "No Role", "norole@example.invalid", "securepassword123")

    disabled_user = create_user(database, "disabled-user", "Disabled User", "dis@example.invalid", "securepassword123")
    disabled_user.status = UserStatus.DISABLED
    disabled_user.roles.append(operator_role)
    database.commit()

    return {
        "operator": operator,
        "unauthorized_user": unauthorized_user,
        "disabled_user": disabled_user,
    }


def test_ws_unauthenticated_connection_rejected(client):
    """Verify that connecting without a session cookie is rejected with WS_1008_POLICY_VIOLATION."""
    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/ws/operational"):
            pass
    assert exc.value.code == 1008

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect("/api/v1/ws/simulation"):
            pass
    assert exc.value.code == 1008


def test_ws_invalid_or_expired_session_rejected(client, database, auth_setup):
    """Verify that an expired or non-existent session cookie is rejected."""
    operator = auth_setup["operator"]
    sess, raw_secret = create_session(database, operator, "127.0.0.1", "test-agent")
    sess.expires_at = datetime.now(UTC).replace(tzinfo=None) - timedelta(hours=1)
    database.commit()

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/api/v1/ws/operational",
            cookies={settings.session_cookie_name: raw_secret},
        ):
            pass
    assert exc.value.code == 1008


def test_ws_disabled_user_rejected(client, database, auth_setup):
    """Verify that a disabled user account is rejected."""
    disabled_user = auth_setup["disabled_user"]
    _, raw_secret = create_session(database, disabled_user, "127.0.0.1", "test-agent")

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/api/v1/ws/operational",
            cookies={settings.session_cookie_name: raw_secret},
        ):
            pass
    assert exc.value.code == 1008


def test_ws_unauthorized_user_rejected_and_audited(client, database, auth_setup):
    """Verify that an authenticated user without required permissions is rejected."""
    unauthorized = auth_setup["unauthorized_user"]
    _, raw_secret = create_session(database, unauthorized, "127.0.0.1", "test-agent")

    with pytest.raises(WebSocketDisconnect) as exc:
        with client.websocket_connect(
            "/api/v1/ws/operational",
            cookies={settings.session_cookie_name: raw_secret},
        ):
            pass
    assert exc.value.code == 1008


def test_ws_authenticated_handshake_and_heartbeat(client, database, auth_setup):
    """Verify that an authorized operator connects successfully, receives greeting and handles ping/pong."""
    operator = auth_setup["operator"]
    _, raw_secret = create_session(database, operator, "127.0.0.1", "test-agent")

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: raw_secret},
    ) as ws:
        # Receive initial greeting
        greeting = ws.receive_json()
        assert greeting["event_type"] == "system.heartbeat"
        assert greeting["channel"] == "operational"
        assert greeting["sequence"] >= 1
        assert greeting["payload"]["status"] == "connected"
        assert greeting["payload"]["user_id"] == operator.id

        # Send ping
        ws.send_json({"type": "ping", "timestamp": "2026-08-27T00:00:00Z"})
        pong = ws.receive_json()
        assert pong["event_type"] == "system.heartbeat"
        assert pong["payload"]["type"] == "pong"
        assert pong["payload"]["client_time"] == "2026-08-27T00:00:00Z"


def test_ws_operational_event_broadcast(client, database, auth_setup):
    """Verify that publishing operational events sends realtime envelopes over WebSocket."""
    operator = auth_setup["operator"]
    _, raw_secret = create_session(database, operator, "127.0.0.1", "test-agent")

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: raw_secret},
    ) as ws:
        # Consume greeting
        greeting = ws.receive_json()
        assert greeting["payload"]["status"] == "connected"

        # Publish a track event via EventBus
        bus = get_event_bus()
        bus.publish(
            event_type=RealtimeEventType.TRACK_CREATED,
            channel=RealtimeChannel.OPERATIONAL,
            payload={
                "id": "TRK-REALTIME-1",
                "state": "NEW",
                "latitude": 37.7749,
                "longitude": -122.4194,
                "altitude": 150.0,
            },
            resource_type="track",
            resource_id="TRK-REALTIME-1",
        )

        event = ws.receive_json()
        assert event["event_type"] == "track.created"
        assert event["channel"] == "operational"
        assert event["resource_id"] == "TRK-REALTIME-1"
        assert event["payload"]["latitude"] == 37.7749


def test_ws_simulation_event_broadcast(client, database, auth_setup):
    """Verify that simulation channel receives simulation state and step events."""
    operator = auth_setup["operator"]
    _, raw_secret = create_session(database, operator, "127.0.0.1", "test-agent")

    with client.websocket_connect(
        "/api/v1/ws/simulation",
        cookies={settings.session_cookie_name: raw_secret},
    ) as ws:
        # Consume greeting
        greeting = ws.receive_json()
        assert greeting["channel"] == "simulation"

        # Publish simulation step
        bus = get_event_bus()
        bus.publish(
            event_type=RealtimeEventType.SIMULATION_STEP,
            channel=RealtimeChannel.SIMULATION,
            payload={
                "scenario_id": "SCN-TEST-1",
                "status": "RUNNING",
                "tick_count": 10,
                "virtual_time": "2026-08-27T01:00:00Z",
            },
            resource_type="scenario",
            resource_id="SCN-TEST-1",
        )

        event = ws.receive_json()
        assert event["event_type"] == "simulation.step"
        assert event["channel"] == "simulation"
        assert event["payload"]["tick_count"] == 10


def test_ws_detection_ingestion_triggers_realtime_track_event(client, database, auth_setup):
    """End-to-end test: Ingesting detection -> tracking creates track -> live event sent over WS."""
    operator = auth_setup["operator"]
    _, raw_secret = create_session(database, operator, "127.0.0.1", "test-agent")

    # Create active sensor
    now = datetime.now(UTC).replace(tzinfo=None)
    sensor = Sensor(
        id="RADAR-WS-1",
        name="Realtime Radar 1",
        source_type="radar",
        source_class=SensorSourceClass.SIMULATION,
        status=SensorStatus.ACTIVE,
        configuration_version=1,
        configuration_metadata={"range_meters": 5000},
        created_at=now,
        updated_at=now,
    )
    database.add(sensor)
    database.commit()

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: raw_secret},
    ) as ws:
        # Consume greeting
        greeting = ws.receive_json()
        assert greeting["payload"]["status"] == "connected"

        # Create Detection and process through TrackingService
        detection = Detection(
            source_detection_id="DET-REALTIME-001",
            sensor_id="RADAR-WS-1",
            source_class=SensorSourceClass.SIMULATION,
            source_type="radar",
            timestamp=datetime.now(UTC).replace(tzinfo=None),
            latitude=37.7749,
            longitude=-122.4194,
            altitude=200.0,
            velocity=25.0,
            heading=90.0,
            confidence=0.95,
            classification="UAV_ROTARY",
            metadata_json={},
            created_at=datetime.now(UTC).replace(tzinfo=None),
        )
        database.add(detection)
        database.commit()

        tracking_svc = TrackingService(database)
        tracking_svc.process_detection(detection)

        # Receive real-time operational events generated by pipeline
        event1 = ws.receive_json()
        event2 = ws.receive_json()
        event_types = {event1["event_type"], event2["event_type"]}
        assert "threat.updated" in event_types
        assert "track.created" in event_types

        track_event = event1 if event1["event_type"] == "track.created" else event2
        assert track_event["channel"] == "operational"
        assert track_event["payload"]["latitude"] == 37.7749
        assert track_event["payload"]["classification"] == "UAV_ROTARY"
