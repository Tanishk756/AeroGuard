# Stage UI1 Operator Console Foundation

Stage UI1 establishes the production frontend architecture, visual design language, application shell, authentication and session integration, RBAC-aware navigation, and the core operator workspace for AeroGuard.

```text
┌─────────────────────────────────────────────────────────────┐
│ SYSTEM / MISSION HEADER (Identity, Status, User, Role, UTC) │
├────────────┬────────────────────────────────────┬───────────┤
│            │                                    │           │
│ NAVIGATION │       PRIMARY WORKSPACE            │ CONTEXT   │
│ (RBAC      │    (Tactical Map Foundation,       │ PANELS    │
│  Filtered) │     Track, Alert, Threat, Timeline)│           │
│            │                                    │           │
├────────────┴────────────────────────────────────┴───────────┤
│ STATUS / SYSTEM FOOTER (Connectivity, DB Health, Scope)     │
└─────────────────────────────────────────────────────────────┘
```

---

## 1. Architectural Principles & Safety Boundaries

- **Zero Client-Side Authoritative Logic**: The frontend operates strictly as a presentation, triage, and operational workspace layer. Track association (F3), multi-sensor fusion (F4), operational threat scoring (F4), simulation execution (F5), and replay state reconstruction (F6) remain strictly authoritative in the backend.
- **Defensive Situational Awareness**: The console is designed specifically for defensive counter-UAS monitoring, research, simulation observation, and threat triage. It contains zero offensive controls, weapon guidance, intercept commands, jamming triggers, or autonomous engagement logic.
- **HttpOnly Cookie Authentication**: Authenticates against `POST /api/v1/auth/login`, `POST /api/v1/auth/logout`, and `GET /api/v1/me`. Zero JWTs, passwords, or session secrets are stored in `localStorage` or `sessionStorage`. All requests include `credentials: 'include'`.
- **RBAC-Aware Navigation**: Navigational surfaces dynamically reflect the authenticated user's permissions (`tracks.read`, `sensors.read`, `alerts.read`, `threats.read`, `scenarios.read`, `system.read`). The frontend enforces navigation guards (`ProtectedRoute`), while the backend remains the authoritative gatekeeper.
- **Zero Real-Time Streaming in UI1**: UI1 explicitly excludes WebSockets/SSE. All data feeds (tracks, alerts, threats, timeline) consume existing REST APIs with bounded and manual refresh controls.
- **No Fabricated Telemetry**: Empty datasets from the backend render explicit, clean empty states rather than simulated fake objects.

---

## 2. Frontend Structure (`apps/operator/src/`)

```text
apps/operator/src/
  ├── api/                # Centralized typed API clients (cookie-based, error handling)
  │   ├── client.ts       # Shared request helper, ApiError class, query serialization
  │   ├── auth.ts         # login, logout, getMe
  │   ├── system.ts       # getHealth, getSystemInfo (requires system.read)
  │   ├── tracks.ts       # getTracks, getTrackDetail, getTrackHistory
  │   ├── sensors.ts      # getSensors, getSensorDetail
  │   ├── alerts.ts       # getAlerts, getAlertDetail
  │   ├── threats.ts      # getThreats, getThreatDetail
  │   ├── history.ts      # Historical detections, alerts, threats, timeline
  │   ├── analytics.ts    # Analytics summary and domain metrics
  │   └── replay.ts       # Snapshot query, virtual clock step, run comparison
  ├── types/              # TypeScript interfaces mirroring backend schemas
  ├── context/            # Global state (AuthContext, SystemContext)
  ├── components/
  │   ├── common/         # StatusBadge, Button, Card, LoadingState, ErrorState, EmptyState
  │   ├── layout/         # AppHeader, AppSidebar, AppFooter, AppShell
  │   └── workspace/      # MapWorkspace, TrackPanel, AlertPanel, ThreatPanel, TimelinePanel
  ├── pages/              # LoginPage, OverviewPage, TracksPage, SensorsPage, AlertsPage,
  │                       # ThreatsPage, HistoryPage, ReplayPage, AnalyticsPage, ModulePlaceholder
  ├── routes/             # AppRoutes, ProtectedRoute (Auth & RBAC guard)
  ├── styles/             # tokens.css (tactical design system), globals.css
  ├── App.tsx             # Root application with router & context providers
  └── main.tsx            # React 18 DOM mount point
```

---

## 3. Visual Language & Tactical Design Tokens

AeroGuard utilizes a purpose-built tactical dark design system configured in `src/styles/tokens.css`:
- **Surface Palette**: Deep tactical navy and carbon (`#060d15`, `#0b1724`, `#102235`).
- **Accent & Data**: High-contrast cyan (`#38bdf8`) for active selections and radar sweeps.
- **Semantic Statuses**:
  - `ACTIVE` / `NORMAL` / `RESOLVED`: Green (`#22c55e` / `rgba(34,197,94,0.12)`)
  - `WARNING` / `STALE` / `DEGRADED`: Amber (`#f59e0b` / `rgba(245,158,11,0.12)`)
  - `CRITICAL` / `HIGH` / `LOST` / `OPEN`: Red (`#ef4444` / `rgba(239,68,68,0.14)`)
  - `INFO` / `SIMULATION` / `NEW`: Cyan (`#38bdf8` / `rgba(56,189,248,0.12)`)
  - `OFFLINE` / `INACTIVE` / `ARCHIVED`: Slate (`#64748b` / `rgba(100,116,139,0.15)`)
- **Non-Color Indicators**: `StatusBadge` components combine background, border, micro-dots, and distinct unicode glyph symbols (`●`, `▲`, `■`, `◆`, `○`) to ensure accessibility across high-contrast environments.

---

## 4. Workspaces & Panels Implemented

### 4.1 Overview Workspace (`/app/overview`)
- **KPI Summary**: Active track counter, open alerts, elevated threat postures, and online sensor assets.
- **Tactical Map View (`MapWorkspace`)**: Structured placeholder featuring WGS84 coordinate grid, concentric range rings (500m, 1000m, 2000m), cardinal orientation, reticle axes, and track marker rendering.
- **Track Registry Panel (`TrackPanel`)**: Compact table displaying track state, classification, quality/confidence score, source count, and coordinates.
- **Threat Assessment Triage (`ThreatPanel`)**: Operational priority ranking with scores (0–100) and contributing kinematic factor summaries.
- **Alert Feed (`AlertPanel`)**: REST-queried active and unacknowledged alerts with severity badges and track references.
- **Operational Timeline (`TimelinePanel`)**: Multi-source normalized event sequence with UTC timestamps.

### 4.2 Track Management & Trajectory History (`/app/tracks`)
- Filterable track list (by `state` and `classification`).
- Inspector view showing full kinematic properties and append-only historical trajectory table (`GET /api/v1/tracks/{id}/history`).

### 4.3 Sensor Inventory (`/app/sensors`)
- Read-only asset catalog displaying sensor ID, modality, source class (`REAL`, `SIMULATION`), coordinates, and status.

### 4.4 Alert Triage (`/app/alerts`)
- Dedicated alert review table filterable by severity (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`) and status (`OPEN`, `ACKNOWLEDGED`, `RESOLVED`).

### 4.5 Threat Assessment View (`/app/threats`)
- Operational priority triage filterable by threat level.

### 4.6 Historical Telemetry & Logs (`/app/history`)
- Bounded time-window query tool for historical detections, alerts, threats, and normalized timelines with backend pagination.

### 4.7 Replay Interface (`/app/replay`)
- Frontend client for the F6 replay API supporting time window specification, initial snapshot query (`POST /api/v1/replay/query`), and single-step forward advancement (`POST /api/v1/replay/step`) with reconstructed state display.

### 4.8 Operational Analytics (`/app/analytics`)
- Visual dashboard consuming `GET /api/v1/analytics/summary` displaying total metrics, modality breakdowns, track lifecycle distributions, and threat score distributions using lightweight SVG/CSS visual bars.

---

## 5. Security & RBAC Guarding

1. **Authentication Boundary**: Unauthenticated requests are intercepted by `ProtectedRoute`, redirecting users to `/login`.
2. **Permission Verification**: Protected views check permissions (`tracks.read`, `sensors.read`, `alerts.read`, `threats.read`, etc.). Unauthorized users are served a clear 403 Access Denied panel displaying the missing permission and current role context.
3. **Sensitive Endpoint Protection**: `SystemContext` checks for `system.read` authority before requesting `GET /api/v1/system/info`, falling back gracefully to public `GET /api/v1/health` when unauthorized.

---

## 6. Verification and Validation

- **TypeScript Compilation**: `npm --prefix apps/operator run typecheck` passes with zero errors.
- **Production Bundle Build**: `npm --prefix apps/operator run build` produces optimized Vite production assets with zero errors.
- **Unit Testing**: `npm test` executes the 16-test suite covering RBAC evaluation, query serialization, status badge semantic mapping, and error classification.
- **Backend Regression**: Full backend regression suite (`pytest -v`) confirms 145/145 tests pass.

---

## 7. Future UI Stages (Roadmap Boundaries)

- **UI2**: Advanced operational map and track visualization (real GIS integration, WebGL/WebGPU layers, vector tiles).
- **UI3**: Alerts and threat management workflows (operator acknowledgement, triage notes, incident assignment).
- **UI4**: Scenario and simulation control interface (synthetic target path builder, sensor placement, scenario start/pause/step controls).
- **UI5**: Advanced history, replay, and comparative analytics tooling.
- **UI6**: Admin Console (user management, RBAC role configuration, audit log viewer).
- **UI7**: Developer and API Console.
- **UI8**: Desktop and native packaging (Tauri 2 integration).
