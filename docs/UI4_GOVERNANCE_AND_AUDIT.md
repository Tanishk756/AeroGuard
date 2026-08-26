# Stage UI4 — Mission Governance, Security Audit & Administrative Operations

## 1. Overview
Stage UI4 delivers the complete enterprise governance, security auditing, and platform diagnostics surface for the AeroGuard Operator Console. It establishes visual observability over the backend tamper-evident audit ledger (Stage E), granular RBAC access controls (Stage D), and platform runtime health (Stage B).

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          AEROGUARD OPERATOR CONSOLE                         │
├─────────────────────────────────────────────────────────────────────────────┤
│  OPERATIONAL LAYER          │  HISTORICAL & SIMULATION  │  GOVERNANCE & ADM │
│  • TacticalMap (Pure SVG)   │  • Scenario Simulation    │  • Audit Explorer │
│  • Entity Inspectors        │  • Replay Analysis        │  • RBAC Governance│
│  • Command Palette (Ctrl+K) │  • Analytics Hub          │  • Diagnostics    │
└─────────────────────────────┴───────────────────────────┴───────────────────┘
```

---

## 2. Architecture & Subsystems

### A. Security Audit Log Explorer (`AuditLogPage.tsx` & `AuditEventInspector.tsx`)
- **Engine**: Direct consumer of Stage E append-only audit event tables via `GET /api/v1/audit/events` and `GET /api/v1/audit/events/{id}`.
- **Cursor-Based Pagination**: Sequential forward and backward navigation preserving server-authoritative cursor tokens without full-table offsets.
- **Comprehensive Filtering**:
  - Event Type (`LOGIN_SUCCESS`, `LOGIN_FAILURE`, `LOGOUT`, `SESSION_CREATED`, `SESSION_REVOKED`, `ROLE_CREATED`, `ROLE_UPDATED`, `ROLE_DELETED`, `ROLE_ASSIGNED`, `ROLE_REVOKED`, `PERMISSION_ASSIGNED`, `PERMISSION_REVOKED`).
  - Result outcome (`SUCCESS`, `FAILURE`).
  - Actor User ID, Target Type (`user`, `role`, `session`, `sensor`, `track`), Target ID, and Permission key.
  - UTC Date-Time range filtering (`date_from`, `date_to`) with quick presets (`1h`, `6h`, `24h`, `7d`).
- **Contextual Inspector**: Detail drawer for comprehensive metadata analysis, correlation ID tracking, source IP, user-agent inspection, and one-click actor/target cross-filtering.
- **Security & Privacy Boundary**: Passwords, secrets, and raw authentication tokens are strictly omitted from rendered payloads.

### B. RBAC Role & Access Governance (`RbacPage.tsx`)
- **Roles Directory**: Lists all system-reserved and custom operational roles, showing active permission count and system immutability badges.
- **Custom Role Builder**: Form for creating new custom roles adhering to backend regex constraints (`^[A-Z][A-Z0-9_]+$`) and descriptions.
- **Permission Grant Matrix**: Visual domain-grouped matrix (`tracks`, `sensors`, `alerts`, `threats`, `scenarios`, `roles`, `permissions`, `audit`, `system`) allowing granular permission toggling on custom roles.
- **System Role Protection**: System-reserved roles (`SUPER_ADMIN`, `SYSTEM_ADMIN`, `OPERATIONS_ADMIN`, `SECURITY_ADMIN`, `OPERATOR`, `ANALYST`, `RESEARCHER`, `VIEWER`) are permanently protected against deletion and structural mutation.
- **User Role Management**: Direct assignment and revocation of role memberships for specific User IDs (`POST/DELETE /api/v1/users/{user_id}/roles/{role_id}`).
- **User Discovery Limitation Notice**: In accordance with AeroGuard zero-trust principles, unauthenticated user lists are not exposed. Administrators provide the explicit target User ID to modify role assignments.

### C. Platform Diagnostics & System Health (`DiagnosticsPage.tsx`)
- **Database Connectivity**: Real-time evaluation of database health (`SELECT 1`) via public `GET /api/v1/health`.
- **Runtime Environment**: Protected system inspection (`GET /api/v1/system/info`, requiring `system.read`) reporting application version, environment, Python runtime version, platform architecture, and debug flags.
- **Operator Session Identity**: Live telemetry from active session context displaying authenticated username, display name, account status, assigned roles, and granted permission counts.
- **Confidentiality Invariant**: Database connection strings, environment secrets, and sensitive server variables are strictly omitted.

---

## 3. Route & Permission Matrix

| Path | Route Component | Required Permissions | Description |
|---|---|---|---|
| `/app/audit` | `AuditLogPage` | `audit.read` | Security audit ledger & event inspector |
| `/app/rbac` | `RbacPage` | `roles.read` OR `permissions.read` | Role directory, matrix & role assignment |
| `/app/diagnostics` | `DiagnosticsPage` | `system.read` | Platform diagnostics & database health |

### Administrative Action Permissions

| Action | API Endpoint | Required Permission |
|---|---|---|
| Create Custom Role | `POST /api/v1/roles` | `roles.create` |
| Update Role Description | `PATCH /api/v1/roles/{id}` | `roles.update` |
| Delete Custom Role | `DELETE /api/v1/roles/{id}` | `roles.delete` |
| Assign Role Permission | `POST /api/v1/roles/{id}/permissions/{id}` | `roles.update` |
| Revoke Role Permission | `DELETE /api/v1/roles/{id}/permissions/{id}` | `roles.update` |
| Assign User Role | `POST /api/v1/users/{user_id}/roles/{role_id}` | `roles.assign` |
| Revoke User Role | `DELETE /api/v1/users/{user_id}/roles/{role_id}` | `roles.assign` |

---

## 4. Command Palette Integration

| Shortcut | Command | Destination |
|---|---|---|
| `g u` | Go to Security Audit Explorer | `/app/audit` |
| `g k` | Go to RBAC Role Governance | `/app/rbac` |
| `g d` | Go to System Platform Diagnostics | `/app/diagnostics` |

---

## 5. Security & Architectural Invariants

1. **HttpOnly Cookie Authentication**: All API requests utilize `credentials: 'include'`. No tokens are stored in `localStorage`, `sessionStorage`, or `indexedDB`.
2. **Defensive Non-Offensive Scope**: AeroGuard is strictly an analysis, simulation, and situational-awareness platform.
3. **Backend Authority**: Role mutations and permission assignments are strictly validated and authorized on the backend. System-reserved roles cannot be modified or deleted.
4. **Accessible Tactical UI**: Adheres to high-contrast dark theme, semantic table and dialog markup, keyboard navigation, and visible focus rings.
