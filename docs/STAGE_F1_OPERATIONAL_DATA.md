# Stage F1 Operational Data Foundation

Stage F1 establishes the persistent operational data plane only. It stores sensor registrations, validated detection records, tracks and track history, alerts, informational threat assessments, scenario metadata, and geofences.

It does not implement ingestion, association, tracking algorithms, alert evaluation, threat scoring, scenario execution, background workers, realtime delivery, AI/ML, or frontend changes.

## Separation from Stage E

Stage E is the security/audit plane: "What did a user or system do?" Stage F is the operational plane: "What is happening in the environment?" F1 models do not write `AuditEvent` records. Future administrative mutations can use the Stage E audit service; detections, telemetry, track updates, and heartbeats remain operational data.

## Entities and relationships

- `Sensor` identifies a source, its controlled provenance class, status, and configuration metadata.
- `Detection` stores one immutable, validated observation and belongs to a sensor; it may reference a track.
- `Track` stores consolidated object state independently of detection IDs.
- `TrackHistory` stores append-only track state points with unique per-track sequences.
- `Alert` is an independent operational notification optionally related to a track and/or sensor.
- `ThreatAssessment` stores one informational assessment per track, with a bounded score and explainable factors.
- `Scenario` stores user-owned scenario metadata; execution is deferred.
- `Geofence` stores application-validated polygon or bounding-box data; spatial database support is deferred.

Lifecycle values are explicit: sensors are `REGISTERED`, `ACTIVE`, `DEGRADED`, `OFFLINE`, or `DISABLED`; tracks are `NEW`, `ACTIVE`, `STALE`, `LOST`, or `ARCHIVED`; alerts are `OPEN`, `ACKNOWLEDGED`, or `RESOLVED`; scenarios are `DRAFT`, `READY`, `RUNNING`, `COMPLETED`, or `FAILED`.

Source provenance is `REAL`, `SIMULATION`, or `REPLAY`. No default operational records are created.

## Validation and persistence

Pydantic contracts reject non-UTC timestamps, non-finite numbers, invalid coordinates, invalid headings, negative uncertainty/velocity, out-of-range confidence or scores, invalid enum values, oversized metadata, and malformed geometries. SQLAlchemy and SQLite add foreign keys, unique constraints, controlled-value constraints, bounded strings, and query indexes. Detection source IDs are unique per sensor when supplied. Detection and history updates or deletes are rejected at the application model layer.

Migration `0005_operational_core` depends on `0004_audit_events` and creates the eight operational tables without changing earlier migrations. SQLite remains the initial local-first store. Retention, analytical storage, and high-throughput scaling are deferred until measured workloads justify them.

## Security and deliberate limits

F1 exposes no new endpoints and adds no services, ingestion loop, simulator, tracking algorithm, alert service, threat engine, WebSocket, GIS dependency, or external infrastructure. Future APIs must use existing authentication and RBAC, and clients must not supply actor identity, permissions, ownership, or authoritative threat decisions.
