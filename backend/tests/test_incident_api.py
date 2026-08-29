"""Functional REST API and contract tests for incident management endpoints."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select

from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.incident import IncidentSeverity, IncidentSource, IncidentStatus
from app.models.incident_event import DefensiveActionCategory, IncidentEventType
from app.models.role import Role
from app.models.track import Track, TrackState
from app.models.user import User
from app.services.auth import create_user


def _authenticate_as(client, database, rbac_user, role_name: str = "OPERATIONS_ADMIN") -> User:
    """Helper to assign role and log in test user."""
    role = database.scalar(select(Role).where(Role.name == role_name))
    if role and role not in rbac_user.roles:
        rbac_user.roles.append(role)
        database.commit()

    login = client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert login.status_code == 200
    return rbac_user


def test_create_incident_api_success_and_response_schema(client, database, rbac_user):
    user = _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    # Create referenced Track and Alert rows for foreign key integrity
    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        id="TRK-00109",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        confidence=0.95,
    )
    alert = Alert(
        id="ALT-9901",
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        reason="Geofence breach detected",
        created_at=now,
        updated_at=now,
    )
    database.add_all([track, alert])
    database.commit()

    payload = {
        "title": "Unauthorized Low-Altitude UAS Incursion",
        "description": "Visual and RF sensor correlation at perimeter sector 4.",
        "severity": "HIGH",
        "source": "INTELLIGENCE",
        "primary_track_id": track.id,
        "primary_group_id": "GRP-SWARM-7",
        "originating_alert_id": alert.id,
        "originating_intelligence_event_id": "AI-EVT-440",
        "metadata": {"altitude_m": 120.5, "velocity_mps": 22.0},
    }

    response = client.post("/api/v1/incidents", json=payload)
    assert response.status_code == 201

    data = response.json()
    assert data["id"]
    assert data["incident_number"].startswith("INC-")
    assert data["title"] == payload["title"]
    assert data["description"] == payload["description"]
    assert data["status"] == "NEW"
    assert data["severity"] == "HIGH"
    assert data["source"] == "INTELLIGENCE"
    assert data["primary_track_id"] == track.id
    assert data["primary_group_id"] == "GRP-SWARM-7"
    assert data["originating_alert_id"] == alert.id
    assert data["originating_intelligence_event_id"] == "AI-EVT-440"
    assert data["created_by"] == user.id
    assert data["metadata"] == payload["metadata"]
    assert data["created_at"]
    assert data["updated_at"]
    assert data["acknowledged_at"] is None


def test_create_incident_api_validation_errors(client, database, rbac_user):
    _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    # 1. Blank title rejected
    res = client.post("/api/v1/incidents", json={"title": "   "})
    assert res.status_code == 422

    # 2. Missing title rejected
    res = client.post("/api/v1/incidents", json={"description": "No title provided"})
    assert res.status_code == 422

    # 3. Oversized metadata (>64KB) rejected
    huge_metadata = {"blob": "x" * 70000}
    res = client.post("/api/v1/incidents", json={"title": "Valid Title", "metadata": huge_metadata})
    assert res.status_code == 422


def test_get_incident_api_detail_and_404(client, database, rbac_user):
    _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    create_res = client.post("/api/v1/incidents", json={"title": "Target Incident"})
    assert create_res.status_code == 201
    incident_id = create_res.json()["id"]

    # Retrieve existing
    get_res = client.get(f"/api/v1/incidents/{incident_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == incident_id
    assert get_res.json()["title"] == "Target Incident"

    # Nonexistent incident -> 404
    missing_res = client.get("/api/v1/incidents/nonexistent-id-999")
    assert missing_res.status_code == 404
    assert missing_res.json()["error"]["code"] == "http_error"


def test_list_incidents_api_filters_and_pagination(client, database, rbac_user):
    _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    # Create distinct incidents
    client.post("/api/v1/incidents", json={"title": "Incident A", "severity": "LOW", "primary_group_id": "GRP-A"})
    client.post("/api/v1/incidents", json={"title": "Incident B", "severity": "HIGH", "primary_group_id": "GRP-B"})
    client.post("/api/v1/incidents", json={"title": "Incident C", "severity": "CRITICAL", "primary_group_id": "GRP-A"})

    # Filter by severity
    res_sev = client.get("/api/v1/incidents", params={"severity": "CRITICAL"})
    assert res_sev.status_code == 200
    items_sev = res_sev.json()["items"]
    assert len(items_sev) == 1
    assert items_sev[0]["title"] == "Incident C"

    # Filter by primary_group_id
    res_grp = client.get("/api/v1/incidents", params={"primary_group_id": "GRP-A"})
    assert res_grp.status_code == 200
    items_grp = res_grp.json()["items"]
    assert len(items_grp) == 2

    # Pagination: limit & offset
    res_page = client.get("/api/v1/incidents", params={"limit": 1, "offset": 0})
    assert res_page.status_code == 200
    assert len(res_page.json()["items"]) == 1
    assert res_page.json()["limit"] == 1
    assert res_page.json()["offset"] == 0

    # Invalid date range (created_from > created_to)
    now = datetime.now(UTC)
    invalid_dates = client.get(
        "/api/v1/incidents",
        params={
            "created_from": now.isoformat(),
            "created_to": (now - timedelta(hours=1)).isoformat(),
        },
    )
    assert invalid_dates.status_code == 400


def test_incident_lifecycle_endpoints_transitions(client, database, rbac_user):
    user = _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    # 1. Create -> NEW
    create = client.post("/api/v1/incidents", json={"title": "Lifecycle Progression"})
    assert create.status_code == 201
    inc_id = create.json()["id"]

    # 2. Acknowledge -> ACKNOWLEDGED
    ack = client.post(f"/api/v1/incidents/{inc_id}/acknowledge", json={"message": "Operator on console"})
    assert ack.status_code == 200
    assert ack.json()["status"] == "ACKNOWLEDGED"
    assert ack.json()["acknowledged_by"] == user.id
    assert ack.json()["acknowledged_at"] is not None

    # 3. Triage -> TRIAGED
    triage = client.post(
        f"/api/v1/incidents/{inc_id}/triage",
        json={"severity": "CRITICAL", "notes": "Confirmed hostile drone formation"},
    )
    assert triage.status_code == 200
    assert triage.json()["status"] == "TRIAGED"
    assert triage.json()["severity"] == "CRITICAL"

    # 4. Escalate -> ESCALATED
    esc = client.post(
        f"/api/v1/incidents/{inc_id}/escalate",
        json={"reason": "Approaching restricted airspace boundary"},
    )
    assert esc.status_code == 200
    assert esc.json()["status"] == "ESCALATED"

    # 5. De-escalate -> TRIAGED
    de_esc = client.post(
        f"/api/v1/incidents/{inc_id}/de-escalate",
        json={"target_status": "TRIAGED", "reason": "Target turned away from boundary"},
    )
    assert de_esc.status_code == 200
    assert de_esc.json()["status"] == "TRIAGED"

    # 6. Resolve -> RESOLVED
    res = client.post(
        f"/api/v1/incidents/{inc_id}/resolve",
        json={"resolution_summary": "Track departed monitored perimeter"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "RESOLVED"
    assert res.json()["resolved_by"] == user.id
    assert res.json()["resolved_at"] is not None

    # 7. Close -> CLOSED
    close = client.post(
        f"/api/v1/incidents/{inc_id}/close",
        json={"closure_notes": "Incident formal review signed off"},
    )
    assert close.status_code == 200
    assert close.json()["status"] == "CLOSED"
    assert close.json()["closed_by"] == user.id
    assert close.json()["closed_at"] is not None


def test_incident_lifecycle_invalid_transition_returns_409(client, database, rbac_user):
    _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    create = client.post("/api/v1/incidents", json={"title": "Invalid Transition Test"})
    inc_id = create.json()["id"]

    # 1. Illegal transition: Direct NEW -> CLOSED should return 409
    res_illegal = client.post(f"/api/v1/incidents/{inc_id}/close", json={"closure_notes": "Premature close"})
    assert res_illegal.status_code == 409
    assert "Cannot transition incident" in res_illegal.json()["error"]["message"]

    # 2. Double acknowledge: Transition NEW -> ACKNOWLEDGED then duplicate ACKNOWLEDGED -> ACKNOWLEDGED
    client.post(f"/api/v1/incidents/{inc_id}/acknowledge")
    res_dup = client.post(f"/api/v1/incidents/{inc_id}/acknowledge")
    assert res_dup.status_code == 409

    # 3. Transitions after CLOSED strictly forbidden
    client.post(f"/api/v1/incidents/{inc_id}/triage")
    client.post(f"/api/v1/incidents/{inc_id}/resolve")
    client.post(f"/api/v1/incidents/{inc_id}/close")

    res_after_closed = client.post(f"/api/v1/incidents/{inc_id}/triage")
    assert res_after_closed.status_code == 409


def test_incident_assign_and_reassign_api(client, database, rbac_user):
    _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    analyst_user = create_user(database, "analyst_jones", "Analyst Jones", "jones@example.invalid", "test-password-123")
    supervisor_user = create_user(database, "supervisor_smith", "Supervisor Smith", "smith@example.invalid", "test-password-123")

    create = client.post("/api/v1/incidents", json={"title": "Assignment Flow"})
    inc_id = create.json()["id"]

    # First assignment
    assign1 = client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"assigned_to": analyst_user.id, "message": "Assigning to duty analyst"},
    )
    assert assign1.status_code == 200
    assert assign1.json()["assigned_to"] == analyst_user.id
    assert assign1.json()["assigned_at"] is not None
    assert assign1.json()["status"] == "NEW"  # Status preserved

    # Reassignment
    assign2 = client.post(
        f"/api/v1/incidents/{inc_id}/assign",
        json={"assigned_to": supervisor_user.id, "message": "Reassigning for shift handover"},
    )
    assert assign2.status_code == 200
    assert assign2.json()["assigned_to"] == supervisor_user.id

    # Blank assignee rejected
    blank = client.post(f"/api/v1/incidents/{inc_id}/assign", json={"assigned_to": "  "})
    assert blank.status_code == 422


def test_incident_notes_endpoint(client, database, rbac_user):
    user = _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    create = client.post("/api/v1/incidents", json={"title": "Note Test"})
    inc_id = create.json()["id"]

    note_res = client.post(
        f"/api/v1/incidents/{inc_id}/notes",
        json={"message": "Observed optical payload signature.", "metadata": {"camera_id": "CAM-01"}},
    )
    assert note_res.status_code == 201
    note_data = note_res.json()
    assert note_data["incident_id"] == inc_id
    assert note_data["event_type"] == "NOTE_ADDED"
    assert note_data["message"] == "Observed optical payload signature."
    assert note_data["actor_user_id"] == user.id
    assert note_data["metadata"] == {"camera_id": "CAM-01"}
    assert note_data["sequence"] == 2  # 1 is CREATED, 2 is NOTE_ADDED

    # Blank note rejected
    blank_res = client.post(f"/api/v1/incidents/{inc_id}/notes", json={"message": "   "})
    assert blank_res.status_code == 422


def test_defensive_action_logging_endpoint(client, database, rbac_user):
    user = _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    create = client.post("/api/v1/incidents", json={"title": "Defensive Action Test"})
    inc_id = create.json()["id"]

    action_res = client.post(
        f"/api/v1/incidents/{inc_id}/actions",
        json={
            "category": "PROCEDURE_REVIEW",
            "message": "Reviewed operational standard response procedure.",
            "metadata": {"procedure_code": "SOP-UAS-04"},
        },
    )
    assert action_res.status_code == 201
    action_data = action_res.json()
    assert action_data["incident_id"] == inc_id
    assert action_data["event_type"] == "ACTION_LOGGED"
    assert action_data["category"] == "PROCEDURE_REVIEW"
    assert action_data["actor_user_id"] == user.id
    assert action_data["metadata"] == {"procedure_code": "SOP-UAS-04"}

    # Invalid action category rejected by Pydantic validation
    bad_cat = client.post(
        f"/api/v1/incidents/{inc_id}/actions",
        json={"category": "INVALID_NONDEFENSIVE_ACTION", "message": "test"},
    )
    assert bad_cat.status_code == 422


def test_incident_timeline_endpoint_and_deterministic_order(client, database, rbac_user):
    _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    assignee = create_user(database, "timeline_analyst", "Timeline Analyst", "analyst@example.invalid", "test-password-123")

    create = client.post("/api/v1/incidents", json={"title": "Timeline Integrity Test"})
    inc_id = create.json()["id"]

    client.post(f"/api/v1/incidents/{inc_id}/acknowledge")
    client.post(f"/api/v1/incidents/{inc_id}/assign", json={"assigned_to": assignee.id})
    client.post(f"/api/v1/incidents/{inc_id}/notes", json={"message": "Initial triage observation"})
    client.post(f"/api/v1/incidents/{inc_id}/triage", json={"severity": "HIGH"})
    client.post(
        f"/api/v1/incidents/{inc_id}/actions",
        json={"category": "OPERATOR_CONTACT", "message": "Contacted sector lead"},
    )
    client.post(f"/api/v1/incidents/{inc_id}/resolve", json={"resolution_summary": "Resolved"})

    timeline_res = client.get(f"/api/v1/incidents/{inc_id}/timeline")
    assert timeline_res.status_code == 200
    timeline = timeline_res.json()
    assert timeline["incident_id"] == inc_id
    assert timeline["total_count"] == 7

    events = timeline["events"]
    assert [e["sequence"] for e in events] == [1, 2, 3, 4, 5, 6, 7]
    assert [e["event_type"] for e in events] == [
        "CREATED",
        "ACKNOWLEDGED",
        "ASSIGNED",
        "NOTE_ADDED",
        "TRIAGED",
        "ACTION_LOGGED",
        "RESOLVED",
    ]


def test_actor_security_spoofing_prevented(client, database, rbac_user):
    user = _authenticate_as(client, database, rbac_user, "OPERATIONS_ADMIN")

    # Attempt to spoof created_by in creation payload
    spoofed_payload = {
        "title": "Spoofing Attempt",
        "created_by": "ATTACKER_INVENTED_USER_ID",
    }
    res = client.post("/api/v1/incidents", json=spoofed_payload)
    assert res.status_code == 201
    # Server must ignore or reject spoofed created_by and bind to real authenticated actor.id
    assert res.json()["created_by"] == user.id


def test_openapi_schema_contains_incident_endpoints(client):
    res = client.get("/openapi.json")
    assert res.status_code == 200
    schema = res.json()
    paths = schema.get("paths", {})

    expected_routes = [
        "/api/v1/incidents",
        "/api/v1/incidents/{incident_id}",
        "/api/v1/incidents/{incident_id}/timeline",
        "/api/v1/incidents/{incident_id}/acknowledge",
        "/api/v1/incidents/{incident_id}/assign",
        "/api/v1/incidents/{incident_id}/triage",
        "/api/v1/incidents/{incident_id}/escalate",
        "/api/v1/incidents/{incident_id}/de-escalate",
        "/api/v1/incidents/{incident_id}/resolve",
        "/api/v1/incidents/{incident_id}/close",
        "/api/v1/incidents/{incident_id}/notes",
        "/api/v1/incidents/{incident_id}/actions",
    ]

    for route in expected_routes:
        assert route in paths, f"OpenAPI schema missing route: {route}"
