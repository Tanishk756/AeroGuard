"""Audit service security and transaction tests."""

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.models.audit import AuditEvent
from app.services.audit import AuditService, normalize_metadata


def test_event_creation_validation_and_sanitization(database, rbac_user):
    event = AuditService(database).record_event(
        "SECURITY_POLICY_VIOLATION", "policy check\n", "FAILURE", correlation="client.trace",
        actor=rbac_user, metadata={"nested": [{"PaSsWoRd": "secret", "normal": "ok"}]},
    )
    database.commit()
    assert event.actor_user_id == rbac_user.id
    assert event.event_metadata["nested"][0]["PaSsWoRd"] == "[redacted]"
    with pytest.raises(ValueError):
        AuditService(database).record_event("NOPE", "x", "SUCCESS")
    with pytest.raises(ValueError):
        AuditService(database).record_event("LOGIN_SUCCESS", "x", "MAYBE")
    with pytest.raises(ValueError):
        AuditService(database).record_event("LOGIN_SUCCESS", "x", "SUCCESS", event_version=2)


def test_metadata_bounds_and_malformed_values():
    assert len(normalize_metadata({"x": "a" * 20_000})["x"]) == 512
    assert normalize_metadata({"items": list(range(200))})["items"][-1] == 99
    assert normalize_metadata({"a": {"b": {"c": {"d": {"e": {"f": {"g": 1}}}}}}})["a"]["b"]["c"]["d"]["e"]["f"]["g"] == "[truncated]"
    assert normalize_metadata(["bad input"])["value"]
    assert normalize_metadata([{"authorization": "Bearer SECRET"}])["value"][0]["authorization"] == "[redacted]"


def test_audit_is_immutable_at_orm_layer(database):
    event = AuditService(database).record_event("LOGIN_FAILURE", "authenticate", "FAILURE")
    database.commit()
    event.action = "changed"
    with pytest.raises(ValueError):
        database.commit()
    database.rollback()
    database.delete(event)
    with pytest.raises(ValueError):
        database.commit()
