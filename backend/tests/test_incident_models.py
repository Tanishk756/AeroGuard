"""Unit tests for Stage IM1 Incident and IncidentEvent database models."""

from datetime import UTC, datetime
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.database.base import Base
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
)
from app.models.incident_event import (
    DefensiveActionCategory,
    IncidentEvent,
    IncidentEventType,
)
from app.models.track import Track, TrackState
from app.models.user import User, UserStatus


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    session = session_factory()
    yield session
    session.close()


def test_incident_model_instantiation(db_session: Session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    incident = Incident(
        incident_number="INC-2026-0001",
        title="Unidentified High-Speed Formation Entry",
        description="Two tracks exhibiting coordinated high-velocity flight towards Perimeter North.",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.HIGH,
        source=IncidentSource.INTELLIGENCE,
        primary_group_id="GRP-104",
        created_at=now,
        updated_at=now,
        metadata_json={"detection_count": 12, "coordination_index": 0.88},
    )
    db_session.add(incident)
    db_session.commit()

    saved = db_session.get(Incident, incident.id)
    assert saved is not None
    assert saved.incident_number == "INC-2026-0001"
    assert saved.title == "Unidentified High-Speed Formation Entry"
    assert saved.status == IncidentStatus.NEW
    assert saved.severity == IncidentSeverity.HIGH
    assert saved.source == IncidentSource.INTELLIGENCE
    assert saved.primary_group_id == "GRP-104"
    assert saved.primary_track_id is None
    assert saved.originating_alert_id is None
    assert saved.created_by is None
    assert saved.acknowledged_at is None
    assert saved.metadata == {"detection_count": 12, "coordination_index": 0.88}


def test_incident_correlations_and_relationships(db_session: Session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)

    user = User(
        username="operator_dronis",
        email="dronis@aeroguard.internal",
        password_hash="hash_placeholder",
        display_name="Operator Dronis",
        status=UserStatus.ACTIVE,
    )
    db_session.add(user)

    track = Track(
        state=TrackState.ACTIVE,
        first_seen_at=now,
        last_seen_at=now,
        latitude=37.7749,
        longitude=-122.4194,
        altitude=180.0,
        velocity=22.5,
        heading=135.0,
        confidence=0.92,
        classification="UAV_ROTARY",
    )
    db_session.add(track)
    db_session.flush()

    alert = Alert(
        type=AlertType.GEOFENCE_BREACH,
        severity=AlertSeverity.HIGH,
        status=AlertStatus.OPEN,
        track_id=track.id,
        reason="Defensive zone northern corridor breach detected",
        metadata_json={"zone_id": "ZONE-ALPHA"},
        created_at=now,
        updated_at=now,
    )
    db_session.add(alert)
    db_session.flush()

    incident = Incident(
        incident_number="INC-2026-0002",
        title="Corridor Alpha Ingress Incident",
        status=IncidentStatus.ACKNOWLEDGED,
        severity=IncidentSeverity.CRITICAL,
        source=IncidentSource.ALERT,
        primary_track_id=track.id,
        originating_alert_id=alert.id,
        originating_intelligence_event_id="EVT-AI-992",
        created_by=user.id,
        acknowledged_by=user.id,
        assigned_to=user.id,
        acknowledged_at=now,
        assigned_at=now,
    )
    db_session.add(incident)
    db_session.commit()

    saved = db_session.get(Incident, incident.id)
    assert saved is not None
    assert saved.primary_track is not None
    assert saved.primary_track.id == track.id
    assert saved.originating_alert is not None
    assert saved.originating_alert.id == alert.id
    assert saved.creator is not None
    assert saved.creator.username == "operator_dronis"
    assert saved.assignee is not None
    assert saved.assignee.username == "operator_dronis"
    assert saved.originating_intelligence_event_id == "EVT-AI-992"


def test_incident_timeline_event_logging(db_session: Session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)

    incident = Incident(
        incident_number="INC-2026-0003",
        title="Tactical Sensor Anomaly Tracking",
        status=IncidentStatus.NEW,
        severity=IncidentSeverity.LOW,
        source=IncidentSource.OPERATOR,
    )
    db_session.add(incident)
    db_session.flush()

    event1 = IncidentEvent(
        incident_id=incident.id,
        timestamp=now,
        event_type=IncidentEventType.CREATED,
        new_status=IncidentStatus.NEW,
        message="Incident created by system ingestion monitor.",
    )
    event2 = IncidentEvent(
        incident_id=incident.id,
        timestamp=now,
        event_type=IncidentEventType.ACTION_LOGGED,
        category=DefensiveActionCategory.SENSOR_REVIEW,
        message="Initiated multi-radar Doppler profile verification.",
        metadata_json={"sensor_ids": ["RADAR-01", "RADAR-02"]},
    )
    db_session.add_all([event1, event2])
    db_session.commit()

    saved_incident = db_session.get(Incident, incident.id)
    assert saved_incident is not None
    assert len(saved_incident.events) == 2
    assert saved_incident.events[0].event_type == IncidentEventType.CREATED
    assert saved_incident.events[1].event_type == IncidentEventType.ACTION_LOGGED
    assert saved_incident.events[1].category == DefensiveActionCategory.SENSOR_REVIEW
    assert saved_incident.events[1].metadata == {"sensor_ids": ["RADAR-01", "RADAR-02"]}


def test_incident_event_immutability_enforcement(db_session: Session) -> None:
    now = datetime.now(UTC).replace(tzinfo=None)
    incident = Incident(
        incident_number="INC-2026-0004",
        title="Immutable Timeline Test Incident",
    )
    db_session.add(incident)
    db_session.flush()

    event = IncidentEvent(
        incident_id=incident.id,
        timestamp=now,
        event_type=IncidentEventType.CREATED,
        message="Initial record",
    )
    db_session.add(event)
    db_session.commit()

    # Mutation attempt: Update
    event.message = "Altered message"
    with pytest.raises(ValueError, match="Incident timeline events are immutable"):
        db_session.commit()
    db_session.rollback()

    # Mutation attempt: Delete
    db_session.delete(event)
    with pytest.raises(ValueError, match="Incident timeline events are immutable"):
        db_session.commit()
    db_session.rollback()


def test_incident_metadata_property_setter_getter(db_session: Session) -> None:
    incident = Incident(
        incident_number="INC-2026-0005",
        title="Metadata Property Test",
    )
    assert incident.metadata == {}
    incident.metadata = {"tag": "defensive_drill", "priority_weight": 1.4}
    assert incident.metadata_json == {"tag": "defensive_drill", "priority_weight": 1.4}
    assert incident.metadata["tag"] == "defensive_drill"
