# Stage UI7 — Developer and API Console

## 1. Overview
Stage UI7 delivers the **Developer and API Console** for the AeroGuard platform. Designed for systems engineers, integration developers, and testing operators, it provides a comprehensive workspace for REST API discovery, interactive request execution with live latency/telemetry inspection, synthetic sensor detection ingestion workbench (`POST /api/v1/sensors/{id}/detections`), Pydantic model contract inspection, and multi-format integration code generation (PowerShell cURL, POSIX cURL, and JavaScript `fetch()`).

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STAGE UI7 — DEVELOPER & API CONSOLE                │
├─────────────────────────────────────────────────────────────────────────────┤
│  API CATALOG & EXPLORER       │  INTERACTIVE REQUEST DISPATCHER             │
│  • 8 Versioned REST Domains   │  • Dynamic path/query parameter builder     │
│  • Method & RBAC permission   │  • Request body JSON editor & validator     │
│  • Fast full-text search      │  • Round-trip execution latency (ms)        │
│  • Quick cURL command copy    │  • Correlation ID & response headers        │
├───────────────────────────────┼─────────────────────────────────────────────┤
│  DETECTION INGESTION WORKBENCH│  SCHEMA & DATA CONTRACT VIEWER              │
│  • Radar, RF, Optical presets │  • Canonical Pydantic schemas               │
│  • Live coordinate validator  │  • Field-level type & boundary constraints  │
│  • sensors.configure gate     │  • cURL & fetch() snippet generators        │
│  • Ingestion result status    │  • Ephemeral in-memory test runner          │
└───────────────────────────────┴─────────────────────────────────────────────┘
```

---

## 2. Architecture & Subsystems

### A. API Catalog & Explorer (`/app/developer?tab=catalog`)
- **8 Versioned API Domains**: Complete mapping of backend routes under `/api/v1`:
  1. *Platform & Health*: `GET /health`, `GET /system/info`
  2. *Authentication & Session*: `POST /auth/login`, `POST /auth/logout`, `GET /me`
  3. *Sensor Ingestion*: `GET /sensors`, `GET /sensors/{id}`, `POST /sensors/{id}/detections`
  4. *Tracking & Fusion*: `GET /tracks`, `GET /tracks/{id}`, `GET /tracks/{id}/history`
  5. *Intelligence & Defense*: `GET /alerts`, `GET /alerts/{id}`, `GET /threats`, `GET /threats/{id}`, `GET/POST /geofences`
  6. *Simulation & Scenarios*: `GET /scenarios`, `GET /scenarios/{id}`, simulation clock controls (`prepare`, `start`, `pause`, `resume`, `step`, `stop`, `reset`)
  7. *Historical & Analytics*: `GET /history/*`, `GET /analytics/*`, `POST /replay/*`
  8. *Governance & RBAC*: `GET /audit/*`, `GET/POST/PATCH/DELETE /roles`, `GET /permissions`
- **Dynamic Search & Domain Filtering**: Filter by method (`GET`, `POST`, `PUT`, `DELETE`), endpoint name, path substring, or required RBAC authority.
- **RBAC Authority Indicators**: Displays required permission for each endpoint and indicates whether the active session holds the necessary grant.

### B. Interactive Request Dispatcher (`/app/developer?tab=dispatcher`)
- **Dynamic Parameter Builder**: Generates path parameter inputs (`{sensor_id}`, `{track_id}`, `{scenario_id}`) and query parameters with default suggestions.
- **JSON Request Body Editor**: In-browser payload editor with JSON syntax validation and auto-formatting.
- **Live Dispatch Runner**: Dispatches requests via `credentials: 'include'`, authenticating with the existing opaque session cookie.
- **Telemetry & Response Inspector**:
  - Response status code badge (e.g. 200, 201, 400, 403, 404, 500).
  - Round-trip execution latency in milliseconds.
  - Traceability inspection via `X-Correlation-ID` header.
  - Collapsible JSON response body viewer with syntax highlighting and one-click copy.

### C. Synthetic Sensor Detection Ingestion Workbench (`/app/developer?tab=workbench`)
- **Sensor Selector**: Discovers registered sensors via `GET /api/v1/sensors`.
- **Modality Presets**:
  - *Radar UAV Detection*: Fast small drone with Doppler velocity, SNR, and RCS.
  - *RF Spectrum Emitter*: 2.4 GHz downlink emission with frequency and signal strength (dBm).
  - *EO/IR Optical Visual*: Visual bounding box and rotary wing classification.
- **Live Kinematic & Coordinate Validation**:
  - Latitude in `[-90.0, 90.0]`
  - Longitude in `[-180.0, 180.0]`
  - Altitude AGL `>= 0.0`
  - Heading in `[0.0, 360.0)`
  - Speed `>= 0.0`
  - Confidence in `[0.0, 1.0]`
  - Observation timestamp is valid ISO-8601 and not in the future.
- **Direct Dispatch to Ingestion Engine**: Triggers `POST /api/v1/sensors/{sensor_id}/detections` (requiring `sensors.configure`).
- **Ingestion Result Status**: Confirms `detection_id`, creation flag (`true` for new track observation vs `false` for idempotent duplicate), and timestamp.

### D. Data Contract & Schema Viewer (`/app/developer?tab=schemas`)
- **Pydantic Model Inspector**: Browse field definitions, types, constraints, and descriptions for canonical models (`RawDetection`, `TrackResponse`, `AlertResponse`, `ThreatResponse`).
- **Sample Contract Generator**: Generates formatted JSON data structures representing valid backend contracts.

### E. Multi-Format Integration Code Generator
- **PowerShell cURL**: Generates `curl.exe` commands with proper argument escaping for Windows PowerShell.
- **POSIX cURL**: Generates standard bash-compatible single-quoted `curl` commands.
- **JavaScript `fetch()` Snippet**: Generates clean, ready-to-run asynchronous `fetch()` code.

---

## 3. Route & Navigation Matrix

| Path | Component | Required Permission | Description |
|---|---|---|---|
| `/app/developer` | `ApiConsolePage` | `system.read` | Main Developer & API Console |
| `/app/developer?tab=catalog` | `ApiCatalog` | `system.read` | Searchable API route catalog |
| `/app/developer?tab=dispatcher` | `RequestDispatcher` | `system.read` | Interactive API request tester |
| `/app/developer?tab=workbench` | `DetectionWorkbench` | `sensors.configure` | Synthetic detection injector |
| `/app/developer?tab=schemas` | `SchemaViewer` | `system.read` | Data contracts & schemas |

---

## 4. Command Palette Integration

| Shortcut | Command | Destination |
|---|---|---|
| `g e` | Go to Developer & API Console | `/app/developer` |
| — | Open Interactive API Request Dispatcher | `/app/developer?tab=dispatcher` |
| — | Open Synthetic Sensor Ingestion Workbench | `/app/developer?tab=workbench` |
| — | Open Data Contract & Pydantic Schema Viewer | `/app/developer?tab=schemas` |

---

## 5. Security & Architectural Invariants

1. **HttpOnly Cookie Authentication**: Dispatched requests execute via `credentials: 'include'`. No tokens or passwords are ever extracted, rendered, or stored in `localStorage`, `sessionStorage`, or `indexedDB`.
2. **Defensive Non-Offensive Scope**: AeroGuard is strictly an analysis, simulation, and situational-awareness platform. No offensive or weaponization capabilities are present.
3. **Backend Authority**: Security decisions, validation errors, and RBAC 403 Forbidden responses are determined and enforced exclusively by the backend.
4. **Zero Client Persistence**: Request payloads and telemetry responses remain strictly ephemeral in component memory.
5. **No Direct Database Terminal**: Access occurs exclusively through defined, versioned REST endpoints.
