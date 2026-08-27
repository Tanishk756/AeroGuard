# Roadmap

This roadmap defines the planned delivery phases for AeroGuard from repository bootstrap through production-oriented operations. It is intentionally a planning document, not an implementation status report.

## Phase 0: repository bootstrap and foundation

Objectives:

- establish the repository structure and project conventions
- document architecture direction and safety boundaries
- define engineering standards and review expectations
- record required subsystem boundaries and project scope

Deliverables:

- repository structure and documents
- licensing, security, and contribution guidance
- architectural documentation set
- placeholder directories for future subsystem development

## Phase 1: platform foundations

Objectives:

- formalize workspace and repo tooling expectations for Windows-first development
- define data contract and event contract standards
- establish test and quality practices
- define backend, frontend, and native boundary conventions

Planned work:

- backend API skeleton and directory structure
- frontend application skeletons for operator/admin/developer consoles
- shared package contracts, schemas, and interfaces
- CI and repository checks configuration as available in the project toolchain

## Phase 2: frontend and developer experience

Objectives:

- deliver the Operator Console shell and workspace concepts
- build Admin Console foundation
- establish Developer/API Console and tooling surfaces
- create reusable UI patterns around tactical mission interfaces

Planned UI capabilities:

- dockable panels and workspace layouts
- map-centric operations views
- alert feed and timeline surfaces
- command palette and keyboard-driven workflows
- dark tactical design language and accessibility baseline

Stage UI1 delivers the Operator Console foundation: tactical dark design tokens,
application shell, session authentication and RBAC-aware navigation, primary operator
overview workspace, tactical map placeholder, track, sensor, alert, threat, timeline,
historical query, replay, and descriptive analytics views consuming backend F1-F6 REST APIs.

Stage UI2 delivers the Operational Map & Mission Workspace: interactive SVG tactical map
with custom projection, pan, zoom, fit-all bounds, and coordinate readout; multi-entity selection
synchronization across map, registry tabs, detail inspectors, and timeline feeds; historical
trajectory path and breadcrumb visualization; valid sensor range coverage circles; geofence
volume boundaries; and restrained REST-backed stale-while-refresh data staging.

Stage UI3 delivers Mission Operations & Interaction: contextual multi-entity inspector hub
supporting tracks, alerts, threats, sensors, and geofences; F5 scenario simulation lifecycle
execution controls (prepare, start, pause, resume, step, stop, reset) and real-time virtual
clock monitoring; F6 historical replay spatial map visualization and comparison analysis; global
command palette modal (Ctrl+K / /) with keyboard acceleration; URL deep-linking synchronization;
enhanced timeline filtering and time window presets; and robust operational UX hardening.

Stage UI4 delivers Mission Governance, Security Audit & Administrative Operations: Security
Audit Log Explorer with cursor pagination, multi-field filter toolbar, and structured payload
inspection; RBAC Role & Access Governance with custom role builder, domain-grouped permission
matrix, system role immutability, and User ID role assignment/revocation; and Platform Diagnostics
with database connectivity verification (SELECT 1), runtime environment inspection, and session authority.

Stage UI5 delivers Mission Authoring & Defense Zone Studio: comprehensive visual management
for defensive geofence perimeters and deterministic simulation scenario authoring, providing full CRUD
workflows, live SVG TacticalMap boundary preview, template cloning, unsaved draft protection, and two-step deletion safety.

Stage UI6 delivers Advanced Analytics & Reporting: comprehensive analytical dashboard,
classification distribution charts, speed and altitude kinematics histograms, threat level breakdowns,
time-window filtering presets, and summary reporting views over Stage F6 analytical datasets.

Stage UI7 delivers the Developer and API Console: versioned REST API catalog across 8 domains,
interactive request dispatcher with live round-trip latency and telemetry inspection, synthetic sensor
detection ingestion workbench, Pydantic schema contract viewer, and multi-format cURL/fetch code snippet generation.

Stage UI8 delivers Desktop and Native Packaging (Tauri 2 Integration): established
a minimal and secure Tauri 2 desktop foundation for Windows; typed desktop environment bridge
with graceful browser fallbacks; custom dark tactical window titlebar with drag region and
window controls; native OS desktop alert notifications for CRITICAL/HIGH alerts with bounded
in-memory deduplication; system tray integration with window toggle and clean exit; and dual
distributable Windows packaging (.msi and .exe installers).

## Phase 3: backend and data services

Objectives:

- establish service-layer architecture and API domains
- implement identity, authorization, and RBAC scaffolding
- define persistence layers for configuration, sensor records, and incidents
- produce typed event interfaces and integration boundaries

Planned work:

- FastAPI service skeleton
- Pydantic model contracts
- session and auditing scaffolds
- database abstraction boundaries and migration planning

## Phase 4: simulation and sensor ingestion

Objectives:

- create scenario definitions and environment simulation flows
- prototype synthetic sensor data and state generation
- support lab and training workflows without conflating simulation with real data

Planned work:

- synthetic sensor models
- scenario execution environment
- track generation and observation streams
- simulation metadata and provenance controls

## Phase 5: sensor fusion and track management

Objectives:

- correlate observations from multiple sources
- manage evolving object tracks and confidence metadata
- produce consistent threat context and state transitions

Planned work:

- observation normalization and correlation
- track lifecycle and state management
- trajectory estimation and confidence scoring
- alignment with replay and audit requirements

Stage F1 delivers the persistence foundation for sensors, detections, tracks,
track history, alerts, threat assessments, scenarios, and geofences. It does
not deliver the processing workflows listed above.

Stage F2 delivers the sensor adapter, validation, normalization, and single
detection ingestion path. Association, tracking, alerts, and threat priority
remain later stages.

Stage F3 delivers deterministic detection association, track lifecycle management,
and append-only history persistence. Alert generation, threat scoring, and realtime
event distribution remain future work.

Stage F4 delivers multi-sensor kinematic/spatial consensus, continuous track quality
scoring, source diversity calculation, multi-source classification reconciliation,
coasting confidence decay, 2D/3D geofence volume evaluation, deterministic operational
threat priority scoring, server-side alert generation with deduplication, and read-only
query APIs for threats, alerts, and geofences. AI/ML, autonomous actions, weaponization,
and external message brokers remain future work.

Stage F5 delivers the scenario execution environment and deterministic simulation engine:
virtual simulation clock, WGS84 great-circle trajectory models (constant-velocity and waypoints),
synthetic multi-sensor models (Radar, Optical, RF) with range/FOV gating and Gaussian noise,
scenario execution lifecycle control (prepare, start, pause, resume, step, stop, reset),
direct observation feeding into the F2-F4 pipeline, scenario management REST APIs, and
geofence management CRUD. WebSocket streaming and UI remain future work.

## Phase 6: AI and analytics

Objectives:

- integrate model-driven analysis and recommendation workflows
- support anomaly detection, classification, and behavior assessment
- define safe and transparent AI use patterns

Planned work:

- model registry and evaluation workflows
- dataset management and labeling structures
- analytics pipelines and reporting
- review of model outputs with human oversight

## Phase 7: threat intelligence and incident workflows

Objectives:

- assess threat patterns and escalation logic
- support incident reviews, operator workflows, and historical analysis
- provide structured reporting and decision support

Planned work:

- threat context models
- incident lifecycle management
- analyst workflow surfaces
- integrated reporting views and summaries

## Phase 8: admin, governance, and operational control

Objectives:

- provide secure configuration and policy administration
- govern sensors, users, roles, AI models, and feature flags
- support database operations, backup, and rollback considerations

Planned work:

- user and role administration
- sensor profiles and scenario management
- policy and feature flag controls
- health monitoring, notifications, and audit review

## Phase 9: analytics, replay, and performance

Objectives:

- add time-based analysis, replay, and historical retrieval
- validate performance-critical paths
- optimize event throughput and UI rendering fidelity

Planned work:

- replay systems and time-slice navigation
- analytical query layers for operational review
- profiling and performance regression checks
- real-time throughput tuning for maps, alerts, and streams

Stage F6 delivers the historical querying, multi-source operational timeline aggregation,
descriptive SQL analytics, virtual clock deterministic replay stepping, and canonical
structural replay run comparison engine.

Stage RT1 delivers the Realtime Streaming & WebSocket Event Bus architecture: in-process
async EventBus with monotonic atomic sequencing, bounded backpressure queue eviction,
authenticated WebSocket streaming channels (`/api/v1/ws/operational`, `/api/v1/ws/simulation`),
frontend `useWebSocketStream` hook with exponential backoff and jitter, `useOperationalData`
adaptive REST reconciliation and requestAnimationFrame track batching, and native Tauri 2
desktop toast notification dispatch.

Stage AI1 delivers Defensive Intelligence & Kinematic Anomaly Detection: deterministic
kinematic feature extraction engine (Haversine geodesic distance, spherical bearing,
turn rates, vertical rates, loitering radius of gyration, directional consistency ratio);
multi-sensor confidence calibration model (modality baseline, multi-source consensus,
history depth scaling, age decay); explainable 5-factor anomaly scoring engine with
blended peak/weighted aggregation; 60s forward trajectory prediction with expanding
spatial uncertainty envelopes; defensive geofence ingress forecasting; realtime `ai.summary`
EventBus broadcasting; `GET /api/v1/tracks/{track_id}/intelligence` REST endpoint; and
Operator Console forward trajectory vector and Track Inspector intelligence surfaces.

Stage MAP2 delivers Advanced Tactical Visualization & GPU Acceleration: unified tactical
renderer abstraction (`IMapRenderer`); hardware capability detection cascade (`WEBGPU` -> `CANVAS` -> `LEGACY`);
WGSL shaders and instanced GPU quad/chevron pipelines; high-performance 2D batch canvas fallback;
high-density spatial culling and density-aware label throttling for 1,000 live tracks;
bounded historical trails; AI1 forward trajectory vectors, expanding uncertainty bands,
time tags (+30s, +60s), and perimeter ingress hazard crosshairs; and keyboard pan/zoom navigation
with screen reader accessibility.

## Phase 10: testing, validation, and hardening

Objectives:

- verify subsystem behavior with unit, integration, API, and regression tests
- perform security review and audit validation
- validate documentation and operational safety constraints

Planned work:

- coverage for backend APIs and contracts
- frontend interaction and workflow tests
- event bus and stream reliability tests
- performance benchmarking for high-volume paths

## Phase 11: production readiness and packaging

Objectives:

- package desktop experiences and operational distributions
- define release engineering and rollback processes
- validate security and admin controls in deployment workflows

Planned work:

- release build and packaging flows
- environment-specific configuration
- deployment review and upgrade strategy
- support and maintenance documentation

## Delivery principles

- Do not claim subsystem completion before validation.
- Keep each phase small and testable.
- Separate product capability from research or prototype state.
- Treat safety, authentication, and audit controls as essential requirements.
