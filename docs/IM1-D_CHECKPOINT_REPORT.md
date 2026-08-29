# AeroGuard Stage IM1 — Checkpoint IM1-D Report
**Incident EventBus, Realtime Streaming & Correlation Layer**

---

## 1. Executive Summary

Stage IM1 Checkpoint IM1-D connects AeroGuard's Incident Management domain to the platform's EventBus and WebSocket realtime broadcast infrastructure. Every incident lifecycle transition, assignment update, operator note, and logged defensive action is deterministically published as a typed realtime event over `/ws/operational` upon successful transaction commit.

This implementation satisfies all defensive situational-awareness constraints:
- Zero offensive, kinetic, interception, or fire-control countermeasures.
- Strict transactional outbox semantics (`after_commit` / `after_rollback` listeners) guaranteeing zero premature or orphan event emissions on database rollbacks.
- Event prioritization: All 11 incident realtime events are classified as `CRITICAL_EVENT_TYPES` to protect against subscriber queue backpressure drops.
- Multi-entity correlation: Seamless preservation of track, swarm group, alert, and historical intelligence identifiers across REST, database, EventBus, and WebSocket channels.
- Strict RBAC stream filtering: WebSocket clients streaming `/ws/operational` require `incidents.read` permission to receive incident events, preserving existing track and alert streams for other roles.

---

## 2. Realtime Event Contracts & Schema Extensions

### 2.1 Event Types (`backend/app/schemas/events.py`)
Eleven new event types were added to `RealtimeEventType`:
1. `incident.created` (`RealtimeEventType.INCIDENT_CREATED`)
2. `incident.acknowledged` (`RealtimeEventType.INCIDENT_ACKNOWLEDGED`)
3. `incident.assigned` (`RealtimeEventType.INCIDENT_ASSIGNED`)
4. `incident.reassigned` (`RealtimeEventType.INCIDENT_REASSIGNED`)
5. `incident.triaged` (`RealtimeEventType.INCIDENT_TRIAGED`)
6. `incident.escalated` (`RealtimeEventType.INCIDENT_ESCALATED`)
7. `incident.de_escalated` (`RealtimeEventType.INCIDENT_DE_ESCALATED`)
8. `incident.resolved` (`RealtimeEventType.INCIDENT_RESOLVED`)
9. `incident.closed` (`RealtimeEventType.INCIDENT_CLOSED`)
10. `incident.note_added` (`RealtimeEventType.INCIDENT_NOTE_ADDED`)
11. `incident.action_logged` (`RealtimeEventType.INCIDENT_ACTION_LOGGED`)

### 2.2 Payload Contract (`IncidentRealtimePayload`)
```python
class IncidentRealtimePayload(BaseModel):
    incident_id: str = Field(..., min_length=1, max_length=36)
    incident_number: str = Field(..., min_length=1, max_length=64)
    title: str = Field(..., min_length=1, max_length=200)
    status: str = Field(..., min_length=1, max_length=32)
    previous_status: str | None = Field(None, max_length=32)
    severity: str = Field(..., min_length=1, max_length=32)
    previous_severity: str | None = Field(None, max_length=32)
    source: str = Field(..., min_length=1, max_length=32)
    primary_track_id: str | None = Field(None, max_length=64)
    primary_group_id: str | None = Field(None, max_length=64)
    originating_alert_id: str | None = Field(None, max_length=64)
    originating_intelligence_event_id: str | None = Field(None, max_length=64)
    assigned_to: str | None = Field(None, max_length=36)
    previous_assignee: str | None = Field(None, max_length=36)
    actor_user_id: str | None = Field(None, max_length=36)
    incident_event_id: str = Field(..., min_length=1, max_length=36)
    incident_event_sequence: int = Field(..., ge=1)
    incident_event_type: str = Field(..., min_length=1, max_length=64)
    category: str | None = Field(None, max_length=64)
    message: str | None = Field(None, max_length=2000)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
```

---

## 3. Transactional Outbox & EventBus Publishing Invariant

To guarantee consistency between persistent SQLite state and realtime WebSocket streams:
1. When any mutation method on `IncidentService` executes, it builds the typed `IncidentRealtimePayload` and queues it inside `session.info["_pending_incident_events"]`.
2. SQLAlchemy event listeners `@sa_event.listens_for(Session, "after_commit")` and `@sa_event.listens_for(Session, "after_rollback")` handle transaction lifecycle:
   - On `after_commit`: Pending events are popped and published to `EventBus.publish(...)` using `RealtimeChannel.OPERATIONAL`.
   - On `after_rollback`: Pending events are immediately wiped, guaranteeing **zero phantom events**.
3. All incident events are registered in `CRITICAL_EVENT_TYPES` within `backend/app/core/events.py` so high-frequency AI/track updates cannot evict critical operational incident notifications under subscriber queue saturation.

---

## 4. Multi-Entity Correlation Architecture

Incidents correlate with other operational telemetry without implementing destructive or kinetic actions:
- `primary_track_id` $\to$ Correlates incident with active fused or historical track state.
- `primary_group_id` $\to$ Correlates incident with AI swarm/formation clusters.
- `originating_alert_id` $\to$ Links incident to threshold/geofence alerts.
- `originating_intelligence_event_id` $\to$ Links incident to historical intelligence snapshots.

---

## 5. Verification Matrix & Test Summary

### 5.1 Focused IM1-D Test Suites
- `backend/tests/test_incident_eventbus.py`:
  - Enums, contracts, payload serialization, and envelope round-trip.
  - Lifecycle event emissions for all 11 operations.
  - Transactional commit vs rollback outbox invariants.
  - Illegal transition zero-event suppression.
  - Critical event backpressure queue eviction.
- `backend/tests/test_incident_realtime.py`:
  - Live WebSocket `/ws/operational` streaming during REST mutations.
  - Non-interference with concurrent AI, track, and alert telemetry.
  - WebSocket ping-pong heartbeat verification.
- `backend/tests/test_incident_correlation.py`:
  - Full persistence and propagation of `primary_track_id`, `primary_group_id`, `originating_alert_id`, and `originating_intelligence_event_id`.
  - Null serialization for standalone incidents.
  - REST API correlation round-trip verification.

### 5.2 Full System Verification Results
| Suite / Check | Result |
| :--- | :--- |
| **Backend Incident Suites** (11 files) | **86 / 86 Passed (100%)** |
| **Full Backend Pytest Suite** | **547 / 547 Passed (100%)** |
| **Frontend Unit Tests (Vitest)** | **246 / 246 Passed (100%)** |
| **TypeScript Typecheck** (`tsc --noEmit`) | **Clean (0 errors)** |
| **Vite Production Build** | **Success** |
| **Desktop Tauri Checks** (`cargo check`, `cargo test`) | **Clean (0 warnings, 0 errors)** |
| **Git Diff Format Check** | **Clean** |

---

## 6. Checkpoint Scope Boundaries

| Capability | IM1-D Status | Scheduled Stage |
| :--- | :--- | :--- |
| Incident EventBus Publishing | **Complete** | IM1-D |
| Transactional Outbox Hooks | **Complete** | IM1-D |
| Realtime Operational WebSocket Streaming | **Complete** | IM1-D |
| Operational Entity Correlation | **Complete** | IM1-D |
| Incident Operator UI Panel | Not Started | IM1-E |
| Tactical Map Incident Overlays | Not Started | IM1-F |
| Defensive Safety Boundary Maintenance | **Enforced** | All Stages |
