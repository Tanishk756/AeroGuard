# Event architecture

This document describes the planned event-driven architecture for AeroGuard. It defines the expected event model, lifecycle, and delivery strategy without implementing event infrastructure.

## 1. Goals

- decouple producers and consumers of operational data
- enable realtime UI updates and alerting
- preserve event traceability for auditing and replay
- support resilient processing and asynchronous workflows
- clearly separate simulation events from real-world or operational data

## 2. Event categories

### 2.1 Telemetry events

Continuous or periodic updates from sensors, scenarios, or synthetic sources.

Examples:

- sensor observation stream
- track state update
- health status heartbeat

### 2.2 Domain events

Significant state transitions in the platform.

Examples:

- track created
- track correlation updated
- threat assessment changed
- incident opened or closed

### 2.3 Workflow events

Triggered by system orchestration or business logic.

Examples:

- scenario started
- AI model evaluation queued
- backup job scheduled
- system configuration updated

### 2.4 Security and audit events

Administrative or system-critical events that must be reviewed.

Examples:

- login success or failure
- role change
- API key rotation
- configuration update
- data export event

### 2.5 Notification events

Messages for operators or administrators.

Examples:

- alert raised
- new incident assigned
- system degradation detected

## 3. Event lifecycle

A typical event lifecycle:

1. Source emits raw data or a state change.
2. Event normalization or validation applies schema and context.
3. Event is published to the internal bus or stream.
4. Relevant consumers process or display the event.
5. Persisted records are written where traceability is required.
6. Derived events are emitted as workflow or analytics outputs.

## 4. Realtime delivery strategy

The platform will use a realtime delivery layer that supports:

- WebSocket-based client streams
- tenant or workspace-specific filtering
- event priority and throttling where needed
- event replay for operator or analyst review

Planned goals:

- low-latency delivery to the console
- resilient reconnect behavior
- structured delivery of typed messages
- separation between operational and audit streams

## 5. Persistence and replay

Not every event needs long-term persistence, but operationally important events should be stored for:

- audit review
- incident reconstruction
- historical analytics
- operator review and replay

Persistent event records should preserve:

- event id and version
- timestamp
- source and origin metadata
- correlation identifiers
- payload schema version

## 6. Contract and compatibility requirements

Event contracts should be:

- typed where practical
- versioned
- explicitly documented
- compatible with replay workflows

Avoid ad hoc event payloads that bypass validation or schema governance.

## 7. Operational safeguards

The event system must support:

- replay-safe ordering
- deduplication where appropriate
- backpressure handling for high-volume telemetry
- security controls for admin and system events
- clear separation of simulation events from real sensor feeds

## 8. Planned non-goal

This document defines the intended event architecture, not a production event bus implementation.

Stage F2 returns an in-process `DetectionIngested` operational result after
successful persistence. This is distinct from the Stage E security/audit plane;
detection telemetry is not written as an audit event.
