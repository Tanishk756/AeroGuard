# Admin architecture

This document defines the planned Admin Console for AeroGuard. It describes the intended governance, policy, and system administration model without implementing the console.

## 1. Admin Console purpose

The Admin Console is the governance surface for platform configuration, user administration, operational policy management, security review, and system oversight. It is distinct from the operator-facing mission views.

## 2. Planned admin domains

### 2.1 Dashboard

The dashboard will summarize:

- system health
- active users and sessions
- sensor and integration status
- critical alerts and backend state
- AI activity and health checks
- backup and recovery readiness

### 2.2 Users

Administrative management for:

- user profiles
- account lifecycle and status
- password or credential policy enforcement
- access reviews
- user activity history

### 2.3 Roles and permissions

Support for:

- role definition and updates
- permission assignment
- access scoping and least-privilege administration
- role-based review and approval workflows

### 2.4 Authentication and sessions

Administration of:

- auth providers and policies
- session lifecycle review
- inactivity timeout and lockout conditions
- suspicious activity monitoring

### 2.5 Sensors

Capabilities for:

- sensor registration and status
- sensor profile maintenance
- calibration and health review
- source validity classification

### 2.6 Sensor profiles

Management of sensor configuration families, including:

- profile versioning
- calibration metadata
- deployment context
- operational assumptions and constraints

### 2.7 Scenarios

Operational administration for:

- scenario creation and lifecycle
- simulation or test environment setup
- scenario categories and labels

### 2.8 Threat policies

Governance for threat and detection policy management, including:

- threshold configuration
- severity rules
- policy history and review

### 2.9 AI models

Model management should cover:

- model registry entries
- versioning
- ownership and access controls
- evaluation state and model health
- usage restrictions and audit visibility

### 2.10 Datasets

Support for dataset lifecycle operations:

- dataset registration
- source identification
- versioning
- classification and retention metadata

### 2.11 Feature flags

Operations for enabling, disabling, and monitoring feature rollout:

- global and scoped flags
- staged deployment controls
- audit of configuration change risk

### 2.12 System configuration

Administrative configuration for:

- platform settings
- operational policy defaults
- integrations and environment configuration
- system tuning and compatibility controls

### 2.13 Database management

Operational view of:

- storage configuration
- database health and capacity considerations
- schema evolution readiness
- retention and backup planning

### 2.14 API keys

Administrative management of:

- API credentials
- service identity and scope
- expiration and rotation policy
- audit trails for issuance and mutation

### 2.15 Audit logs

The admin console should provide tools to review:

- authentication and authorization events
- sensor and configuration changes
- user management actions
- AI model and dataset changes
- policy changes and incidents

Stage E provides the backend audit records and read-only query API. Audit UI
and export workflows remain outside this stage.

### 2.16 System health

Monitoring surfaces for:

- server health
- worker and service status
- data pipeline health
- alert conditions and degradation

### 2.17 Notifications

Administration of operational notifications, including:

- alert routing
- escalation pathways
- user or team delivery preferences

### 2.18 Backups

Operational planning for:

- backup scheduling
- restore metadata
- retention policy visibility
- backup verification status

### 2.19 Import/export

Governance for:

- import of data or configuration records
- export of operational and audit artifacts
- data classification and policy enforcement during transfer

### 2.20 Versioning and rollback

The admin console should support planned operational governance for:

- software or configuration version visibility
- rollback readiness
- environment drift review
- change approval tracking

## 3. Security expectations

The Admin Console must enforce:

- strong authentication
- strict RBAC
- audit logging for all critical actions
- separation between admin and operator roles
- no bypass of policy enforcement or auth checks

Stage D provides the backend RBAC foundation for these expectations. The exact
eight system roles are seeded deterministically, system roles are protected from
rename/deletion, and management APIs enforce permissions server-side. The
frontend must not be treated as an authorization boundary.

## 4. Design principles

- keep governance and operational tasks functionally separate
- emphasize integrity and auditability
- support safe rollback and review workflows
- maintain clear role boundaries across the platform

## 5. Planned non-goal

This document defines the intended admin architecture only. It does not claim the operational admin system has been built or is in active use.
