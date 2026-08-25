This document defines the conceptual data model and records the implemented Stage C identity/session schema. Other domain entities remain planned.
# Data model

This document defines the intended conceptual data model for AeroGuard. It describes the planned domain entities and relationships without creating database migrations or serialized schema implementations.

## 1. Design principles

- Keep operational state separate from governance data.
- Distinguish simulated data from real sensor data.
- Preserve provenance and confidence metadata.
- Support replay, auditability, and time-series analysis.
- Use typed contracts across API, event, and persistence boundaries.

## 2. Core domain entities

### 2.1 User

Represents an authenticated user of the platform.

Key attributes:

- user_id
- username
- display_name
- email
- status
- created_at
- last_login_at
- organization or scope membership

Relationships:

- many-to-one with organization or tenant context
- many-to-many with roles
- one-to-many with audit events and sessions

Stage C persists `users` with `id`, normalized unique `username`,
`display_name`, normalized unique `email`, Argon2id `password_hash`,
`status` (`ACTIVE` or `DISABLED`), UTC-normalized timestamps, and nullable
`last_login_at`. Roles and audit events are not implemented.

### 2.2 Role

Represents a named authorization grouping.

Key attributes:

- role_id
- name
- description
- scope

Relationships:

- many-to-many with users
- one-to-many with permissions

### 2.3 Permission

Defines the allowed action or resource access.

Key attributes:

- permission_id
- resource
- action
- effect

Relationships:

- many-to-many with roles
- used by authorization checks across admin and runtime operations

### 2.4 Session

Represents an active login or authenticated operational session.

Key attributes:

- session_id
- user_id
- device or client metadata
- start_time
- end_time
- status

Relationships:

- belongs to one user
- linked to audit logs and notifications

Stage C persists `sessions` with `id`, `user_id`, a unique SHA-256 hash of an
opaque random cookie secret, `created_at`, `expires_at`, `last_seen_at`,
nullable `revoked_at`, and bounded nullable `client_ip` and `user_agent`.
Raw session secrets are never persisted.

### 2.5 Sensor

Represents a system, sensor, or data source contributing information.

Key attributes:

- sensor_id
- sensor_type
- name
- status
- source_class
- configuration_version
- provenance metadata

Relationships:

- many-to-one with sensor profile
- one-to-many with observations
- one-to-many with sensor health records

### 2.6 SensorProfile

Defines configuration and calibration characteristics for a sensor family or instance.

Key attributes:

- profile_id
- name
- sensor_type
- configuration metadata
- calibration descriptor
- deployment context

Relationships:

- one-to-many with sensor instances

### 2.7 Observation

Represents a raw or normalized measurement from a sensor.

Key attributes:

- observation_id
- sensor_id
- timestamp
- source_class
- confidence
- measurement_type
- payload

Relationships:

- belongs to one sensor
- may contribute to one or more tracks
- may be associated with scenario or replay state

### 2.8 Track

Represents a consolidated object or target state over time.

Key attributes:

- track_id
- object_type
- status
- confidence
- first_seen
- last_seen
- current_state

Relationships:

- one-to-many with observations
- one-to-many with track events
- may be associated with threat assessment and incident state

### 2.9 ThreatAssessment

Represents risk or threat evaluation for a track or scenario context.

Key attributes:

- assessment_id
- entity_reference
- threat_level
- confidence
- reasons
- status

Relationships:

- may reference track, scenario, or incident data
- one-to-many with evidence and notes

### 2.10 Incident

Represents an operational investigation or response workflow.

Key attributes:

- incident_id
- title
- severity
- status
- opened_at
- closed_at
- owner

Relationships:

- one-to-many with track references
- one-to-many with alerts, notes, and evidence

### 2.11 Alert

Represents a significant event or triage notification.

Key attributes:

- alert_id
- type
- severity
- source
- timestamp
- status

Relationships:

- may correlate to track, sensor, incident, or policy

### 2.12 Scenario

Represents a synthetic or operational scenario for simulation, evaluation, or training.

Key attributes:

- scenario_id
- name
- description
- type
- status
- created_by

Relationships:

- one-to-many with scenario entities and events
- includes simulation-specific metadata

### 2.13 Dataset

Represents collected or curated data for training, evaluation, or analytics.

Key attributes:

- dataset_id
- name
- type
- source
- version
- description

Relationships:

- one-to-many with records or references
- may be used across AI or analytics workflows

### 2.14 ModelRegistryEntry

Represents a model definition or version record.

Key attributes:

- model_id
- name
- version
- type
- status
- owner

Relationships:

- many-to-one with dataset or training context
- referenced by analysis workflows

### 2.15 AuditEvent

Represents security, administrative, or operational traceability records.

Key attributes:

- audit_id
- actor
- action
- resource
- timestamp
- result
- metadata

Relationships:

- tied to user, session, resource, or system event

## 3. Relationship model

Core conceptual relationships:

- User -> Role (many-to-many)
- User -> Session (one-to-many)
- Role -> Permission (many-to-many)
- SensorProfile -> Sensor (one-to-many)
- Sensor -> Observation (one-to-many)
- Observation -> Track (many-to-many or many-to-one via derived correlation)
- Track -> ThreatAssessment (one-to-many)
- ThreatAssessment -> Incident (many-to-one or many-to-many)
- Scenario -> Observation or synthetic entity records (one-to-many)
- Dataset -> ModelRegistryEntry (many-to-many or one-to-many by lineage)
- AuditEvent -> User, Session, Resource (many-to-one or derived references)

## 4. Temporal and provenance requirements

The model must support:

- event timestamps and ordering
- state validity windows
- observation confidence values
- scenario metadata and synthetic origin
- detector model provenance and versioning
- audit trail for administrative activities

## 5. Planned storage categories

The platform is expected to maintain several data classes:

- transactional configuration data
- operational telemetry and state snapshots
- event streams and replay records
- analytical datasets and derived outputs
- security, audit, and policy data

## 6. Intentional limitations of this document

This document is a conceptual design only. It does not define database schema, table names, migrations, or ORM decisions. Those will come later when implementation begins.
