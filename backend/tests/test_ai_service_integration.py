"""Integration tests for AeroGuard AI defensive intelligence service, EventBus, and API."""

from datetime import UTC, datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.schemas import DefensiveIntelligenceSummary
from ai.service import DefensiveIntelligenceService
from app.core.events import get_event_bus
from app.models.detection import Detection
from app.models.geofence import Geofence
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.track import Track, TrackHistory, TrackState
from app.schemas.events import RealtimeChannel, RealtimeEventType
from app.tracking.service import TrackingService


def test_ai_service_track_evaluation_and_event_publishing(database: Session):
    """Verify DefensiveIntelligenceService evaluates track and publishes ai.summary to EventBus."""
    bus = get_event_bus()
    bus.reset()
    sub = bus.subscribe(RealtimeChannel.OPERATIONAL)

    now = datetime.now(UTC).replace(tzinfo=None)

    # 1. Create track with history
    track = Track(
        id="TRK-AI-001",
        state=TrackState.ACTIVE,
        first_seen_at=now - timedelta(seconds=20),
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=120.0,
        velocity=25.0,
        heading=45.0,
        confidence=0.95,
        classification="UAV_ROTARY",
        source_count=2,
        created_at=now,
        updated_at=now,
    )
    database.add(track)

    for i in range(5):
        hist = TrackHistory(
            track_id="TRK-AI-001",
            sequence=i + 1,
            timestamp=now - timedelta(seconds=20 - (i * 4)),
            latitude=37.7749 + (i * 0.0002),
            longitude=-122.4194 + (i * 0.0002),
            altitude=120.0,
            velocity=25.0,
            heading=45.0,
            confidence=0.95,
            state=TrackState.ACTIVE,
            provenance=SensorSourceClass.REAL,
            source_detection_ids=[f"DET-{i}"],
            created_at=now,
        )
        database.add(hist)
    database.commit()

    # 2. Add defensive geofence
    geofence = Geofence(
        id="GEO-AI-01",
        name="Sector Alpha",
        geometry={"type": "BBOX", "min_lat": 37.7800, "max_lat": 37.7900, "min_lon": -122.4200, "max_lon": -122.4000},
        enabled=True,
        created_at=now,
        updated_at=now,
    )
    database.add(geofence)
    database.commit()

    # 3. Evaluate track
    summary = DefensiveIntelligenceService.evaluate_track(
        database, track, geofences=[geofence], publish_events=True
    )

    assert summary is not None
    assert summary.track_id == "TRK-AI-001"
    assert summary.features.sample_count >= 5
    assert summary.anomaly.sensor_confidence > 0.7
    assert len(summary.trajectory.waypoints) == 12  # 60s / 5s = 12 waypoints
    assert len(summary.ingress_estimates) == 1

    # Verify event was published to EventBus
    events = []
    while not sub.queue.empty():
        events.append(sub.queue.get_nowait())

    ai_events = [e for e in events if e.event_type == RealtimeEventType.AI_SUMMARY]
    assert len(ai_events) >= 1
    assert ai_events[0].payload["track_id"] == "TRK-AI-001"

    bus.unsubscribe(sub)


def test_track_intelligence_api_endpoint(client: TestClient, database: Session, rbac_user):
    """Verify /api/v1/tracks/{track_id}/intelligence permissions and schema."""
    now = datetime.now(UTC).replace(tzinfo=None)
    track = Track(
        id="TRK-AI-002",
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=100.0,
        velocity=15.0,
        heading=90.0,
        confidence=0.9,
        classification="DRONE",
        source_count=1,
        created_at=now,
        updated_at=now,
    )
    database.add(track)
    database.commit()

    # 1. Unauthenticated -> 401
    resp = client.get("/api/v1/tracks/TRK-AI-002/intelligence")
    assert resp.status_code == 401

    # 2. Authenticated with viewer (no tracks.read) -> 403
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )
    assert client.get("/api/v1/tracks/TRK-AI-002/intelligence").status_code == 403

    # 3. Grant OPERATOR role (which has tracks.read) -> 200
    from app.models.role import Role
    role = database.scalar(select(Role).where(Role.name == "OPERATOR"))
    rbac_user.roles.append(role)
    database.commit()

    intel_resp = client.get("/api/v1/tracks/TRK-AI-002/intelligence")
    assert intel_resp.status_code == 200
    data = intel_resp.json()

    assert data["track_id"] == "TRK-AI-002"
    assert "features" in data
    assert "anomaly" in data
    assert "trajectory" in data
    assert "ingress_estimates" in data
    assert data["anomaly"]["anomaly_score"] >= 0.0

    # 4. Unknown track -> 404
    unknown_resp = client.get("/api/v1/tracks/TRK-NONEXISTENT/intelligence")
    assert unknown_resp.status_code == 404
