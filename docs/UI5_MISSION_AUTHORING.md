# Stage UI5 — Mission Authoring & Defense Zone Studio

## Overview
Stage UI5 delivers the Mission Authoring & Defense Zone Studio for the AeroGuard operator console. It introduces comprehensive visual management for defensive geofence perimeters (Stage F4/F5 backend engine) and deterministic simulation scenario authoring (Stage F5 backend engine), providing full CRUD workflows, live SVG TacticalMap boundary preview, template cloning, unsaved draft protection, and two-step deletion safety.

---

## Key Capabilities

### 1. Geofence Zone Studio (`/app/geofences`)
- **Defense Zone Directory**: View and manage all registered 2D/3D defensive perimeters with status indicators (ENABLED/DISABLED), rule classification (INCLUSION/EXCLUSION), and altitude limits.
- **2D Bounding Box Authoring**: Precise input fields for `min_lat`, `min_lon`, `max_lat`, `max_lon` with mathematical sanity checks (`min < max`, standard GPS coordinate ranges).
- **Multi-Vertex Polygon Authoring**: Ordered vertex coordinate list with add, remove, and reorder controls, plus raw coordinate array paste support (`[[lat, lon], ...]`).
- **Vertical Airspace Boundaries**: Optional ground floor (`min_altitude`) and ceiling (`max_altitude`) constraints in meters AGL.
- **Live SVG Map Boundary Preview**: Real-time synchronization of draft bounding boxes and polygons to the `TacticalMap` via dashed cyan overlay.
- **Two-Step Destructive Deletion Safety**: Requires explicit user confirmation in a dedicated safety dialog before executing `DELETE /api/v1/geofences/{id}`.

### 2. Scenario Simulation Builder Studio (`/app/scenarios`)
- **4-Section Multi-Tab Studio**:
  1. *General & Clock*: Scenario Name, Description, Duration (1–86,400s), Tick Rate (0.1–100.0 Hz), Random Seed, and UTC Simulation Start Time.
  2. *Synthetic Targets & Kinematics*: Multi-target drone authoring with initial GPS position, altitude, speed, heading, classification, and constant-velocity vs sequential waypoint trajectories.
  3. *Synthetic Sensors & Modalities*: Attach Radar, Optical, and RF synthetic sensors with coverage range, detection probability, position noise, and FOV azimuth start/span degrees.
  4. *Defense Zone Linkages*: Associate registered geofence boundaries for automated perimeter breach alert testing.
- **Template Cloner**: Clone existing scenario configurations into editable drafts with appended copy suffixes for rapid testing.
- **Execution Safeguard**: Hard client-side and server-side blocks preventing structural configuration edits or deletion on simulations in `RUNNING` or `PAUSED` state.
- **Two-Step Destructive Deletion Safety**: Requires explicit confirmation in a dedicated safety dialog before executing `DELETE /api/v1/scenarios/{id}`.

### 3. Unsaved-Draft Protection & Safety
- Form-level dirty-state tracking (`isDirty`).
- Warning modal intercepts dialog close, tab switches, and cancellations when unsaved changes exist.

### 4. Command Palette & Navigation Integration
- Route `/app/geofences` registered with `scenarios.read` permission.
- "Defense Zones" navigation item in `AppSidebar`.
- Global Command Palette shortcut: `g z` (Go to Defense Zones Studio).

---

## Architecture & Data Contracts

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STAGE UI5 MISSION AUTHORING STUDIO                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  GEOFENCE ZONE STUDIO             │  SCENARIO CONFIGURATION BUILDER         │
│  • GeofencesPage Directory        │  • ScenarioEditorModal (4-Tab Studio)   │
│  • GeofenceEditor (BBox & Poly)   │  • Target Kinematics & Waypoint List    │
│  • Live SVG Boundary Preview      │  • Sensor Modality & FOV Attachments    │
│  • Unsaved-Draft Protection       │  • Template Cloner & Execution Guard    │
│  • Two-Step Delete Confirmation   │  • Two-Step Delete Confirmation         │
└───────────────────────────────────┴─────────────────────────────────────────┘
```

### Backend Endpoints Consumed:
- `GET /api/v1/geofences`, `POST /api/v1/geofences`, `GET /api/v1/geofences/{id}`, `PUT /api/v1/geofences/{id}`, `DELETE /api/v1/geofences/{id}`
- `GET /api/v1/scenarios`, `POST /api/v1/scenarios`, `GET /api/v1/scenarios/{id}`, `PUT /api/v1/scenarios/{id}`, `DELETE /api/v1/scenarios/{id}`

---

## Automated Test Coverage

Suite: `apps/operator/src/test/authoring.test.ts` (69 passing frontend tests across repository):
1. Geofence 2D bounding box coordinate validity and inverted bounds rejection.
2. Geofence polygon vertex coordinate validation and minimum 3-point requirement.
3. Geofence altitude floor/ceiling bounds validation.
4. Scenario configuration payload serialization conforming to backend schema.
5. Unique synthetic target ID and sensor ID enforcement.
6. Dirty-state change detection and discard protection.
7. Execution safety guard blocking deletion of active/running scenarios.
8. Two-step destructive deletion confirmation.
9. RBAC permission gating (`scenarios.create`, `scenarios.update`, `scenarios.delete`, `scenarios.run`).
