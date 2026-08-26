"""Validated, sanitized, transaction-aware audit writing."""

import json
import logging
import re
from collections.abc import Mapping
from datetime import UTC, datetime
from itertools import islice
from typing import Any
from uuid import uuid4

from sqlalchemy.orm import Session

from app.models.audit import AuditEvent
from app.models.session import Session as AuthSession
from app.models.user import User

logger = logging.getLogger(__name__)

EVENT_TYPES = frozenset({
    "LOGIN_SUCCESS", "LOGIN_FAILURE", "LOGOUT", "SESSION_CREATED", "SESSION_REVOKED", "SESSION_EXPIRED",
    "AUTHORIZATION_DENIED", "ROLE_CREATED", "ROLE_UPDATED", "ROLE_DELETED", "ROLE_ASSIGNED", "ROLE_REVOKED",
    "PERMISSION_ASSIGNED", "PERMISSION_REVOKED", "SUPER_ADMIN_BOOTSTRAPPED", "SECURITY_POLICY_VIOLATION",
})
RESULTS = frozenset({"SUCCESS", "FAILURE", "DENIED"})
MAX_METADATA_BYTES = 16_384
MAX_DEPTH = 6
MAX_COLLECTION_ITEMS = 100
MAX_STRING_LENGTH = 512
SECRET_KEY_PATTERN = re.compile(r"(?:pass|secret|token|cookie|authorization|bearer|jwt|api.?key|private.?key|credential|hash)", re.I)
SAFE_CORRELATION = re.compile(r"^[A-Za-z0-9._:-]{1,64}$")


def sanitize_string(value: Any, limit: int = MAX_STRING_LENGTH) -> str:
    return "".join(character for character in str(value) if ord(character) >= 32 and character not in "\x7f\r\n")[:limit]


def normalize_metadata(value: Any) -> dict:
    def clean(item: Any, depth: int) -> Any:
        if depth > MAX_DEPTH:
            return "[truncated]"
        if isinstance(item, Mapping):
            output = {}
            for key, child in islice(item.items(), MAX_COLLECTION_ITEMS):
                key_text = sanitize_string(key, 128)
                if SECRET_KEY_PATTERN.search(key_text):
                    output[key_text] = "[redacted]"
                else:
                    output[key_text] = clean(child, depth + 1)
            return output
        if isinstance(item, (list, tuple, set)):
            children = item[:MAX_COLLECTION_ITEMS] if isinstance(item, (list, tuple)) else islice(item, MAX_COLLECTION_ITEMS)
            return [clean(child, depth + 1) for child in children]
        if item is None or isinstance(item, (bool, int, float)):
            return item
        return sanitize_string(item)

    cleaned = clean(value, 0)
    if not isinstance(cleaned, dict):
        cleaned = {"value": cleaned}
    encoded = json.dumps(cleaned, separators=(",", ":"), default=sanitize_string)
    if len(encoded.encode("utf-8")) > MAX_METADATA_BYTES:
        return {"_audit_metadata": "[oversized metadata redacted]"}
    return cleaned


def correlation_id(value: str | None) -> str:
    return value if value and SAFE_CORRELATION.fullmatch(value) else str(uuid4())


class AuditService:
    def __init__(self, db: Session):
        self.db = db

    def record_event(
        self,
        event_type: str,
        action: str,
        result: str,
        *,
        event_version: int = 1,
        correlation: str | None = None,
        actor: User | None = None,
        session: AuthSession | None = None,
        target_type: str | None = None,
        target_id: str | None = None,
        reason: str | None = None,
        permission: str | None = None,
        source_ip: str | None = None,
        user_agent: str | None = None,
        metadata: Any = None,
    ) -> AuditEvent:
        if event_type not in EVENT_TYPES:
            raise ValueError("Unsupported audit event type")
        if result not in RESULTS:
            raise ValueError("Unsupported audit result")
        if event_version != 1:
            raise ValueError("Unsupported audit event version")
        event = AuditEvent(
            event_type=event_type, event_version=event_version, action=sanitize_string(action, 128), result=result,
            correlation_id=correlation_id(correlation), actor_user_id=actor.id if actor else None,
            actor_session_id=session.id if session else None, target_type=sanitize_string(target_type, 64) if target_type else None,
            target_id=sanitize_string(target_id, 128) if target_id else None, reason=sanitize_string(reason) if reason else None,
            permission=sanitize_string(permission, 128) if permission else None, source_ip=sanitize_string(source_ip, 45) if source_ip else None,
            user_agent=sanitize_string(user_agent, 512) if user_agent else None, event_metadata=normalize_metadata(metadata or {}),
        )
        self.db.add(event)
        return event
