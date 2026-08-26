# Stage UI2 — Operational Map & Mission Workspace

Stage UI2 delivers the synchronized, interactive operational visualization and mission workspace for the AeroGuard Operator Console.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ MISSION HEADER (AeroGuard Branding, Telemetry KPIs, Refresh / Stale State) │
├─────────────────────────────────────────────────────────────────────────────┤
│ WORKSPACE FILTER TOOLBAR (State, Classification, Severity, Threat, Search)  │
├────────────────────────────────────────┬────────────────────────────────────┤
│                                        │                                    │
│   TACTICAL MAP WORKSPACE               │    WORKSPACE INSPECTOR             │
│   (Pure SVG Interactive Viewport:      │    (Context-sensitive telemetry,   │
│    Grid, Range Rings, Tracks, Vectors, │     Kinematics, Threat Factors,    │
│    Sensors, Geofences, Trajectories)   │     Breached Geofences, Alerts)    │
│                                        │                                    │
├────────────────────────────────────────┴────────────────────────────────────┤
│ OPERATIONAL REGISTRY TABS (Tracks | Alerts | Threats | Sensors | Geofences) │
├─────────────────────────────────────────────────────────────────────────────┤
│ STATUS / SYSTEM FOOTER (Connectivity, DB Health, Scope Boundary)            │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Architectural Principles & Boundaries

- **Pure Presentation & Interaction Layer**: The frontend displays backend operational truth (F1–F6) without recalculating threat scores, inventing track associations, modifying historical state, or fabricating telemetry.
- **Pure SVG / CSS Tactical Map**: Zero third-party mapping SDK dependencies (no Mapbox, Google Maps, Leaflet, or OpenLayers). Features custom deterministic coordinate projection, pan, zoom, fit-to-data, coordinate readout, and layer rendering.
- **REST-Backed Staging & Restrained Refresh**: Zero WebSockets/SSE. Uses bounded REST queries with `AbortController` cancellation, stale-while-refresh caching, visible "Last Updated" UTC timestamp, and manual refresh controls.
- **Multi-Entity Selection Synchronization**: Map marker click $\leftrightarrow$ Registry row click $\leftrightarrow$ Detail inspector $\leftrightarrow$ Timeline entry.
- **Separation of Selection and Data Fetching**: Selecting a track updates the selection state; a dedicated hook (`useTrackHistory`) independently reacts to the selected track and retrieves its trajectory history.
- **Sensor Range / Coverage Boundary**: Sensor coverage circles are rendered only when the backend provides valid positive `range_meters` metadata in `configuration_metadata`.
- **Strict Security & RBAC**: Pure HttpOnly cookie session (`credentials: 'include'`), zero token persistence in `localStorage`/`sessionStorage`, and permission-aware view rendering.

---

## 2. Component Hierarchy & Module Design

```text
apps/operator/src/
  ├── types/
  │   ├── geofence.ts                  # Geofence & GeofenceGeometry interfaces
  │   ├── workspace.ts                 # WorkspaceFilterState, SelectedEntity, MapLayerVisibility
  │   └── index.ts                     # Aggregated type exports
  │
  ├── api/
  │   ├── geofences.ts                 # API client for GET /api/v1/geofences, /geofences/{id}
  │   ├── sensors.ts                   # Normalized sensor list/array response handling
  │   └── index.ts                     # Aggregated API client exports
  │
  ├── hooks/
  │   ├── useMapViewport.ts            # Viewport math: pan, zoom, fit-to-bounds, lat/lon <-> screen projection
  │   ├── useOperationalData.ts        # Centralized REST state fetcher with cancellation & stale-while-refresh
  │   ├── useWorkspaceSelection.ts     # Selection state management (track, sensor, geofence, alert, threat)
  │   └── useTrackHistory.ts           # Trajectory history fetcher reacting to selected track ID
  │
  ├── components/
  │   ├── map/
  │   │   ├── TacticalMap.tsx          # Interactive SVG tactical map surface with pan, zoom, grid, rings
  │   │   ├── MapControls.tsx          # Zoom (+/-), fit-all, center reset, layer toggles bar
  │   │   ├── TrackLayer.tsx           # Track markers, heading vectors, labels, selected highlight reticle
  │   │   ├── TrajectoryLayer.tsx      # Historical track trajectory polyline & sequence breadcrumbs
  │   │   ├── SensorLayer.tsx          # Sensor icons, valid range coverage circles
  │   │   ├── GeofenceLayer.tsx        # Bounding boxes, polygon boundaries, breach/containment highlights
  │   │   └── CoordinateReadout.tsx    # Cursor & viewport center lat/lon coordinate badge
  │   │
  │   ├── inspector/
  │   │   ├── WorkspaceInspector.tsx   # Multi-entity inspector panel (Track / Sensor / Geofence)
  │   │   ├── TrackInspector.tsx       # Identity, quality, kinematics, timing, threat factor breakdown, related alerts
  │   │   ├── SensorInspector.tsx      # Sensor metadata, modality, status, configuration details
  │   │   └── GeofenceInspector.tsx    # Geofence geometry, altitude limits, associated tracks & breaches
  │   │
  │   ├── workspace/
  │   │   ├── OperationalWorkspace.tsx # Master synchronized operational workspace layout
  │   │   ├── WorkspaceFilterBar.tsx   # Filter bar for state, classification, severity, modality
  │   │   ├── TrackPanel.tsx           # Synchronized track registry table
  │   │   ├── SensorPanel.tsx          # Synchronized sensor inventory table
  │   │   ├── GeofencePanel.tsx        # Synchronized geofence registry table
  │   │   ├── AlertPanel.tsx           # Synchronized alert feed with track selection link
  │   │   ├── ThreatPanel.tsx          # Synchronized threat triage with track selection link
  │   │   └── TimelinePanel.tsx        # Synchronized timeline with track selection link
  │   │
  │   └── common/                      # StatusBadge, Button, Card, LoadingState, ErrorState, EmptyState
  │
  ├── pages/
  │   ├── OverviewPage.tsx             # Hosts OperationalWorkspace
  │   └── TracksPage.tsx               # Dedicated track management page
  │
  └── test/
      ├── operator.test.ts             # UI1 foundation unit tests
      └── workspace.test.ts            # UI2 viewport, projection, selection, filtering, and stale state tests
```

---

## 3. Map Projection & Interactive Features

- **Equirectangular Projection with Cosine Latitude Scaling**:
  $$\begin{aligned}
    x &= \frac{\text{width}}{2} + (\text{lon} - \text{centerLon}) \cdot \text{scale} \cdot \cos\left(\frac{\text{centerLat} \cdot \pi}{180}\right) + \text{panOffset.x} \\
    y &= \frac{\text{height}}{2} - (\text{lat} - \text{centerLat}) \cdot \text{scale} + \text{panOffset.y}
  \end{aligned}$$
- **Interactive Controls**:
  - Drag mouse or touch surface to pan.
  - Scroll wheel or `+`/`-` buttons to zoom ($0.05\times$ to $50\times$).
  - **Fit All**: Calculates geographic bounding box across all active tracks, registered sensors, and geofence vertices, adjusting center and zoom automatically.
  - **Layer Toggles**: Independently toggle Tracks, Sensors, Geofences, Trajectories, Range Rings, Coordinate Grid, and Labels.
- **Adaptive Overlays**:
  - Lat/Lon grid lines with coordinate annotations.
  - Range rings centered at viewport center ($500\,\text{m}$, $1000\,\text{m}$, $2000\,\text{m}$, $5000\,\text{m}$).
  - Live cursor and viewport center WGS84 readout.

---

## 4. Selection Synchronization Matrix

| Action | Map Effect | Registry Effect | Inspector Effect |
|---|---|---|---|
| **Click Track Marker** | Target reticle locks on track, trajectory polyline displayed | Selected track highlighted in Tracks table | `TrackInspector` shows full kinematics, threat triage, and alert links |
| **Click Sensor Marker** | Reticle highlights sensor, range circle highlighted | Selected sensor highlighted in Sensors table | `SensorInspector` shows modality, status, coordinates, and config metadata |
| **Click Geofence Boundary** | Boundary highlighted in cyan/amber | Selected geofence highlighted in Geofences table | `GeofenceInspector` shows bounds, altitude limits, and contained tracks |
| **Click Alert in Feed** | Associated track (if present) selected on map | Alert row highlighted | If track present, opens `TrackInspector` with alert highlighted |
| **Click Threat in Triage** | Associated track selected on map | Threat row highlighted | Opens `TrackInspector` with detailed threat scoring factor breakdown |
| **Click Timeline Event** | Associated entity selected on map | Timeline row highlighted | Opens corresponding inspector for associated track, sensor, or geofence |

---

## 5. Verification & Testing

- **Frontend Unit Tests**: 30 unit tests across 12 test suites passing in 160ms (`npm test`).
  - Viewport projection math, inverse coordinate mapping, zoom clamping, and `fitBounds` calculation.
  - Selection synchronization and entity resolution.
  - Client-side filtering logic across tracks, alerts, threats, and sensors.
  - Sensor range circle rendering boundary (only rendered when `range_meters` is valid positive float).
  - Geofence bbox and polygon validation.
  - Stale-while-refresh data caching.
- **TypeScript Typecheck**: Passed with 0 errors (`npm --prefix apps/operator run typecheck`).
- **Production Build**: Vite production bundle compiled in 1.81s (`npm --prefix apps/operator run build`).
- **Backend Regression Suite**: 145 / 145 pytest tests passed in 14.78s across Stages F1–F6.
