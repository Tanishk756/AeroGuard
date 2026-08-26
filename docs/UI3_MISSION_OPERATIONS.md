# Stage UI3 — Mission Operations & Interaction

Stage UI3 delivers the comprehensive mission-operations, investigation, simulation control, historical replay, and keyboard workflow for the AeroGuard Operator Console.

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│ MISSION HEADER (AeroGuard Branding, UTC Clock, Health, Role, Command Hub)   │
├─────────────────────────────────────────────────────────────────────────────┤
│ WORKSPACE FILTER & COMMAND TOOLBAR (Filters, Reset, Search, Quick Palette)  │
├────────────────────────────────────────┬────────────────────────────────────┤
│                                        │                                    │
│   TACTICAL MAP / REPLAY VIEWPORT       │    CONTEXTUAL INSPECTOR HUB        │
│   (Pure SVG Tactical Display:          │    (Context-sensitive inspector:   │
│    Grid, Range Rings, Tracks, Sensors, │     • Track Kinematics & Triage    │
│    Geofences, Heading Vectors, Trails) │     • Alert Details & Root Cause   │
│                                        │     • Threat Operational Priority  │
│                                        │     • Sensor Metadata & Status     │
│                                        │     • Geofence Bounds & Breaches)  │
├────────────────────────────────────────┴────────────────────────────────────┤
│ OPERATIONAL REGISTRY TABS                                                   │
│ [ Tracks (N) | Alerts (N) | Threat Triage (N) | Sensors (N) | Geofences (N) │
│   Timeline (N) | Scenario Execution (F5) | Replay & Compare (F6) ]          │
├─────────────────────────────────────────────────────────────────────────────┤
│ STATUS FOOTER (Data Freshness UTC, Refresh Triggers, Scope Boundaries)      │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 1. Architectural Principles & Boundaries

- **Pure Presentation & Interaction Layer**: The frontend displays backend operational truth (F1–F6) without recalculating threat scores, inventing track associations, modifying historical state, or fabricating telemetry.
- **Backend-Authoritative Simulation & Replay**: F5 Scenario simulation clock and F6 historical replay state reconstruction are executed strictly on the backend. The UI controls discrete step advancement and visualizes reconstructed states.
- **Contextual Multi-Entity Inspector Hub**: Dynamic inspection supporting all operational entities: Tracks, Alerts, Threat Assessments, Sensors, and Geofences.
- **Command Palette & Keyboard Acceleration**: Fast global keyboard workflow (`Ctrl+K`, `Cmd+K`, `/`) for instant navigation, map fitting, and selection actions.
- **Strict Security & RBAC Boundary**: Pure HttpOnly cookie session (`credentials: 'include'`), zero token persistence in `localStorage`/`sessionStorage`, and permission-aware view rendering.
- **Counter-UAS Defensive Scope Boundary**: Prominently clarifies that Threat Triage scores indicate situational monitoring urgency and *not* hostile intent probability. No weapon, jamming, or offensive functionality.

---

## 2. Component Hierarchy & Module Design

```text
apps/operator/src/
  ├── types/
  │   ├── scenario.ts                  # Scenario, ScenarioConfiguration, ScenarioExecutionStatus
  │   ├── geofence.ts                  # Geofence & GeofenceGeometry interfaces
  │   ├── workspace.ts                 # WorkspaceFilterState, SelectedEntity, MapLayerVisibility
  │   └── index.ts                     # Aggregated type exports
  │
  ├── api/
  │   ├── scenarios.ts                 # REST client for F5 scenario execution, stepping & status
  │   ├── replay.ts                    # REST client for F6 replay query, step & run comparison
  │   ├── geofences.ts                 # REST client for geofences
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
  │   ├── command/
  │   │   └── CommandPalette.tsx       # Global keyboard command palette modal (Ctrl+K)
  │   │
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
  │   │   ├── WorkspaceInspector.tsx   # Multi-entity inspector dispatcher (Track / Sensor / Geofence / Alert / Threat)
  │   │   ├── TrackInspector.tsx       # Kinematics, quality, threat score, geofences, related alerts, trajectory points
  │   │   ├── AlertInspector.tsx       # Alert details, severity, rule reason, metadata JSON, track/sensor links
  │   │   ├── ThreatInspector.tsx      # Operational priority score, factor breakdown, track link, defensive disclaimers
  │   │   ├── SensorInspector.tsx      # Sensor metadata, modality, status, configuration details
  │   │   └── GeofenceInspector.tsx    # Geofence geometry, altitude limits, associated tracks & breaches
  │   │
  │   ├── workspace/
  │   │   ├── OperationalWorkspace.tsx # Master synchronized operational workspace layout & deep-linking
  │   │   ├── ScenarioPanel.tsx        # F5 simulation execution, virtual clock monitor & discrete stepping
  │   │   ├── WorkspaceFilterBar.tsx   # Filter bar for state, classification, severity, modality
  │   │   ├── TrackPanel.tsx           # Synchronized track registry table
  │   │   ├── AlertPanel.tsx           # Synchronized alert feed with track selection link
  │   │   ├── ThreatPanel.tsx          # Synchronized threat triage with track selection link
  │   │   ├── SensorPanel.tsx          # Synchronized sensor inventory table
  │   │   ├── GeofencePanel.tsx        # Synchronized geofence registry table
  │   │   └── TimelinePanel.tsx        # Synchronized timeline with event type and time presets
  │   │
  │   └── layout/
  │       ├── AppHeader.tsx            # Header with Command Hub trigger (Ctrl+K), UTC clock, health
  │       └── AppSidebar.tsx           # Navigation sidebar including Scenarios hub
  │
  ├── pages/
  │   ├── OverviewPage.tsx             # Hosts OperationalWorkspace with deep linking
  │   ├── ScenariosPage.tsx            # Dedicated F5 simulation management and execution page
  │   ├── ReplayPage.tsx               # F6 replay analysis with embedded TacticalMap visualization
  │   └── TracksPage.tsx               # Dedicated track management page
  │
  └── test/
      ├── operator.test.ts             # UI1 foundation unit tests
      ├── workspace.test.ts            # UI2 viewport, projection, selection, filtering, and stale state tests
      └── operations.test.ts           # UI3 command palette, multi-entity inspectors, scenario lifecycle tests
```

---

## 3. Keyboard Shortcuts & Command Registry

| Shortcut | Command | Action |
|---|---|---|
| `Ctrl + K` / `Cmd + K` | **Open Command Hub** | Displays the global command palette modal |
| `/` | **Quick Command Search** | Opens command palette (when not typing in an input) |
| `Escape` | **Clear / Close** | Closes palette or deselects active entity |
| `g o` | **Go to Overview** | Navigates to `/app/overview` |
| `g t` | **Go to Tracks** | Navigates to `/app/tracks` |
| `g s` | **Go to Sensors** | Navigates to `/app/sensors` |
| `g a` | **Go to Alerts** | Navigates to `/app/alerts` |
| `g h` | **Go to Threats** | Navigates to `/app/threats` |
| `g c` | **Go to Scenarios** | Navigates to `/app/scenarios` |
| `g r` | **Go to Replay** | Navigates to `/app/replay` |
| `g l` | **Go to History** | Navigates to `/app/history` |
| `g y` | **Go to Analytics** | Navigates to `/app/analytics` |
| `f` | **Fit Map to Entities** | Re-centers and zooms viewport to fit all active objects |
| `c` | **Center Map View** | Centers viewport coordinate readout |
| `r` | **Refresh Telemetry** | Triggers asynchronous operational data refresh |
| `i` | **Toggle Inspector** | Expands or collapses the contextual inspector panel |
