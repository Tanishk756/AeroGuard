# AeroGuard Stage IM1 — Checkpoint IM1-D Report
**Incident EventBus, Realtime Streaming & Correlation Layer**

---

**Date**: 2026-08-29
**Dev Environment**: Windows 11 / Python 3.12 / TypeScript / Vite / Tauri / SQLite
**Scope**: Defensive Situational Awareness & Operational Workflow Only
**Starting Baseline Commit**: `a1eb86c` (`feat: expose incident REST API with RBAC (IM1-C)`)
**IM1-D Implementation Commit**: `af58f37` (`feat: integrate incident events with realtime pipeline (IM1-D)`)
**Final Checkpoint Commit**: `af58f37` + test expansion

---

## 1. Executive Summary

Checkpoint **IM1-D** connects AeroGuard's Incident Management domain to the platform's EventBus and WebSocket realtime broadcast infrastructure. Every incident lifecycle transition, assignment update, operator note, and logged defensive action is deterministically published as a typed realtime event over `/ws/operational` upon successful transaction commit.

This implementation satisfies all defensive situational-awareness constraints:
- **Strictly Defensive**: Zero offensive, kinetic, interception, fire-control, or jamming countermeasures.
- **Transactional Outbox Hooks**: SQLAlchemy session listeners (`@sa_event.listens_for(Session, "after_commit")` / `after_rollback`) guarantee zero premature or orphan event emissions on database rollbacks.
- **Backpressure Protection**: All 11 incident realtime event types are classified as `CRITICAL_EVENT_TYPES` within `backend/app/core/events.py`, preventing eviction during high-density telemetry bursts.
- **Multi-Entity Correlation**: Seamless preservation of track, swarm group, alert, and historical intelligence identifiers across REST, database, EventBus, and WebSocket channels.
- **Strict RBAC Stream Filtering**: WebSocket clients streaming `/ws/operational` require `incidents.read` permission to receive incident events, preventing data leakage to unauthorized roles while preserving track and alert streams for other roles.

---

## 2. Incident Realtime Event Inventory

Eleven deterministic event types are registered under `RealtimeEventType` in `backend/app/schemas/events.py`:

| Event Enum Variant | Wire Value (`event_type`) | Triggering Service Method | Description |
|---|---|---|---|
| `INCIDENT_CREATED` | `incident.created` | `create_incident` | Initial incident creation (`NEW` status) |
| `INCIDENT_ACKNOWLEDGED` | `incident.acknowledged` | `acknowledge_incident` | Operator acknowledgement (`ACKNOWLEDGED` status) |
| `INCIDENT_ASSIGNED` | `incident.assigned` | `assign_incident` | Initial operator/analyst assignment |
| `INCIDENT_REASSIGNED` | `incident.reassigned` | `assign_incident` | Reassignment from previous assignee to new assignee |
| `INCIDENT_TRIAGED` | `incident.triaged` | `triage_incident` | Severity/assessment update (`TRIAGED` status) |
| `INCIDENT_ESCALATED` | `incident.escalated` | `escalate_incident` | Escalation transition (`ESCALATED` status) |
| `INCIDENT_DE_ESCALATED` | `incident.de_escalated` | `de_escalate_incident` | De-escalation transition |
| `INCIDENT_RESOLVED` | `incident.resolved` | `resolve_incident` | Resolution summary logged (`RESOLVED` status) |
| `INCIDENT_CLOSED` | `incident.closed` | `close_incident` | Administrative closure (`CLOSED` status) |
| `INCIDENT_NOTE_ADDED` | `incident.note_added` | `add_note` | Operator observation or timeline note added |
| `INCIDENT_ACTION_LOGGED` | `incident.action_logged` | `log_defensive_action` | Procedural defensive review action logged |

---

## 3. Realtime Event Envelope & Payload Schemas

### 3.1 Event Envelope (`RealtimeEventEnvelope`)
```python
class RealtimeEventEnvelope(BaseModel):
    event_id: str = Field(default_factory=lambda: str(uuid.uuid4()), min_length=1, max_length=64)
    event_type: str = Field(min_length=1, max_length=64)
    channel: str = Field(min_length=1, max_length=32)
    sequence: int = Field(ge=1)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    resource_type: str | None = Field(default=None, max_length=64)
    resource_id: str | None = Field(default=None, max_length=128)
    correlation_id: str | None = Field(default=None, max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
```

### 3.2 Incident Payload Schema (`IncidentRealtimePayload`)
```python
class IncidentRealtimePayload(BaseModel):
    incident_id: str = Field(min_length=1, max_length=64)
    incident_number: str = Field(min_length=1, max_length=64)
    title: str = Field(min_length=1, max_length=256)
    status: str = Field(min_length=1, max_length=32)
    previous_status: str | None = Field(default=None, max_length=32)
    severity: str = Field(min_length=1, max_length=32)
    previous_severity: str | None = Field(default=None, max_length=32)
    source: str = Field(min_length=1, max_length=32)
    primary_track_id: str | None = Field(default=None, max_length=64)
    primary_group_id: str | None = Field(default=None, max_length=64)
    originating_alert_id: str | None = Field(default=None, max_length=64)
    originating_intelligence_event_id: str | None = Field(default=None, max_length=64)
    assigned_to: str | None = Field(default=None, max_length=64)
    previous_assignee: str | None = Field(default=None, max_length=64)
    actor_user_id: str | None = Field(default=None, max_length=64)
    incident_event_id: str = Field(min_length=1, max_length=64)
    incident_event_sequence: int = Field(ge=1)
    incident_event_type: str = Field(min_length=1, max_length=32)
    category: str | None = Field(default=None, max_length=64)
    message: str | None = Field(default=None, max_length=2048)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

---

## 4. Key Architectural Mechanisms

### 4.1 Event Sequencing Model
- **Realtime Transport Sequence**: The EventBus assigns an atomic monotonic `sequence` integer (`1, 2, 3...`) to every envelope dispatched over `RealtimeChannel.OPERATIONAL`.
- **Incident Timeline Sequence**: The underlying `incident_event_sequence` (`1, 2, 3...`) tracks the exact chronological progression within that specific incident, allowing clients to reconstruct the timeline or detect gaps.

### 4.2 Transactional Outbox Hooks (`after_commit` / `after_rollback`)
1. During `IncidentService` mutation methods, validated payloads are buffered in `session.info["_pending_incident_events"]`.
2. `@sa_event.listens_for(Session, "after_commit")` drains the pending buffer and publishes each event to `EventBus`.
3. `@sa_event.listens_for(Session, "after_rollback")` clears the pending buffer, guaranteeing **zero phantom events** on database rollback.
4. If a transient error occurs during event publication, the error is logged while the committed database state remains durable.

### 4.3 WebSocket Security & RBAC Stream Filtering
- WebSocket clients connecting to `/api/v1/ws/operational` must present a valid HttpOnly session cookie during the connection handshake.
- Handshake validates active status and permissions.
- In `ws.py`, `_operational_filter` checks `AuthorizationService(db).has_permission(user, "incidents.read")`: clients lacking `incidents.read` continue streaming tracks and alerts but receive 0 incident events.

### 4.4 Multi-Entity Correlation Model
- `primary_track_id`: Links the incident to a specific fused track.
- `primary_group_id`: Links the incident to an AI swarm cluster or formation.
- `originating_alert_id`: Links the incident to a threshold or perimeter geofence alert.
- `originating_intelligence_event_id`: Links the incident to an immutable historical intelligence snapshot.
- Missing or standalone correlations cleanly serialize as `null`.

---

## 5. Comprehensive Verification Evidence

### 5.1 Focused IM1-D Test Matrix (31 Tests)
- `backend/tests/test_incident_eventbus.py`: 19 tests covering contracts, creation, lifecycle (10 operations), invalid transition rejection, deduplication, rollback suppression, bus error recovery, monotonic sequencing, deterministic timeline ordering, and critical backpressure queue eviction.
- `backend/tests/test_incident_realtime.py`: 7 tests verifying live `/ws/operational` streaming during REST mutations, non-interference with concurrent AI telemetry, unauthenticated disconnect rejection, and ping-pong heartbeat exchange.
- `backend/tests/test_incident_correlation.py`: 5 tests verifying track, swarm group, alert, historical intelligence correlation round-trips, and null serialization for standalone incidents.

### 5.2 Full System Regression Results
| Suite / Verification Area | Command | Result |
| :--- | :--- | :--- |
| **All Incident Subsystem Tests** | `pytest backend/tests/test_incident_*.py` | **102 / 102 Passed (100%)** |
| **Full Backend Regression Suite** | `pytest -q` | **564 / 564 Passed (100%)** in 56.25s |
| **Frontend Operator Unit Tests** | `npm test` | **246 / 246 Passed (100%)** across 101 suites |
| **Frontend TypeScript Typecheck** | `npm --prefix apps/operator run typecheck` | **Clean (0 errors)** |
| **Frontend Vite Production Build** | `npm --prefix apps/operator run build` | **Clean production bundle** |
| **Desktop Tauri Checks** | `cargo test`, `cargo check` | **Clean (0 errors, 0 warnings)** |
| **Git Diff Format & Whitespace** | `git diff --check` | **Clean** |
| **Security Credential Scan** | `git grep -n -i -E ...` | **Clean (0 hardcoded credentials or token leaks)** |
| **Defensive Safety Boundary Scan** | `git grep -n -i -E ...` | **Clean (0 offensive or kinetic capabilities)** |

---

## 6. Defensive Safety & Security Audit

- **No Credential Persistence**: 0 usage of `localStorage`, `sessionStorage`, or `indexedDB` for auth tokens.
- **Audit Logging**: All authorization denials and incident mutations record structured `AuditEvent` rows with correlation IDs.
- **Defensive Boundary**: Incident management is strictly an operational workflow, review, and audit tool. All logged actions (`SENSOR_REVIEW`, `TRACK_CORRELATION_REVIEW`, `OPERATOR_CONTACT`, `SUPERVISOR_ESCALATION`, `PROCEDURE_REVIEW`, `SCENARIO_REVIEW`, `OTHER`) are analytical and procedural records without hardware kinetic execution.

---

## 7. Known Limitations & Deferred Work

1. **Frontend Operator Incident UI**: Operator console incident triage workspace, incident details drawer, and timeline components are deferred to **IM1-E**.
2. **Tactical Map Overlays**: Visual incident markers, bounding boxes, and correlation overlays on the MAP2 tactical map are deferred to **IM1-F**.
