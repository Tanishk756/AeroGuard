This document defines the intended API domains and the implemented Stage B/C routes. Later domains remain planned.
# API design

This document defines the intended API domains and endpoint categories for AeroGuard. It does not implement the API or define final concrete routes yet.

## 1. API principles

- separate public API concerns from internal service concerns
- keep typed contracts explicit
- make authentication and authorization part of every protected route group
- support event-driven updates and realtime subscriptions
- enable operational introspection for diagnostics and admin review

## 2. Planned API domains

### 2.1 Authentication and identity

Purpose:

- sign-in and session creation
- identity verification and token handling
- password or credential policy enforcement
- logout and session termination

Categories:

- auth/session endpoints
- token lifecycle operations
- user self-service access management

Stage C implements `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, and
`GET /api/v1/me` using opaque server-side sessions in an HttpOnly cookie.
Login failures are returned as `AUTH_INVALID_CREDENTIALS`; protected requests
use stable codes for unauthenticated, expired, revoked, and disabled sessions.
## 7. Stage C session contract

The session cookie is named `aeroguard_session`, is HttpOnly, uses `SameSite=Lax`,
and is scoped to `/api/v1`. It is not returned in JSON. `Secure` is false only
for explicit local HTTP development and must be true outside local development.
Allowed browser origins are configuration-driven and credentialed CORS never
uses a wildcard. State-changing requests with an Origin header outside the
allowlist are rejected. CORS is not treated as a substitute for CSRF protection.

## 8. Documentation status

Stage D implements permission-protected `system/info` and the RBAC management
surface: `/roles`, `/permissions`, and explicit user-role and role-permission
assignment routes. Health remains public; `/me` remains authentication-only.
The RBAC permission vocabulary does not implement future domains.
Authentication route contracts are implemented in Stage C. Other API domains remain planned and require separate phases.

### 2.2 User and role management

Purpose:

- create and update users
- assign and revoke roles
- manage permissions and access scopes

Categories:

- user CRUD
- role and permission management
- access review and authorization assessment

### 2.3 Sensor management

Purpose:

- register sensor systems
- manage sensor profiles and status
- configure calibration and integration points

Categories:

- sensor CRUD
- profile CRUD
- health and telemetry status

### 2.4 Scenario and simulation management

Purpose:

- create, start, and stop scenarios
- manage synthetic environments and scenario metadata
- support test and training operations

Categories:

- scenarios
- simulation task lifecycle
- synthetic environment configuration

### 2.5 Observation and track APIs

Purpose:

- ingest sensor observations
- query track state and history
- manage object lifecycle and correlation state

Categories:

- observation ingestion
- track queries
- state and confidence retrieval

### 2.6 Threat and incident APIs

Purpose:

- manage risk assessments and incident workflows
- support analyst review and operational triage

Categories:

- threat assessments
- incidents
- alerts and escalation records

### 2.7 Analytics and reporting

Purpose:

- expose search and query capabilities for operational history
- allow report generation and export
- support dashboard-oriented operational intelligence

Categories:

- summary queries
- analytics workloads
- exported reports

### 2.8 AI model and dataset APIs

Purpose:

- register AI models and version metadata
- manage datasets and evaluation state
- coordinate support workflows for model-assisted analysis

Categories:

- model registry
- dataset management
- model evaluation endpoints

### 2.9 Administrative and configuration APIs

Purpose:

- manage feature flags, system settings, and operational policies
- support backups, versioning, import/export, and rollback planning

Categories:

- system configuration
- feature flags
- backup and recovery status
- data import/export

### 2.10 Audit and observability APIs

Purpose:

- retrieve audit records
- inspect system health and operational logs
- support admin review and compliance workflows

Categories:

- audit history
- system health
- notifications and logs

Stage E implements the read-only `/api/v1/audit/events` collection and
`/api/v1/audit/events/{id}` detail endpoint. Both require `audit.read`, use
bounded filters, and use descending timestamp/id cursor pagination.

## 3. Planned endpoint categories

The API will likely be grouped by business capability rather than a single monolithic surface. Category examples include:

- v1/auth
- v1/users
- v1/roles
- v1/sensors
- v1/scenarios
- v1/observations
- v1/tracks
- v1/incidents
- v1/alerts
- v1/models
- v1/datasets
- v1/analytics
- v1/admin
- v1/audit

## 4. Security requirements for routes

Protected endpoints must enforce:

- authentication
- authorization checks
- data scope restrictions
- audit logging for significant actions
- rate limiting where needed

## 5. Realtime interaction model

Some resources will be surfaced over WebSocket channels or pub/sub topics, including:

- operator alert streams
- track updates
- system health events
- admin notification feeds
- scenario lifecycle transitions

## 6. API versioning and compatibility

Future implementations should plan for:

- explicit versioning
- compatibility review for breaking changes
- schema evolution rules
- event contract versioning alongside API versioning

## 7. Documentation status

This file defines the intended API boundaries and categories. Actual implementation, validation, and concrete route definitions will come in later project phases.
