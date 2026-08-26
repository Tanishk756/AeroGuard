# Stage E Audit Infrastructure

Stage E provides local, append-only security audit infrastructure for the existing authentication, authorization, and RBAC workflows. It does not add audit UI, sensors, simulation, AI, WebSockets, or future identity workflows.

## Events

Events use version `1` and a controlled vocabulary: `LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`, `SESSION_CREATED`, `SESSION_REVOKED`, `SESSION_EXPIRED`, `AUTHORIZATION_DENIED`, `ROLE_CREATED`, `ROLE_UPDATED`, `ROLE_DELETED`, `ROLE_ASSIGNED`, `ROLE_REVOKED`, `PERMISSION_ASSIGNED`, `PERMISSION_REVOKED`, `SUPER_ADMIN_BOOTSTRAPPED`, and `SECURITY_POLICY_VIOLATION`. Results are restricted to `SUCCESS`, `FAILURE`, and `DENIED`. Successful authorization checks are not recorded by default.

## Transactions and security

`AuditService.record_event()` validates and adds an event to the caller's SQLAlchemy transaction but never commits. Successful security-sensitive operations validate, authorize, mutate, record, and commit together. A failed commit rolls back both operation and audit record. Failed login and authorization events use bounded best-effort persistence so audit failure cannot turn a 401 or 403 into a 500.

Metadata is recursively sanitized, including suspicious key variants in nested mappings and collections. It is bounded to 16 KiB serialized, six nesting levels, 100 collection items, and 512-character strings. Secret values, credentials, cookies, tokens, authorization data, hashes, and keys are redacted. Correlation IDs are tracing identifiers only and never establish actor identity.

## Query API

`GET /api/v1/audit/events` and `GET /api/v1/audit/events/{id}` require `audit.read`. The list endpoint supports bounded event, result, actor, target, permission, and UTC date filters. Results use descending `(timestamp, id)` cursor pagination with a default page size of 50 and a maximum of 100. There are no audit write or delete endpoints.

## Immutability and limitations

The service rejects ORM updates and deletes, and SQLite migrations install update and delete triggers. This is append-only application and database protection, not cryptographic immutability. Direct modification of the SQLite file is outside the guarantee. Stage E intentionally does not add hash chains, external logging infrastructure, retention jobs, or regulatory-compliance claims. Retention remains an operational policy; larger deployments may later move query/storage concerns behind a dedicated durable event pipeline.

Client IP uses `request.client.host`; `X-Forwarded-For` is not trusted. Deployments behind a proxy must establish and document a trusted proxy boundary before changing this behavior.