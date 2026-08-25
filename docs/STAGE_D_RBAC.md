# Stage D RBAC

Stage D adds server-side role-based access control to the Stage C session
foundation. Authentication remains cookie-based; authorization resolves the
user's current database roles and permissions on each request.

## Roles and permissions

The eight immutable system roles are `SUPER_ADMIN`, `SYSTEM_ADMIN`,
`SECURITY_ADMIN`, `OPERATIONS_ADMIN`, `OPERATOR`, `ANALYST`, `RESEARCHER`, and
`VIEWER`. System roles have `is_system=true`, cannot be renamed or deleted,
and are not username-based bypasses.

The exact permission vocabulary is:

```text
users.read users.create users.update users.disable users.delete
roles.read roles.create roles.update roles.delete roles.assign permissions.read
sessions.read sessions.revoke system.read system.configure
sensors.read sensors.configure
scenarios.read scenarios.create scenarios.update scenarios.delete scenarios.run
tracks.read alerts.read threats.read models.read models.deploy audit.read
```

Permissions are exact allow keys. There are no wildcards or deny rules. Sensor,
scenario, track, alert, threat, model, and audit keys do not implement those
future subsystems.

Role mappings are seeded deterministically in migration `0003_rbac.py`:

| Role | Permission set |
| --- | --- |
| SUPER_ADMIN | All listed permissions |
| SYSTEM_ADMIN | system.read, system.configure, users.read, roles.read, permissions.read, sessions.read, sessions.revoke |
| SECURITY_ADMIN | users.read, users.create, users.update, users.disable, roles.read, roles.assign, permissions.read, sessions.read, sessions.revoke |
| OPERATIONS_ADMIN | system.read, users.read, sessions.read, sensors.read, sensors.configure, scenarios.read, scenarios.create, scenarios.update, scenarios.delete, scenarios.run, tracks.read, alerts.read, threats.read |
| OPERATOR | system.read, sensors.read, scenarios.read, scenarios.run, tracks.read, alerts.read, threats.read |
| ANALYST | system.read, scenarios.read, tracks.read, alerts.read, threats.read, models.read |
| RESEARCHER | system.read, scenarios.read, scenarios.create, scenarios.update, scenarios.run, tracks.read, models.read |
| VIEWER | system.read, tracks.read, alerts.read, threats.read |

## Authorization

Reusable dependency factories provide `require_permission`,
`require_any_permission`, and `require_all_permissions`. They build on Stage C
authentication and evaluate current database state without caching. Missing or
invalid sessions return `401`; authenticated users without permission return a
structured `403 AUTH_FORBIDDEN` without revealing missing permission details.

## API protection

- `/api/v1/health` remains public.
- Login remains public.
- Logout and `/api/v1/me` require authentication only.
- `/api/v1/system/info` requires `system.read`.
- Role listing/detail requires `roles.read`.
- Role creation requires `roles.create`.
- Role updates/deletion require `roles.update`/`roles.delete`.
- Permission listing requires `permissions.read`.
- User-role assignment/revocation requires `roles.assign`.
- Role-permission mutation requires `roles.update` and is forbidden for system roles.

Management responses never expose passwords, password hashes, session secrets, or
session hashes.

## Bootstrap and protections

Migration seeding creates no users and assigns no roles to existing users. The
explicit `seed-rbac` command is idempotent. The explicit `bootstrap-rbac`
command targets an existing active user, requires typing `BOOTSTRAP`, grants
`SUPER_ADMIN` only when no active `SUPER_ADMIN` exists, and rejects replay.

Role assignment is conservative: the target role's effective permissions must
be a subset of the actor's effective permissions. System roles cannot be
renamed or deleted, and reserved names cannot be used by custom roles. The
final active `SUPER_ADMIN` cannot lose that role. SQLite security mutations use
an immediate writer transaction, and the reusable final-admin invariant is
available to future user lifecycle operations. All checks occur in the service
layer and role changes are visible immediately because permissions are resolved
per request.

## Limitations and deferred work

RBAC mutations are not yet audit logged. Tenant/scope restrictions, session
invalidation policies, frontend RBAC UI, WebSocket authorization, API keys,
MFA, password reset, lockout, rate limiting, sensors, simulation, AI, threat
assessment, autonomous behavior, and Tauri remain deferred.