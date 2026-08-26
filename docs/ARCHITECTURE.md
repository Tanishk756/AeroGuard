# Architecture

This document defines the intended high-level architecture for AeroGuard during the bootstrap and planning phase. It is intentionally a design statement for future implementation, not a claim that the platform is complete or operational.

## 1. Purpose and scope

AeroGuard is a defensive, research-oriented platform focused on:

- counter-UAS awareness and monitoring
- sensor and track fusion
- simulation and scenario rehearsal
- behavior analysis and anomaly review
- threat assessment and operator support
- admin and governance workflows

The project is not an offensive weapons system and will not implement autonomous engagement or destructive countermeasure logic.

## 2. Architectural principles

- Keep frontend and backend concerns cleanly separated.
- Keep domain logic independent from UI concerns.
- Prefer explicit contracts and typed interfaces where practical.
- Use Windows-first tooling while keeping Linux compatibility non-mandatory.
- Keep high-performance native boundaries isolated and measurable.
- Treat simulation data and real sensor data as distinct classes of information.
- Require auditability for governance-critical actions.

## 3. High-level system decomposition

The system is organized into the following major areas:

1. Operator Console
   - mission-oriented UI for live operations, tracking, and analysis
   - 2D/3D visualization and timeline workspaces
   - alert and threat summarization

2. Admin Console
   - users, RBAC, sensors, policies, models, datasets, feature flags, configuration
   - operational governance and audit visibility

3. Developer/API Console
   - API exploration, dev workflows, diagnostics, and integration tooling

4. Backend API
   - service layer, auth, policy enforcement, CRUD and query interfaces
   - event and workflow orchestration

5. Event bus and realtime layer
   - stream processing, notifications, and state distribution

6. Simulation and sensor subsystems
   - synthetic scenarios, model-driven sensors, environment data, and generated telemetry

7. Fusion, tracking, and analytics
   - correlation, classification, trajectory prediction, anomaly detection

8. AI services
   - detection assistance, model orchestration, dataset workflows, risk evaluation

9. Data layer and persistence
   - relational, analytical, and event storage

10. Platform operations and security
   - audits, backups, configuration, deployment boundaries, and monitoring

## 4. Frontend and backend separation

The frontend will be centered on operator and admin experiences, while the backend will own domain logic, authorization, persistence, and event orchestration.

### Frontend responsibilities

- UI rendering and interaction
- visualization and workspace operation
- presentation of maps, overlays, timelines, and alerts
- client-side state management and interaction orchestration
- realtime rendering from server streams

### Backend responsibilities

- identity, authorization, and session management
- API endpoints and validation
- persistence and retrieval
- cross-domain workflows and orchestration
- event publication and stream management
- domains such as sensors, incidents, tracks, AI model metadata, and policies

This separation supports a clean contract between client workflows and backend services while preserving room for advanced future features.

## 5. Native and high-performance boundaries

AeroGuard will use a layered architecture in which native components are isolated behind clear boundaries and only introduced where profiling or operational constraints justify them.

Planned boundary model:

- UI and orchestration: React + TypeScript + Tauri 2
- Domain logic and API workflows: Python + FastAPI + Pydantic
- High-performance or compute-heavy tasks: Rust-first components
- C++ only when profiling shows a genuine requirement

This approach avoids unnecessary native complexity while enabling targeted optimization in throughput-sensitive areas, such as streaming ingestion, filtering, or compute-heavy processing.

## 6. AI boundaries

AI services must remain clearly separated from core event-processing logic and operational decision execution.

Planned responsibilities:

- model lifecycle and metadata management
- dataset governance and evaluation
- behavior analysis and anomaly hypotheses
- prediction and classification support
- alert triage augmentation and scenario analysis

AI should be used as a support and analysis engine, not as an autonomous operator or control system. Recommendations, scores, probabilities, and classifications should be clearly surfaced and auditable.

## 7. Event bus and realtime architecture

AeroGuard depends on an event-driven design to move data between sensors, fusion logic, operators, automation services, and administrative systems.

### Event concepts

- domain events: state changes or significant incidents
- telemetry events: continuous sensor or synthetic feed activity
- workflow events: task, approval, or orchestration triggers
- system events: health, configuration, and lifecycle notifications

### Realtime architecture

- WebSocket transport for operator-facing updates and streaming state changes
- typed event contracts to ensure schema clarity and versioning
- batching and filtering for high-volume feeds
- event persistence for operational traceability and replay

### Event flow

Sensor or scenario data enters the platform through ingestion boundaries, is normalized into domain events, routed to relevant subscribers, persisted when appropriate, and then surfaced to operator and admin consoles.

## 8. Plugin architecture

The platform is planned to support extension points without collapsing into uncontrolled custom logic.

Planned plugin capabilities:

- custom sensor adapters
- analysis and enrichment extensions
- scene or visualization overlays
- custom reporting and export formats
- administrative integrations with governance constraints

Plugin boundaries should be explicit, versioned, and governed by security review. Plugins must not bypass authorization, audit, or data provenance responsibilities.

## 9. Data flow overview

A representative flow looks like this:

1. A sensor, scenario engine, or external stream delivers raw observations.
2. Ingestion validation and normalization transform the source into canonical domain data.
3. Event bus emits typed domain events to subscribers.
4. Fusion and track management correlate observations into tracks and context.
5. Analytics and AI services enrich the state with prediction or anomaly assessment.
6. Operator and admin UIs receive relevant updates via realtime streams.
7. Persistence stores operational records, snapshots, and audit artifacts.
8. Reporting, incident review, and replay workflows consume the stored state.

## 10. Operational principles

- Real-time updates should be efficient and prioritization-aware.
- State should be queryable and replayable.
- High-volume sensor pipelines should be batchable and filterable.
- Security-sensitive actions should be explicitly audited.
- Data provenance must remain visible.

## 11. Planned subsystem boundaries

AeroGuard is intentionally split into clear subsystem boundaries before implementation:

- Operator Console: tactical and mission-facing workflows
- Admin Console: governance, configuration, and policy management
- Developer/API Console: integration and testing workflows
- Backend API: service and orchestration layer
- Event bus: async communication and stream distribution
- Simulation engine: scenario generation and synthetic environments
- Sensor simulation: synthetic emitters and data generation
- Fusion and tracking: correlation and state estimation
- AI services: recommendation and analytical assistance
- Database and analytics: persistence and query layers
- Audit and security: traceability, authz, and governance controls

## 12. Documentation status

This architecture document reflects the planned end-state of the platform and the intended engineering boundaries. It is not a statement that all subsystems are implemented or complete.

Stage F1 implements only the operational data foundation: Sensor, Detection,
Track, TrackHistory, Alert, ThreatAssessment, Scenario, and Geofence
persistence plus strict contracts. Ingestion, normalization pipelines,
association, tracking, alert evaluation, threat scoring, scenario execution,
realtime delivery, and UI remain future work. These operational records remain
separate from Stage E security/audit events.

Stage F2 adds the bounded sensor-adapter to canonical-detection ingestion path.
Adapters, validation, normalization, and persistence remain separate from F3
association/tracking and F4 alert/threat processing.

Stage F3 adds deterministic detection association, track lifecycle management,
and append-only history persistence. Gating, normalized scoring, deterministic
tie-breaking, and read-only track query APIs are implemented without threat scoring,
alerts, or external broker infrastructure.

Stage F4 adds multi-sensor kinematic and spatial consensus, track quality scoring,
source diversity quantification, multi-source classification reconciliation,
coasting confidence decay, 2D/3D geofence volume evaluation, deterministic operational
threat priority scoring, alert rule evaluation and deduplication, and read-only APIs
for threats, alerts, and geofences. AI/ML, autonomous actions, weaponization, and
external message brokers remain strictly out of scope.

Stage F5 activates the scenario data model and implements a deterministic,
in-process simulation engine featuring a virtual simulation clock, WGS84 great-circle
trajectory generation with constant-velocity and waypoint navigation, synthetic multi-modality
sensor models (Radar, Optical, RF) with range/FOV gating and Gaussian noise, scenario
execution lifecycle management, and full integration into the F2-F4 operational pipeline
along with scenario and geofence REST APIs. WebSocket streaming and UI remain future work.

Stage F6 adds the historical querying, timeline aggregation, descriptive analytics, and
deterministic replay and run comparison subsystem. Operating strictly as a read-only analysis
layer over canonical operational truth (F1-F5), it provides bounded historical queries,
unified operational timeline reconstruction with microsecond deterministic tie-breaking,
aggregate descriptive SQL metrics, virtual clock replay stepping, and canonical structural
run comparisons. It introduces zero new database migrations, zero external brokers, and zero audit log pollution.

Stage UI1 establishes the Operator Console frontend foundation in React 18 and TypeScript.
It delivers the tactical dark design system, application shell, HttpOnly cookie session
authentication, RBAC-aware navigation, primary operator overview workspace, tactical map
placeholder, track/sensor/alert/threat/timeline panels, bounded historical querying, replay
stepping interface, and descriptive analytics views consuming backend F1-F6 REST APIs.

Stage UI2 implements the Operational Map & Mission Workspace on top of the UI1 foundation.
It provides an interactive SVG tactical map with custom Equirectangular/cosine projection, pan,
zoom, fit-all bounds, and coordinate readout; multi-entity selection synchronization across map,
registry tabs, detail inspectors, and timeline feeds; historical trajectory path and breadcrumb
visualization; valid sensor range coverage circles; geofence volume boundaries; and restrained
REST-backed stale-while-refresh data staging.

Stage UI3 implements Mission Operations & Interaction. It delivers a contextual multi-entity
inspector hub supporting tracks, alerts, threats, sensors, and geofences; F5 scenario simulation
lifecycle execution controls (prepare, start, pause, resume, step, stop, reset) and real-time virtual
clock monitoring; F6 historical replay spatial map visualization and comparison analysis; global
command palette modal (Ctrl+K / /) with keyboard acceleration; URL deep-linking synchronization;
enhanced timeline filtering and time window presets; and robust operational UX hardening.
