# Stage UI4 Implementation Plan — Mission Governance & Security Audit Console

## 1. Stage Name
**Stage UI4 — Mission Governance, Security Audit & Administrative Operations**

---

## 2. Problem Statement
The AeroGuard backend provides enterprise-grade, deterministic access control (Stage D: RBAC API with roles, permissions, and user assignments) and tamper-evident append-only security audit event recording (Stage E: Audit API with cursor pagination, actor tracking, and result logging), as well as system runtime introspection (Stage B). 

However, the frontend currently has **zero interface** for auditing security events, administering custom roles and permissions, inspecting user authority, or reviewing platform diagnostics. Operators and administrators currently cannot view audit trails, verify role assignments, inspect permission boundaries, or monitor system operational health without directly querying the database or raw API endpoints.

---

## 3. User & Operator Value
- **Security & Compliance Auditing**: Security administrators and compliance officers can inspect the immutable audit trail with sub-second cursor pagination, filter by event type, actor ID, target entity, outcome result (`SUCCESS`/`FAILURE`), and date range, and inspect detailed audit payloads.
- **RBAC Role & Permission Management**: Operations administrators can view active roles, inspect assigned permissions, create custom roles with scoped descriptions, and manage user role assignments with full server-side permission checks (`roles.read`, `roles.create`, `roles.update`, `roles.delete`, `roles.assign`, `permissions.read`).
- **System Telemetry & Platform Diagnostics**: Administrators can inspect environment parameters, database connectivity health (`SELECT 1`), Python runtime specifications, active configuration flags, and server uptime.
- **Command Palette & Global Navigation Integration**: Direct navigation shortcuts (`g u` for audit, `g k` for RBAC, `g d` for diagnostics) in the global Command Palette.

---

## 4. Exact Scope
1. **Audit Log Explorer Subsystem**:
   - `AuditLogPage` with responsive data table and cursor-based infinite/page pagination.
   - Audit filter bar: Event Type (`LOGIN_SUCCESS`, `LOGIN_FAILURE`, `ROLE_CREATED`, `ROLE_UPDATED`, `ROLE_DELETED`, `ROLE_ASSIGNED`, `ROLE_REVOKED`, `PERMISSION_ASSIGNED`, `PERMISSION_REVOKED`, `SESSION_CREATED`, `SESSION_REVOKED`), Result (`SUCCESS`, `FAILURE`), Actor User ID, Target Type (`user`, `role`, `session`), Target ID, and UTC Date Range (`date_from`, `date_to`).
   - `AuditEventInspector`: Contextual drawer/card inspecting full event schema (Event ID, Timestamp UTC, Actor ID, Event Type, Action, Result, Correlation ID, Source IP, User Agent, Target Type, Target ID, Permission Key, and structured Metadata JSON).
2. **RBAC & Role Governance Subsystem**:
   - `RbacPage` tabbed into:
     - **Roles Directory**: List all system and custom roles (`SUPER_ADMIN`, `SYSTEM_ADMIN`, `OPERATIONS_ADMIN`, `SECURITY_ADMIN`, `OPERATOR`, `ANALYST`, `RESEARCHER`, `VIEWER`, plus custom roles), showing name, description, assigned permissions count, and system immutability badge.
     - **Role Creator & Editor Modal/Drawer**: Create custom roles with name and description, and manage permission assignments (`assign_permission`, `revoke_permission`) with permission dependency validation.
     - **User Role Management**: Search user by ID, inspect active role assignments, and assign/revoke roles (`roles.assign`).
     - **Permission Dictionary**: Read-only directory of all granular permissions across all domains (`tracks.*`, `sensors.*`, `alerts.*`, `threats.*`, `scenarios.*`, `roles.*`, `permissions.*`, `audit.*`, `system.*`).
3. **System Diagnostics & Platform Health Subsystem**:
   - `DiagnosticsPage`: Comprehensive overview displaying database health, application runtime version, Python environment details, platform architecture, debug flags, and live session status.
4. **Navigation & Route Protection**:
   - Register routes `/app/audit`, `/app/rbac`, and `/app/diagnostics` in `AppRoutes.tsx`.
   - Update `AppSidebar.tsx` with a dedicated "Governance & Admin" navigation section protected by `audit.read`, `roles.read`, and `system.read`.
   - Update `CommandPalette.tsx` with governance navigation commands (`g u`, `g k`, `g d`).
5. **Types & REST API Clients**:
   - Create `apps/operator/src/types/audit.ts` and `apps/operator/src/types/rbac.ts`.
   - Create `apps/operator/src/api/audit.ts` and `apps/operator/src/api/rbac.ts`.
   - Update `apps/operator/src/api/system.ts` to export `getSystemInfo` (`system.read`).

---

## 5. Explicit Exclusions
- **No Direct Password Mutation in Frontend**: Passwords remain exclusively managed via existing Argon2id authentication flows.
- **No Modification of System Roles**: System-reserved roles (`SUPER_ADMIN`, `OPERATOR`, etc.) are protected on backend and marked immutable/read-only in UI.
- **No WebSocket/SSE Streams**: All audit and RBAC management operations use standard REST with cursor pagination and explicit refresh triggers.
- **No External Authorization Libraries**: Uses pure TypeScript RBAC helpers (`hasPermission`, `hasAnyPermission`) backed by server-authoritative API responses.
- **No Token/Local Storage**: Strictly preserves HttpOnly cookie sessions.

---

## 6. Existing Backend Dependencies
- `GET /api/v1/audit/events` (`audit.read`)
- `GET /api/v1/audit/events/{id}` (`audit.read`)
- `GET /api/v1/roles` (`roles.read`)
- `POST /api/v1/roles` (`roles.create`)
- `GET /api/v1/roles/{id}` (`roles.read`)
- `PATCH /api/v1/roles/{id}` (`roles.update`)
- `DELETE /api/v1/roles/{id}` (`roles.delete`)
- `GET /api/v1/permissions` (`permissions.read`)
- `POST /api/v1/users/{id}/roles/{id}` (`roles.assign`)
- `DELETE /api/v1/users/{id}/roles/{id}` (`roles.assign`)
- `POST /api/v1/roles/{id}/permissions/{id}` (`roles.update`)
- `DELETE /api/v1/roles/{id}/permissions/{id}` (`roles.update`)
- `GET /api/v1/system/info` (`system.read`)
- `GET /api/v1/health` (public)

---

## 7. Existing Frontend Dependencies
- `apps/operator/src/components/common/` (`Button`, `Card`, `StatusBadge`, `EmptyState`, `ErrorState`, `LoadingState`)
- `apps/operator/src/context/AuthContext.tsx` (`useAuth`, `hasPermission`, `hasAnyPermission`)
- `apps/operator/src/context/SystemContext.tsx` (`useSystem`)
- `apps/operator/src/routes/ProtectedRoute.tsx`
- `apps/operator/src/components/layout/` (`AppHeader`, `AppSidebar`, `AppShell`)
- `apps/operator/src/components/command/CommandPalette.tsx`

---

## 8. New Files (8 files)
1. `apps/operator/src/types/audit.ts` — TypeScript types for AuditEvent, AuditEventPage, AuditFilterParams.
2. `apps/operator/src/types/rbac.ts` — TypeScript types for Role, Permission, RoleCreate, RoleUpdate, RoleAssignment.
3. `apps/operator/src/api/audit.ts` — REST client for audit queries and cursor-based pagination.
4. `apps/operator/src/api/rbac.ts` — REST client for role CRUD, permission assignments, and user role management.
5. `apps/operator/src/components/inspector/AuditEventInspector.tsx` — Contextual drawer/card for detailed audit record inspection.
6. `apps/operator/src/pages/AuditLogPage.tsx` — Security audit explorer with filter bar, cursor paging, and inspection.
7. `apps/operator/src/pages/RbacPage.tsx` — Role directory, custom role builder, permission dictionary, and user role assignment hub.
8. `apps/operator/src/pages/DiagnosticsPage.tsx` — System diagnostics, runtime configuration, and database health dashboard.

---

## 9. Modified Files (8 files)
1. `apps/operator/src/types/index.ts` — Export `audit` and `rbac` types.
2. `apps/operator/src/api/index.ts` — Export `audit` and `rbac` API clients.
3. `apps/operator/src/api/system.ts` — Add `getSystemInfo` function.
4. `apps/operator/src/routes/AppRoutes.tsx` — Register `/app/audit`, `/app/rbac`, and `/app/diagnostics` routes.
5. `apps/operator/src/components/layout/AppSidebar.tsx` — Add Governance navigation section.
6. `apps/operator/src/components/command/CommandPalette.tsx` — Add navigation shortcuts for Audit, RBAC, Diagnostics.
7. `apps/operator/src/test/governance.test.ts` (new test suite) — Frontend unit tests for audit filters, cursor parsing, RBAC validation, and role mutation rules.
8. `docs/UI4_GOVERNANCE_AND_AUDIT.md` — Complete documentation for Stage UI4.

---

## 10. API Contracts Used

### Audit API
```typescript
export interface AuditEvent {
  id: string;
  timestamp: string;
  actor_user_id?: string | null;
  event_type: string;
  action: string;
  result: 'SUCCESS' | 'FAILURE';
  correlation_id?: string | null;
  source_ip?: string | null;
  user_agent?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  permission?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AuditEventPage {
  items: AuditEvent[];
  next_cursor?: string | null;
}
```

### RBAC API
```typescript
export interface Role {
  id: string;
  name: string;
  description?: string | null;
  is_system: boolean;
  permissions?: Permission[];
}

export interface Permission {
  id: string;
  key: string;
  description?: string | null;
  domain: string;
}

export interface RoleAssignment {
  user_id: string;
  role_id: string;
  role_name: string;
}
```

---

## 11. RBAC Requirements
- `/app/audit`: Requires `audit.read`
- `/app/rbac`: Requires `roles.read` or `permissions.read`
- Role Creation: Requires `roles.create`
- Role Updating / Permission Assignment: Requires `roles.update`
- Role Deletion: Requires `roles.delete`
- User Role Assignment / Revocation: Requires `roles.assign`
- `/app/diagnostics`: Requires `system.read`

---

## 12. State-Management Design
- **Audit Cursor State**: Maintains current page cursor history stack (`cursorStack: string[]`) enabling both forward pagination and clean back-paging.
- **Role & Permission State**: Cached locally during active session; invalidates and refreshes upon successful mutation (`add_role`, `patch_role`, `remove_role`, `add_permission`, `revoke_permission`).
- **Separation of Selection and Network Operations**: Clicking an audit event updates synchronous inspection state; detailed audit payload is displayed immediately from the page cache.

---

## 13. Error / Loading / Stale-State Behavior
- Standard `LoadingState` spinner during query execution.
- Standard `ErrorState` with actionable retry buttons on network or API failures.
- Non-blocking error alerts on mutation failures (e.g., duplicate role name, 409 conflict, or permission denied).
- Empty states with informative copy when queries return 0 records.

---

## 14. Accessibility Requirements
- Semantic HTML tables with `<th scope="col">` and keyboard-navigable rows.
- Modal dialogs with `role="dialog"`, `aria-modal="true"`, and `Escape` key listeners.
- High-contrast badges for audit outcomes (`SUCCESS` green, `FAILURE` red).
- Proper ARIA labels on all form inputs and action buttons.

---

## 15. Performance Considerations
- Maximum `limit=50` or `100` per page on audit queries.
- Bounded date-time range filters to prevent table full-scans.
- Zero client-side re-sorting of cursor-paginated backend results.

---

## 16. Test Strategy
- Unit tests in `apps/operator/src/test/governance.test.ts`:
  - Audit filter parameter serialization (event type, result, actor, date range).
  - Cursor pagination state stack traversal.
  - Role creation validation (alphanumeric, non-empty).
  - Permission grouping by domain.
  - Immutable system role protection in UI.
  - RBAC permission check verification for administrative actions.

---

## 17. Security Checks
- Verify zero token storage in `localStorage`, `sessionStorage`, or `indexedDB`.
- Verify all mutation requests pass through `credentials: 'include'` session cookie auth.
- Verify system roles cannot be edited or deleted from UI controls.

---

## 18. Documentation Changes
- Create `docs/UI4_GOVERNANCE_AND_AUDIT.md`.
- Update `docs/ARCHITECTURE.md`, `docs/PHASE1_IMPLEMENTATION.md`, and `docs/ROADMAP.md`.

---

## 19. Acceptance Criteria
1. Security Admins with `audit.read` can view the audit log with event filtering, cursor pagination, and payload inspection.
2. Operations Admins with `roles.read` can view the roles directory and permission matrix.
3. Operations Admins with `roles.create`, `roles.update`, and `roles.delete` can create, modify description, and delete custom roles.
4. Users with `roles.assign` can assign and revoke roles for users.
5. Users with `system.read` can view system runtime and platform diagnostic telemetry.
6. Command palette includes shortcuts to jump to Audit, RBAC, and Diagnostics.
7. All frontend unit tests, typechecks, build, and backend regression tests pass with 0 errors.

---

## 20. Definition of Done
- 8 new files created and 8 existing files modified.
- `npm test` passes with >= 55 unit tests.
- `npm --prefix apps/operator run typecheck` passes with 0 errors.
- `npm --prefix apps/operator run build` builds cleanly.
- `pytest -v` passes 145/145 tests.
- Zero token storage or offensive terms in codebase.
