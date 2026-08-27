"""Comprehensive API integration tests for AeroGuard AI2 defensive intelligence endpoints, EventBus, and WebSockets."""

from datetime import UTC, datetime, timedelta
import json
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.schemas import (
    DefensiveIntelligenceSummary,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
)
from ai.service import DefensiveIntelligenceService
from app.core.events import get_event_bus
from app.models.geofence import Geofence
from app.models.role import Role
from app.models.sensor import SensorSourceClass
from app.models.track import Track, TrackHistory, TrackState
from app.schemas.events import RealtimeChannel, RealtimeEventType


def assign_role(database: Session, user, role_name: str = "OPERATOR"):
    role = database.scalar(select(Role).where(Role.name == role_name))
    user.roles.append(role)
    database.commit()


@pytest.fixture
def test_tracks_and_geofences(database: Session):
    """Fixture populating realistic airspace tracks and geofences for intelligence API tests."""
    now = datetime.now(UTC).replace(tzinfo=None)

    # Track 1: Fast approaching track with history
    t1 = Track(
        id="TRK-INTEL-01",
        state=TrackState.ACTIVE,
        first_seen_at=now - timedelta(seconds=30),
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=150.0,
        velocity=35.0,
        heading=45.0,
        confidence=0.95,
        classification="UAV_ROTARY",
        source_count=2,
        created_at=now,
        updated_at=now,
    )

    # Track 2: Coordinated wingman flying in tight formation with Track 1
    t2 = Track(
        id="TRK-INTEL-02",
        state=TrackState.ACTIVE,
        first_seen_at=now - timedelta(seconds=30),
        last_seen_at=now,
        latitude=37.7751,
        longitude=-122.4192,
        altitude=152.0,
        velocity=35.2,
        heading=45.5,
        confidence=0.92,
        classification="UAV_ROTARY",
        source_count=2,
        created_at=now,
        updated_at=now,
    )

    # Track 3: Isolated nominal track
    t3 = Track(
        id="TRK-INTEL-03",
        state=TrackState.ACTIVE,
        first_seen_at=now - timedelta(seconds=30),
        last_seen_at=now,
        latitude=37.8500,
        longitude=-122.3500,
        altitude=300.0,
        velocity=10.0,
        heading=180.0,
        confidence=0.85,
        classification="DRONE",
        source_count=1,
        created_at=now,
        updated_at=now,
    )

    database.add_all([t1, t2, t3])

    # Add history for Track 1
    for i in range(5):
        hist = TrackHistory(
            track_id="TRK-INTEL-01",
            sequence=i + 1,
            timestamp=now - timedelta(seconds=20 - (i * 4)),
            latitude=37.7749 + (i * 0.0003),
            longitude=-122.4194 + (i * 0.0003),
            altitude=150.0,
            velocity=35.0,
            heading=45.0,
            confidence=0.95,
            state=TrackState.ACTIVE,
            provenance=SensorSourceClass.REAL,
            source_detection_ids=[f"DET-INTEL-{i}"],
            created_at=now,
        )
        database.add(hist)

    # Add defensive geofence
    geofence = Geofence(
        id="GEO-INTEL-01",
        name="Defensive Perimeter Alpha",
        geometry={"type": "BBOX", "min_lat": 37.7700, "max_lat": 37.7900, "min_lon": -122.4300, "max_lon": -122.4000},
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    database.add(geofence)
    database.commit()

    return {"t1": t1, "t2": t2, "t3": t3, "geofence": geofence}


# ─────────────────────────────────────────────────────────────────────────────
# 1. Single-Track Intelligence Endpoint & Priority Exposure
# ─────────────────────────────────────────────────────────────────────────────

def test_single_track_intelligence_endpoint_structure(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify GET /api/v1/tracks/{track_id}/intelligence returns valid DefensiveIntelligenceSummary with priority."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp = client.get("/api/v1/tracks/TRK-INTEL-01/intelligence")
    assert resp.status_code == 200
    data = resp.json()

    # Validate against Pydantic schema
    summary = DefensiveIntelligenceSummary.model_validate(data)
    assert summary.track_id == "TRK-INTEL-01"
    assert summary.features is not None
    assert summary.anomaly is not None
    assert summary.trajectory is not None
    assert isinstance(summary.ingress_estimates, list)

    # Priority assertion (AI2-E / AI2-F)
    assert summary.priority is not None
    assert summary.priority.track_id == "TRK-INTEL-01"
    assert 0.0 <= summary.priority.priority_score <= 100.0
    assert summary.priority.priority_level in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
    assert len(summary.priority.factors) == 5

    # Factor reconciliation in API response
    sum_contrib = sum(f.contribution for f in summary.priority.factors)
    assert sum_contrib >= 0.0


def test_single_track_intelligence_not_found(client: TestClient, database: Session, rbac_user):
    """Verify 404 on missing track for single-track intelligence."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp = client.get("/api/v1/tracks/TRK-NONEXISTENT/intelligence")
    assert resp.status_code == 404


# ─────────────────────────────────────────────────────────────────────────────
# 2. Multi-Track Intelligence Summary Endpoint
# ─────────────────────────────────────────────────────────────────────────────

def test_multi_track_intelligence_summary_endpoint(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify GET /api/v1/intelligence/summary returns groups, formations, behaviors, priorities."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp = client.get("/api/v1/intelligence/summary")
    assert resp.status_code == 200
    data = resp.json()

    summary = MultiTrackIntelligenceSummary.model_validate(data)
    assert len(summary.groups) >= 1
    assert len(summary.formations) >= 1
    assert len(summary.behaviors) == 3
    assert len(summary.priorities) == 3

    # Verify Track 1 and Track 2 are clustered into a group
    group = summary.groups[0]
    assert "TRK-INTEL-01" in group.member_track_ids
    assert "TRK-INTEL-02" in group.member_track_ids
    assert group.member_count == 2

    # Verify formation
    formation = summary.formations[0]
    assert formation.synchronization_index > 0.80

    # Verify priorities
    p_map = {p.track_id: p for p in summary.priorities}
    assert "TRK-INTEL-01" in p_map
    assert "TRK-INTEL-02" in p_map
    assert "TRK-INTEL-03" in p_map
    assert p_map["TRK-INTEL-01"].priority_score >= 0.0


def test_multi_track_summary_empty_state(client: TestClient, database: Session, rbac_user):
    """Verify GET /api/v1/intelligence/summary returns empty arrays when no active tracks exist."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp = client.get("/api/v1/intelligence/summary")
    assert resp.status_code == 200
    data = resp.json()

    summary = MultiTrackIntelligenceSummary.model_validate(data)
    assert summary.groups == []
    assert summary.formations == []
    assert summary.behaviors == []
    assert summary.priorities == []
    assert summary.evaluated_at is not None


# ─────────────────────────────────────────────────────────────────────────────
# 3. Filtering and Query Parameters
# ─────────────────────────────────────────────────────────────────────────────

def test_multi_track_summary_track_id_filter(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify track_id filter isolates intelligence for a single track."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp = client.get("/api/v1/intelligence/summary?track_id=TRK-INTEL-03")
    assert resp.status_code == 200
    data = resp.json()

    summary = MultiTrackIntelligenceSummary.model_validate(data)
    assert len(summary.behaviors) == 1
    assert summary.behaviors[0].track_id == "TRK-INTEL-03"
    assert len(summary.priorities) == 1
    assert summary.priorities[0].track_id == "TRK-INTEL-03"
    assert len(summary.groups) == 0  # TRK-INTEL-03 is not in a group


def test_multi_track_summary_group_id_filter(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify group_id filter isolates intelligence for a specific group."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    # First fetch all to obtain the deterministic group_id
    all_resp = client.get("/api/v1/intelligence/summary")
    target_group_id = all_resp.json()["groups"][0]["group_id"]

    filtered_resp = client.get(f"/api/v1/intelligence/summary?group_id={target_group_id}")
    assert filtered_resp.status_code == 200
    data = filtered_resp.json()

    summary = MultiTrackIntelligenceSummary.model_validate(data)
    assert len(summary.groups) == 1
    assert summary.groups[0].group_id == target_group_id
    assert len(summary.behaviors) == 2
    assert all(b.track_id in ("TRK-INTEL-01", "TRK-INTEL-02") for b in summary.behaviors)


def test_multi_track_summary_priority_level_and_score_filters(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify min_priority_level and min_priority_score filtering."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    # Filter with min_priority_level=LOW (should return all)
    resp_low = client.get("/api/v1/intelligence/summary?min_priority_level=LOW")
    assert resp_low.status_code == 200
    assert len(resp_low.json()["priorities"]) >= 1

    # Filter with min_priority_score=0.0
    resp_score = client.get("/api/v1/intelligence/summary?min_priority_score=0.0")
    assert resp_score.status_code == 200
    assert len(resp_score.json()["priorities"]) == 3

    # Filter with unreachable score (min_priority_score=99.9)
    resp_high_score = client.get("/api/v1/intelligence/summary?min_priority_score=99.9")
    assert resp_high_score.status_code == 200
    assert len(resp_high_score.json()["priorities"]) == 0


def test_multi_track_summary_malformed_parameters(client: TestClient, database: Session, rbac_user):
    """Verify 422 Unprocessable Entity on malformed query parameters."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    # Invalid min_priority_level string
    resp_bad_level = client.get("/api/v1/intelligence/summary?min_priority_level=INVALID_LEVEL")
    assert resp_bad_level.status_code == 422

    # Negative min_priority_score
    resp_bad_score_low = client.get("/api/v1/intelligence/summary?min_priority_score=-10.0")
    assert resp_bad_score_low.status_code == 422

    # Excessive min_priority_score
    resp_bad_score_high = client.get("/api/v1/intelligence/summary?min_priority_score=150.0")
    assert resp_bad_score_high.status_code == 422


# ─────────────────────────────────────────────────────────────────────────────
# 4. Authentication and RBAC
# ─────────────────────────────────────────────────────────────────────────────

def test_intelligence_api_authentication_and_authorization(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify 401 for unauthenticated, 403 for unauthorized, and 200 for OPERATOR."""
    # 1. Unauthenticated -> 401
    assert client.get("/api/v1/tracks/TRK-INTEL-01/intelligence").status_code == 401
    assert client.get("/api/v1/intelligence/summary").status_code == 401

    # 2. Authenticated user without tracks.read -> 403
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert client.get("/api/v1/tracks/TRK-INTEL-01/intelligence").status_code == 403
    assert client.get("/api/v1/intelligence/summary").status_code == 403

    # 3. Grant OPERATOR role (has tracks.read) -> 200
    assign_role(database, rbac_user, "OPERATOR")
    assert client.get("/api/v1/tracks/TRK-INTEL-01/intelligence").status_code == 200
    assert client.get("/api/v1/intelligence/summary").status_code == 200


# ─────────────────────────────────────────────────────────────────────────────
# 5. Determinism & Idempotence
# ─────────────────────────────────────────────────────────────────────────────

def test_intelligence_summary_deterministic_repeated_requests(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify repeated requests return identical grouped structures and priorities."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp1 = client.get("/api/v1/intelligence/summary").json()
    resp2 = client.get("/api/v1/intelligence/summary").json()

    # Compare structural entities ignoring microsecond timestamps
    assert len(resp1["groups"]) == len(resp2["groups"])
    assert resp1["groups"][0]["group_id"] == resp2["groups"][0]["group_id"]
    assert len(resp1["formations"]) == len(resp2["formations"])
    assert resp1["formations"][0]["synchronization_index"] == resp2["formations"][0]["synchronization_index"]
    assert len(resp1["priorities"]) == len(resp2["priorities"])


# ─────────────────────────────────────────────────────────────────────────────
# 6. EventBus and Realtime Telemetry
# ─────────────────────────────────────────────────────────────────────────────

def test_intelligence_eventbus_dispatch(database: Session, test_tracks_and_geofences):
    """Verify intelligence evaluation dispatches ai.summary to RealtimeChannel.OPERATIONAL."""
    bus = get_event_bus()
    bus.reset()
    sub = bus.subscribe(RealtimeChannel.OPERATIONAL)

    t1 = test_tracks_and_geofences["t1"]
    geo = test_tracks_and_geofences["geofence"]

    # Trigger evaluation with event publishing enabled
    summary = DefensiveIntelligenceService.evaluate_track(
        database, t1, geofences=[geo], publish_events=True
    )
    assert summary is not None

    events = []
    while not sub.queue.empty():
        events.append(sub.queue.get_nowait())

    ai_events = [e for e in events if e.event_type == RealtimeEventType.AI_SUMMARY]
    assert len(ai_events) >= 1
    payload = ai_events[0].payload
    assert payload["track_id"] == "TRK-INTEL-01"
    assert "priority" in payload
    assert payload["priority"]["priority_score"] >= 0.0

    bus.unsubscribe(sub)


def test_multi_track_intelligence_eventbus_dispatch(test_tracks_and_geofences):
    """Verify multi-track intelligence evaluation dispatches ai.summary when publish_events=True."""
    bus = get_event_bus()
    bus.reset()
    sub = bus.subscribe(RealtimeChannel.OPERATIONAL)

    tracks = [
        test_tracks_and_geofences["t1"],
        test_tracks_and_geofences["t2"],
        test_tracks_and_geofences["t3"],
    ]

    summary = DefensiveIntelligenceService.evaluate_multi_track_intelligence(
        tracks, publish_events=True
    )
    assert summary is not None

    events = []
    while not sub.queue.empty():
        events.append(sub.queue.get_nowait())

    multi_events = [
        e for e in events
        if e.event_type == RealtimeEventType.AI_SUMMARY and e.resource_type == "multi_track_intelligence"
    ]
    assert len(multi_events) >= 1
    assert "groups" in multi_events[0].payload
    assert "priorities" in multi_events[0].payload

    bus.unsubscribe(sub)


def test_websocket_operational_receives_intelligence_events(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify authenticated /ws/operational WebSocket client receives AI intelligence events."""
    from app.core.config import get_settings
    from app.services.auth import create_session

    settings = get_settings()
    assign_role(database, rbac_user, "OPERATOR")
    _, raw_secret = create_session(database, rbac_user, "127.0.0.1", "test-agent")

    t1 = test_tracks_and_geofences["t1"]
    geo = test_tracks_and_geofences["geofence"]

    with client.websocket_connect(
        "/api/v1/ws/operational",
        cookies={settings.session_cookie_name: raw_secret},
    ) as ws:
        # Receive greeting envelope
        greeting = ws.receive_json()
        assert greeting["event_type"] == "system.heartbeat"
        assert greeting["channel"] == "operational"

        # Emit an intelligence event via service
        DefensiveIntelligenceService.evaluate_track(
            database, t1, geofences=[geo], publish_events=True
        )

        # Receive AI intelligence event on websocket
        event_data = ws.receive_json()
        assert event_data["event_type"] == "ai.summary"
        assert event_data["channel"] == "operational"
        assert event_data["payload"]["track_id"] == "TRK-INTEL-01"
        assert "priority" in event_data["payload"]


def test_intelligence_summary_schema_and_timestamp_validation(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify UTC ISO timestamp format and complete schema serialization on multi-track summary."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp = client.get("/api/v1/intelligence/summary")
    assert resp.status_code == 200
    data = resp.json()

    # Verify timestamp presence and ISO parseability
    assert "evaluated_at" in data
    eval_ts = datetime.fromisoformat(data["evaluated_at"].replace("Z", "+00:00"))
    assert eval_ts.tzinfo is not None

    # Verify each group, behavior, formation, and priority entry has valid schema
    for grp in data["groups"]:
        assert "group_id" in grp
        assert "member_track_ids" in grp
        assert "centroid_lat" in grp
        assert "centroid_lon" in grp
        assert "radius_meters" in grp
        assert "confidence" in grp

    for b in data["behaviors"]:
        assert "track_id" in b
        assert "state" in b
        assert "confidence" in b
        assert "reason" in b

    for f in data["formations"]:
        assert "formation_id" in f
        assert "synchronization_index" in f
        assert 0.0 <= f["synchronization_index"] <= 1.0

    for p in data["priorities"]:
        assert "track_id" in p
        assert "priority_score" in p
        assert 0.0 <= p["priority_score"] <= 100.0
        assert p["priority_level"] in ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        assert len(p["factors"]) == 5
        for factor in p["factors"]:
            assert "name" in factor
            assert "score" in factor
            assert "weight" in factor
            assert "contribution" in factor
            assert "description" in factor


def test_single_track_priority_factor_reconciliation(client: TestClient, database: Session, rbac_user, test_tracks_and_geofences):
    """Verify explainable priority factor contributions mathematically reconcile with base score."""
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assign_role(database, rbac_user, "OPERATOR")

    resp = client.get("/api/v1/tracks/TRK-INTEL-01/intelligence")
    assert resp.status_code == 200
    prio = resp.json()["priority"]
    assert prio is not None

    # Sum of factor contributions
    sum_contributions = sum(f["contribution"] for f in prio["factors"])
    # Scaled priority score
    conf = prio["confidence"]
    scale = 0.30 + (0.70 * conf)
    expected_final = round(max(0.0, min(100.0, sum_contributions * scale)), 1)
    assert abs(prio["priority_score"] - expected_final) <= 0.1
