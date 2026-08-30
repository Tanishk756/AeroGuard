"""Authenticated WebSocket streaming endpoints for operational and simulation telemetry."""

import asyncio
from datetime import UTC, datetime
import json
import logging
from typing import Any

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.events import get_event_bus
from app.database.session import get_db
from app.models.session import Session as AuthSession
from app.models.user import User
from app.schemas.events import RealtimeChannel, RealtimeEventEnvelope, RealtimeEventType
from app.services.audit import AuditService
from app.services.auth import hash_session_secret
from app.services.authorization import AuthorizationService

logger = logging.getLogger(__name__)
settings = get_settings()

router = APIRouter()


async def _authenticate_ws(
    websocket: WebSocket,
    db: Session,
    required_permissions: list[str],
    channel_name: str,
) -> tuple[AuthSession, User] | None:
    """Validate HttpOnly session cookie and RBAC permissions for WebSocket handshake."""
    session_secret = websocket.cookies.get(settings.session_cookie_name)
    if not session_secret:
        # Check Authorization or Cookie header fallback if direct cookie dictionary is unparsed
        cookie_header = websocket.headers.get("cookie", "")
        for part in cookie_header.split(";"):
            part = part.strip()
            if part.startswith(f"{settings.session_cookie_name}="):
                session_secret = part.split("=", 1)[1]
                break

    if not session_secret:
        logger.warning("WebSocket connection rejected: missing session cookie (%s)", channel_name)
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Authentication is required.")
        return None

    try:
        secret_hash = hash_session_secret(session_secret)
        session = db.scalar(select(AuthSession).where(AuthSession.session_secret_hash == secret_hash))
        if session is None or session.revoked_at is not None:
            logger.warning("WebSocket connection rejected: invalid or revoked session (%s)", channel_name)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="The session is no longer valid.")
            return None

        if session.expires_at <= datetime.now(UTC).replace(tzinfo=None):
            logger.warning("WebSocket connection rejected: expired session (%s)", channel_name)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="The session has expired.")
            return None

        user = session.user
        if user.status.value == "DISABLED":
            logger.warning("WebSocket connection rejected: disabled user account (%s)", channel_name)
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="The user account is disabled.")
            return None

        auth_service = AuthorizationService(db)
        if not auth_service.has_any_permission(user, required_permissions):
            logger.warning("WebSocket connection rejected: user %s lacks required permissions %s", user.id, required_permissions)
            try:
                AuditService(db).record_event(
                    "AUTHORIZATION_DENIED",
                    "authorize_websocket",
                    "DENIED",
                    actor=user,
                    session=session,
                    permission=",".join(required_permissions),
                    target_type="websocket",
                    target_id=channel_name,
                    source_ip=websocket.client.host if websocket.client else None,
                )
                db.commit()
            except Exception:
                db.rollback()
            await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="You do not have permission to access this channel.")
            return None

        session.last_seen_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        return session, user

    except Exception:
        db.rollback()
        logger.exception("Unexpected error during WebSocket authentication")
        await websocket.close(code=status.WS_1011_INTERNAL_ERROR, reason="Internal authentication error.")
        return None


async def _handle_stream(
    websocket: WebSocket,
    channel: RealtimeChannel,
    user: User,
    filter_func: Any | None = None,
) -> None:
    """Pump realtime event envelopes to the connected client while handling incoming heartbeats."""
    event_bus = get_event_bus()
    subscription = event_bus.subscribe(channel=channel, maxsize=100, filter_func=filter_func)

    # Send initial connection confirmation envelope
    greeting_seq = event_bus.get_next_sequence(channel.value)
    greeting = RealtimeEventEnvelope(
        event_type=RealtimeEventType.HEARTBEAT,
        channel=channel.value,
        sequence=greeting_seq,
        timestamp=datetime.now(UTC),
        payload={
            "status": "connected",
            "channel": channel.value,
            "user_id": user.id,
            "server_time": datetime.now(UTC).isoformat(),
        },
    )
    await websocket.send_json(greeting.model_dump(mode="json"))

    async def _event_pump():
        try:
            while True:
                envelope = await subscription.queue.get()
                try:
                    await websocket.send_json(envelope.model_dump(mode="json"))
                finally:
                    subscription.queue.task_done()
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("WebSocket event pump error (%s): %s", channel.value, exc)

    async def _message_receiver():
        try:
            while True:
                data = await websocket.receive_text()
                try:
                    msg = json.loads(data)
                except Exception:
                    continue

                if isinstance(msg, dict) and msg.get("type") in {"ping", "heartbeat"}:
                    pong_seq = event_bus.get_next_sequence(channel.value)
                    pong = RealtimeEventEnvelope(
                        event_type=RealtimeEventType.HEARTBEAT,
                        channel=channel.value,
                        sequence=pong_seq,
                        timestamp=datetime.now(UTC),
                        payload={
                            "type": "pong",
                            "client_time": msg.get("timestamp"),
                            "server_time": datetime.now(UTC).isoformat(),
                        },
                    )
                    await websocket.send_json(pong.model_dump(mode="json"))
        except (WebSocketDisconnect, asyncio.CancelledError):
            pass
        except Exception as exc:
            logger.debug("WebSocket message receiver error (%s): %s", channel.value, exc)

    pump_task = asyncio.create_task(_event_pump())
    recv_task = asyncio.create_task(_message_receiver())

    from app.core.telemetry import WEBSOCKET_CONNECTIONS
    WEBSOCKET_CONNECTIONS.inc()

    try:
        done, pending = await asyncio.wait(
            [pump_task, recv_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        for task in pending:
            task.cancel()
    finally:
        WEBSOCKET_CONNECTIONS.dec()
        event_bus.unsubscribe(subscription)
        for task in [pump_task, recv_task]:
            if not task.done():
                task.cancel()
        logger.debug("WebSocket connection closed cleanly for user %s on channel %s", user.id, channel.value)


@router.websocket("/ws/operational")
async def operational_websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """Realtime WebSocket stream for defensive operational events (tracks, alerts, threats, geofences, incidents)."""
    try:
        auth_res = await _authenticate_ws(
            websocket,
            db,
            required_permissions=["tracks.read", "threats.read", "alerts.read", "system.read", "incidents.read"],
            channel_name="/ws/operational",
        )
        if auth_res is None:
            return

        _, user = auth_res
        auth_service = AuthorizationService(db)
        has_incidents_permission = auth_service.has_permission(user, "incidents.read")

        def _operational_filter(envelope: RealtimeEventEnvelope) -> bool:
            if envelope.event_type.startswith("incident."):
                return has_incidents_permission
            return True

        await websocket.accept()
        await _handle_stream(websocket, RealtimeChannel.OPERATIONAL, user, filter_func=_operational_filter)
    except WebSocketDisconnect:
        logger.debug("Client disconnected from /ws/operational")


@router.websocket("/ws/simulation")
async def simulation_websocket_endpoint(
    websocket: WebSocket,
    db: Session = Depends(get_db),
):
    """Realtime WebSocket stream for scenario simulation state, stepping, and virtual clock ticks."""
    try:
        auth_res = await _authenticate_ws(
            websocket,
            db,
            required_permissions=["scenarios.read", "scenarios.execute", "system.read"],
            channel_name="/ws/simulation",
        )
        if auth_res is None:
            return

        _, user = auth_res
        await websocket.accept()
        await _handle_stream(websocket, RealtimeChannel.SIMULATION, user)
    except WebSocketDisconnect:
        logger.debug("Client disconnected from /ws/simulation")
