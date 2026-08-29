"""Tests for historical defensive intelligence analytics and endpoints (Stage HI1-D)."""

from datetime import UTC, datetime, timedelta
import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.testclient import TestClient

from ai.schemas import (
    BehaviorClassification,
    BehavioralState,
    CoordinatedFormation,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    TrackGroup,
)
from app.analytics.service import AnalyticsService
from app.history.intelligence import IntelligencePersistenceService
from app.models.user import User


@pytest.fixture
def populated_intelligence_db(database: Session):
    now = datetime(2026, 8, 29, 12, 0, 0, tzinfo=UTC)
    persistence = IntelligencePersistenceService()

    # 1. First snapshot at T=0
    summary_1 = MultiTrackIntelligenceSummary(
        groups=[
            TrackGroup(
                group_id="GRP-101",
                member_track_ids=["TRK-1", "TRK-2", "TRK-3"],
                member_count=3,
                centroid_lat=37.7750,
                centroid_lon=-122.4190,
                radius_meters=60.0,
                behavioral_state="COORDINATED",
                updated_at=now,
            )
        ],
        behaviors=[
            BehaviorClassification(
                track_id="TRK-1",
                state=BehavioralState.COORDINATED,
                confidence=0.92,
                duration_seconds=8.0,
                reason="Formation flight",
                evaluated_at=now,
            )
        ],
        formations=[
            CoordinatedFormation(
                formation_id="FMT-101",
                group_id="GRP-101",
                member_track_ids=["TRK-1", "TRK-2", "TRK-3"],
                synchronization_index=0.88,
                heading_dispersion_deg=3.5,
                velocity_dispersion_mps=0.4,
                confidence=0.92,
                evaluated_at=now,
            )
        ],
        priorities=[
            ThreatPriorityAssessment(
                track_id="TRK-1",
                priority_score=60.0,
                priority_level="MEDIUM",
                confidence=0.90,
                reason="Coordinated group movement",
                evaluated_at=now,
            )
        ],
        evaluated_at=now,
    )

    # 2. Second snapshot at T=10
    summary_2 = MultiTrackIntelligenceSummary(
        groups=[
            TrackGroup(
                group_id="GRP-101",
                member_track_ids=["TRK-1", "TRK-2", "TRK-3"],
                member_count=3,
                centroid_lat=37.7760,
                centroid_lon=-122.4180,
                radius_meters=55.0,
                behavioral_state="APPROACHING",
                updated_at=now + timedelta(seconds=10),
            )
        ],
        behaviors=[
            BehaviorClassification(
                track_id="TRK-1",
                state=BehavioralState.APPROACHING,
                confidence=0.96,
                duration_seconds=18.0,
                reason="Approach toward perimeter",
                evaluated_at=now + timedelta(seconds=10),
            )
        ],
        formations=summary_1.formations,
        priorities=[
            ThreatPriorityAssessment(
                track_id="TRK-1",
                priority_score=85.0,
                priority_level="CRITICAL",
                confidence=0.95,
                reason="Critical perimeter breach threat",
                evaluated_at=now + timedelta(seconds=10),
            )
        ],
        evaluated_at=now + timedelta(seconds=10),
    )

    persistence.record_summary_snapshot(summary_1, force=True, now=now)
    persistence.record_group_history(summary_1.groups[0], coordination_index=0.88, now=now)
    persistence.record_behavior_event(
        track_id="TRK-1",
        previous_state="NORMAL",
        new_state="COORDINATED",
        duration_seconds=8.0,
        confidence=0.92,
        reasons=["Formation flight"],
        now=now,
    )

    persistence.record_summary_snapshot(summary_2, force=True, now=now + timedelta(seconds=10))
    persistence.record_group_history(summary_2.groups[0], coordination_index=0.92, now=now + timedelta(seconds=10))
    persistence.record_behavior_event(
        track_id="TRK-1",
        previous_state="COORDINATED",
        new_state="APPROACHING",
        duration_seconds=18.0,
        confidence=0.96,
        reasons=["Approach toward perimeter"],
        now=now + timedelta(seconds=10),
    )

    persistence.flush(db=database)
    return now


def test_analytics_service_get_intelligence_metrics(database: Session, populated_intelligence_db):
    base_time = populated_intelligence_db
    service = AnalyticsService(database)

    report = service.get_intelligence_metrics(
        start_time=base_time - timedelta(minutes=1),
        end_time=base_time + timedelta(minutes=1),
    )

    assert report.total_snapshots == 2
    assert report.total_group_events == 2
    assert report.total_behavior_transitions == 2
    assert report.peak_threat_score == 85.0
    assert report.max_group_size == 3
    assert report.avg_group_size == 3.0
    assert report.avg_coordination_index == 0.90
    assert "COORDINATED" in report.group_state_distribution
    assert "APPROACHING" in report.group_state_distribution
    assert "COORDINATED" in report.behavior_distribution
    assert "APPROACHING" in report.behavior_distribution
    assert len(report.coordination_peaks) == 2
    assert len(report.threat_score_time_series) == 2


def test_analytics_summary_includes_intelligence(database: Session, populated_intelligence_db):
    base_time = populated_intelligence_db
    service = AnalyticsService(database)

    summary = service.get_summary(
        window_start=base_time - timedelta(minutes=1),
        window_end=base_time + timedelta(minutes=1),
    )

    assert summary.intelligence is not None
    assert summary.intelligence.total_snapshots == 2
    assert summary.intelligence.peak_threat_score == 85.0


from app.models.role import Role


def assign_role(database: Session, user: User, role_name: str):
    role = database.scalar(select(Role).where(Role.name == role_name))
    if role not in user.roles:
        user.roles.append(role)
        database.commit()


def test_api_get_intelligence_analytics(client: TestClient, database: Session, rbac_user: User, populated_intelligence_db):
    base_time = populated_intelligence_db

    assign_role(database, rbac_user, "OPERATIONS_ADMIN")
    client.post(
        "/api/v1/auth/login",
        json={"identifier": rbac_user.username, "password": "stage-d-test-password"},
    )

    response = client.get(
        "/api/v1/analytics/intelligence",
        params={
            "start_time": (base_time - timedelta(minutes=1)).isoformat(),
            "end_time": (base_time + timedelta(minutes=1)).isoformat(),
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_snapshots"] == 2
    assert data["peak_threat_score"] == 85.0
    assert data["avg_coordination_index"] == 0.90
    assert len(data["threat_score_time_series"]) == 2
    assert len(data["coordination_peaks"]) == 2


def test_api_get_intelligence_unauthorized(client: TestClient):
    response = client.get("/api/v1/analytics/intelligence")
    assert response.status_code == 401
