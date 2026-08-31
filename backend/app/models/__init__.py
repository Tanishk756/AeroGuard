"""SQLAlchemy models."""

from app.models.association import TrackAssociation, TrackAssociationDecision
from app.models.audit import AuditEvent
from app.models.alert import Alert, AlertSeverity, AlertStatus, AlertType
from app.models.detection import Detection
from app.models.geofence import Geofence
from app.models.session import Session
from app.models.incident import (
    Incident,
    IncidentSeverity,
    IncidentSource,
    IncidentStatus,
    InvalidIncidentTransitionError,
    VALID_INCIDENT_TRANSITIONS,
    can_transition,
    validate_transition,
)
from app.models.incident_event import (
    DefensiveActionCategory,
    IncidentEvent,
    IncidentEventType,
)
from app.models.intelligence_history import (
    BehaviorEventHistory,
    IntelligenceSnapshot,
    TrackGroupHistory,
)
from app.models.permission import Permission
from app.models.role import Role
from app.models.user import User, UserStatus
from app.models.scenario import Scenario, ScenarioStatus
from app.models.sensor import Sensor, SensorSourceClass, SensorStatus
from app.models.threat import ThreatAssessment, ThreatLevel
from app.models.track import Track, TrackHistory, TrackState
from app.models.scheduler import SchedulerLock
from app.models.simulation_platform import (
    PersistentSimulationScenario,
    PersistentSimulationRun,
)
from app.models.hardware_registry import (
    PersistentHardwareComponent,
    PersistentVehicle,
)
from app.models.snapshot import PersistentSimulationRunSnapshot
from app.models.scenario_world import (
    PersistentSimulationWorld,
    PersistentWorldObject,
    PersistentScenarioEntity,
)
from app.models.incident_export import (
    IncidentExport,
    IncidentExportFormat,
    IncidentExportStatus,
)

__all__ = [
    "Alert", "AlertSeverity", "AlertStatus", "AlertType", "AuditEvent", "BehaviorEventHistory",
    "DefensiveActionCategory", "Detection", "Geofence", "Incident", "IncidentEvent",
    "IncidentEventType", "IncidentExport", "IncidentExportFormat", "IncidentExportStatus",
    "IncidentSeverity", "IncidentSource", "IncidentStatus",
    "IntelligenceSnapshot", "InvalidIncidentTransitionError", "Permission", "Role", "Scenario",
    "ScenarioStatus", "SchedulerLock", "Sensor", "SensorSourceClass", "SensorStatus", "Session",
    "ThreatAssessment", "ThreatLevel", "Track", "TrackAssociation", "TrackAssociationDecision",
    "TrackGroupHistory", "TrackHistory", "TrackState", "User", "UserStatus",
    "VALID_INCIDENT_TRANSITIONS", "can_transition", "validate_transition",
]
