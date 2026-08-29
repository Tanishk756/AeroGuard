# Stage IM1 Checkpoint IM1-A Verification Report

**Checkpoint**: IM1-A — Incident Domain, State Machine & Database Migration  
**Baseline HEAD**: `6321895`  
**Date**: 2026-08-29  
**Dev Environment**: Windows 11 / Python 3.12 / TypeScript / Vite / Tauri / SQLite  
**Scope**: Defensive Situational Awareness & Operational Workflow Only  

---

## 1. Checkpoint Overview

Checkpoint **IM1-A** establishes the core database domain and lifecycle state machine for AeroGuard's incident management subsystem:

1. **Incident Domain Model (`Incident`)**:
   - Primary key (`id`), human-readable reference (`incident_number`), title, description.
   - Lifecycle status (`NEW`, `ACKNOWLEDGED`, `TRIAGED`, `ESCALATED`, `RESOLVED`, `CLOSED`).
   - Operational severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and source (`OPERATOR`, `ALERT`, `INTELLIGENCE`, `SYSTEM`).
   - Correlation links: `primary_track_id` (`tracks.id`), `originating_alert_id` (`alerts.id`), `primary_group_id`, `originating_intelligence_event_id`.
   - Actor auditing: `created_by`, `acknowledged_by`, `assigned_to`, `resolved_by`, `closed_by`.
   - Lifecycle timestamps: `created_at`, `updated_at`, `acknowledged_at`, `assigned_at`, `resolved_at`, `closed_at`.
   - Structured metadata storage (`metadata_json` with `.metadata` property).

2. **Incident Timeline Event Model (`IncidentEvent`)**:
   - Append-only event entity with foreign key to `incidents.id` (`CASCADE`).
   - Event types: `CREATED`, `ACKNOWLEDGED`, `ASSIGNED`, `REASSIGNED`, `TRIAGED`, `ESCALATED`, `DE_ESCALATED`, `NOTE_ADDED`, `ACTION_LOGGED`, `STATUS_CHANGED`, `RESOLVED`, `CLOSED`.
   - Action categories: `SENSOR_REVIEW`, `TRACK_CORRELATION_REVIEW`, `OPERATOR_CONTACT`, `SUPERVISOR_ESCALATION`, `PROCEDURE_REVIEW`, `SCENARIO_REVIEW`, `OTHER`.
   - Database-level immutability listener (`@event.listens_for("before_update")` / `before_delete`) preventing modification of historical records.

3. **Deterministic State Machine**:
   - Formal transition validator (`validate_transition`, `can_transition`).
   - Rejects illegal state leaps and self-transitions.
   - Treats `CLOSED` as terminal.
   - Pure, deterministic, zero-side-effects implementation.

4. **Alembic Migration (`0008_incident_management`)**:
   - Creates `incidents` and `incident_events` tables with composite indexes.
   - Seeds `incidents.*` permissions and binds them to existing system roles.
   - Full upgrade and downgrade support.

---

## 2. State Machine Transition Matrix

| From Status | Permitted Target Statuses | Workflow Rationale |
|---|---|---|
| `NEW` | `ACKNOWLEDGED` | Initial operator acknowledgment of incident creation. |
| `ACKNOWLEDGED` | `TRIAGED`, `RESOLVED` | Operator triage assessment or direct resolution. |
| `TRIAGED` | `ESCALATED`, `RESOLVED` | Escalation to supervisor/operations or resolution after analysis. |
| `ESCALATED` | `TRIAGED`, `ACKNOWLEDGED` | De-escalation back to operator triage or acknowledged state. |
| `RESOLVED` | `TRIAGED`, `CLOSED` | Formal closure or reopening for further investigation. |
| `CLOSED` | *None* | Terminal state. |

---

## 3. Database Schema

### Table: `incidents`
```text
┌───────────────────────────────────────┬──────────────┬──────────────┬──────────────────────────────────┐
│ Column                                │ Type         │ Nullable     │ Constraints / References         │
├───────────────────────────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
│ id                                    │ VARCHAR(36)  │ No           │ PRIMARY KEY                      │
│ incident_number                       │ VARCHAR(32)  │ No           │ UNIQUE, INDEX                    │
│ title                                 │ VARCHAR(256) │ No           │                                  │
│ description                           │ VARCHAR(2048)│ Yes          │                                  │
│ status                                │ VARCHAR(32)  │ No           │ INDEX (Enum)                     │
│ severity                              │ VARCHAR(32)  │ No           │ INDEX (Enum)                     │
│ source                                │ VARCHAR(32)  │ No           │ (Enum)                           │
│ primary_track_id                      │ VARCHAR(36)  │ Yes          │ FK -> tracks.id (SET NULL)       │
│ primary_group_id                      │ VARCHAR(64)  │ Yes          │ INDEX                            │
│ originating_alert_id                  │ VARCHAR(36)  │ Yes          │ FK -> alerts.id (SET NULL)       │
│ originating_intelligence_event_id     │ VARCHAR(64)  │ Yes          │                                  │
│ created_by                            │ VARCHAR(36)  │ Yes          │ FK -> users.id (SET NULL)        │
│ acknowledged_by                       │ VARCHAR(36)  │ Yes          │ FK -> users.id (SET NULL)        │
│ assigned_to                           │ VARCHAR(36)  │ Yes          │ FK -> users.id (SET NULL), INDEX │
│ resolved_by                           │ VARCHAR(36)  │ Yes          │ FK -> users.id (SET NULL)        │
│ closed_by                             │ VARCHAR(36)  │ Yes          │ FK -> users.id (SET NULL)        │
│ created_at                            │ DATETIME     │ No           │ INDEX                            │
│ updated_at                            │ DATETIME     │ No           │                                  │
│ acknowledged_at                       │ DATETIME     │ Yes          │                                  │
│ assigned_at                           │ DATETIME     │ Yes          │                                  │
│ resolved_at                           │ DATETIME     │ Yes          │                                  │
│ closed_at                             │ DATETIME     │ Yes          │                                  │
│ metadata                              │ JSON         │ No           │                                  │
└───────────────────────────────────────┴──────────────┴──────────────┴──────────────────────────────────┘
```

### Table: `incident_events`
```text
┌───────────────────────────────────────┬──────────────┬──────────────┬──────────────────────────────────┐
│ Column                                │ Type         │ Nullable     │ Constraints / References         │
├───────────────────────────────────────┼──────────────┼──────────────┼──────────────────────────────────┤
│ id                                    │ VARCHAR(36)  │ No           │ PRIMARY KEY                      │
│ incident_id                           │ VARCHAR(36)  │ No           │ FK -> incidents.id (CASCADE)     │
│ timestamp                             │ DATETIME     │ No           │ INDEX                            │
│ event_type                            │ VARCHAR(32)  │ No           │ INDEX (Enum)                     │
│ actor_user_id                         │ VARCHAR(36)  │ Yes          │ FK -> users.id (SET NULL)        │
│ previous_status                       │ VARCHAR(32)  │ Yes          │                                  │
│ new_status                            │ VARCHAR(32)  │ Yes          │                                  │
│ message                               │ VARCHAR(1024)│ Yes          │                                  │
│ category                              │ VARCHAR(64)  │ Yes          │ (Enum)                           │
│ metadata                              │ JSON         │ No           │                                  │
│ created_at                            │ DATETIME     │ No           │                                  │
└───────────────────────────────────────┴──────────────┴──────────────┴──────────────────────────────────┘
```

---

## 4. Test Matrix & Verification Evidence

### Backend Pytest Suite
```text
============================= test session starts =============================
platform win32 -- Python 3.12.10, pytest-8.3.4, pluggy-1.6.0
collected 496 items

================= 496 passed, 8 warnings in 66.80s (0:01:06) ==================
```
- `backend/tests/test_incident_models.py`: 5 passed
- `backend/tests/test_incident_state_machine.py`: 5 passed
- `backend/tests/test_operational_migration.py`: 1 passed (Alembic upgrade, downgrade to `0004_audit_events`, and re-upgrade)

### Frontend Operator Console
- `npm test -- --run`: **246 / 246 passed** (0 failures, 794ms)
- `npm run typecheck`: **0 errors**
- `npm run build`: **Clean Vite production build**

### Desktop Tauri Native Suite
- `cargo test`: **0 errors**
- `cargo check`: **0 errors**

---

## 5. Security & Defensive Safety Audit

- **Secret Scans**: Verified zero unauthenticated endpoints or secret leaks.
- **Defensive Safety Invariant**: Strictly within observation, triage, and mission documentation. Zero physical engagement, weapon targeting, jamming, or destructive actions.
- **Immutability Invariant**: Historical incident events cannot be updated or deleted.

---

## 6. Known Limitations (IM1-A Baseline)

1. Service layer, REST APIs, and RBAC endpoint enforcement are deferred to **IM1-B** and **IM1-C**.
2. EventBus telemetry dispatch is deferred to **IM1-D**.
3. Frontend incident dashboard and triage UI are deferred to **IM1-E** and **IM1-F**.
