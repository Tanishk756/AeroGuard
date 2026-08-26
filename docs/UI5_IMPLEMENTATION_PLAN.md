# Stage UI5 Implementation Plan — Mission Authoring & Defense Zone Studio

## 1. Problem Statement
The AeroGuard platform backend provides comprehensive REST APIs for defining defensive geofence boundaries (Stage F4/F5: 2D bounding boxes, polygon vertex perimeters, altitude ceilings, and breach detection rules) and authoring multi-target deterministic simulation scenarios (Stage F5: synthetic trajectories, waypoint navigation, sensor modality attachments, and seeds). 

However, the operator console currently lacks any visual authoring, editing, or configuration tools for geofences and scenarios. Operators and mission planners can only view existing geofences and execute pre-existing scenarios. Creating new defense perimeters, modifying restricted zones, or constructing synthetic test scenarios currently requires raw API requests or direct database manipulation.

---

## 2. Current Repository Evidence
- **Backend Geofence Endpoints**: `POST /api/v1/geofences`, `GET /api/v1/geofences/{id}`, `PUT /api/v1/geofences/{id}`, `DELETE /api/v1/geofences/{id}` are fully implemented in `backend/app/api/v1/routes/geofences.py` with SQLAlchemy models, Alembic migrations, and 100% passing tests (`test_geofences_crud_api`).
- **Backend Scenario Endpoints**: `POST /api/v1/scenarios`, `GET /api/v1/scenarios/{id}`, `PUT /api/v1/scenarios/{id}`, `DELETE /api/v1/scenarios/{id}` are fully implemented in `backend/app/api/v1/routes/scenarios.py` with Pydantic schemas (`ScenarioCreateRequest`, `ScenarioUpdateRequest`, `ScenarioConfiguration`, `ScenarioTargetDefinition`, `ScenarioSensorDefinition`, `ScenarioWaypoint`) and comprehensive lifecycle tests (`test_scenarios_api_crud_and_execution_lifecycle`).
- **Frontend Current State**:
  - Geofences: Rendered on `TacticalMap` (UI2) and inspected in `GeofenceInspector` (UI3), but no creation/editing UI exists.
  - Scenarios: Managed during execution via `ScenarioPanel` and `ScenariosPage` (UI3), but creation/editing relies entirely on pre-seeded records.

---

## 3. User / Operator Value
- **Defensive Airspace & Perimeter Definition**: Operators and security administrators can visually define restricted flight zones, critical asset bounding boxes, and multi-vertex polygon boundaries with precise minimum and maximum altitude constraints.
- **Simplified Polygon Drafting**: Mission planners can construct polygon boundaries using an intuitive vertex list editor, direct coordinate input, and real-time SVG boundary overlay preview on the TacticalMap without complex external GIS dependencies.
- **Comprehensive Scenario Authoring**: Test engineers and simulation researchers can construct deterministic simulation scenarios, configuring synthetic drone trajectories (constant-velocity bearings or multi-waypoint flight paths), sensor modality payloads (Radar, Optical, RF), range/FOV limits, noise parameters, and geofence breach conditions.
- **Template Cloning & Rapid Reconfiguration**: Planners can duplicate existing scenarios into editable drafts and adjust parameters (seed, duration, tick rate) for regression testing and training drills.
- **Destructive-Action Safety & Unsaved-Draft Protection**: Prevents accidental loss of complex configuration drafts through dirty-state detection, and protects operational stability through two-step confirmation on zone/scenario deletion and deletion-blocking of active/running scenarios.

---

## 4. Exact Scope

### A. Geofence Zone Studio Subsystem
1. **`GeofencesPage` Directory**:
   - Filterable table of all active and inactive defense perimeters.
   - Status indicators (ENABLED / DISABLED), geometry type badge (BBOX / POLYGON), and altitude bounds readout.
   - Zone summary metrics: Total Zones, Active Inclusions, Active Exclusions.
   - Action triggers: "+ New Defense Zone", "Edit Perimeter", "Toggle Enabled", "Delete Zone".
2. **`GeofenceEditor` Modal / Drawer**:
   - **Geometry Mode Selection**:
     - *2D Bounding Box*: Explicit inputs for `min_lat`, `min_lon`, `max_lat`, `max_lon`.
     - *Multi-Vertex Polygon*: Ordered coordinate list editor with "+ Add Vertex", delete vertex, reorder, and paste coordinate array (`[[lat, lon], ...]`).
   - **Coordinate Validation**: Validates latitude `[-90, 90]`, longitude `[-180, 180]`, bounding box sanity (`min < max`), and minimum 3 vertices for polygons.
   - **Altitude Constraints**: Optional minimum and maximum altitude limits (in meters, `>= 0`, `min <= max`).
   - **Zone Rules & Metadata**: Name (1-200 chars), description, enabled toggle, rule classification (`INCLUSION` vs `EXCLUSION`).
   - **Live SVG Map Preview**: Synchronizes draft geometry directly to the `TacticalMap` overlay for immediate visual confirmation.
3. **Destructive Deletion Workflow**:
   - Two-step confirmation modal requiring explicit confirmation before executing `DELETE /api/v1/geofences/{id}`.

### B. Scenario Authoring & Simulation Builder Subsystem
1. **`ScenarioEditorModal` / Builder Studio**:
   - **Section 1: General Parameters**:
     - Name (1-200 chars), description (0-1000 chars).
     - Duration (1 to 86,400 seconds), tick rate (0.1 to 100.0 Hz).
     - Random seed (integer `0` to `2^31 - 1`).
     - Simulation start timestamp (ISO-8601 UTC).
   - **Section 2: Synthetic Target Kinematics & Waypoint Trajectories**:
     - Add/remove multiple synthetic target drones (unique `target_id`).
     - Classification selection (`DRONE_ROTARY`, `DRONE_FIXED_WING`, etc.).
     - Initial position (`latitude`, `longitude`, `altitude`) and kinematics (`velocity` m/s, `heading` deg).
     - Trajectory Mode:
       - *Constant-Velocity*: Fixed speed and heading vector.
       - *Waypoint Navigation*: Ordered sequence of waypoints (`latitude`, `longitude`, `altitude`, `speed`) with arrival tolerance.
   - **Section 3: Synthetic Sensor Modality Attachments**:
     - Add/remove synthetic sensor assets (unique `sensor_id`).
     - Modality type (`RADAR`, `OPTICAL`, `RF`).
     - Origin position (`latitude`, `longitude`, `altitude`).
     - Coverage bounds: `range_meters` (`>= 0`), detection probability (`0.0` to `1.0`).
     - Field-of-View gating: `fov_azimuth_start_deg` (`0` to `< 360`), `fov_azimuth_span_deg` (`0` to `360`).
     - Measurement noise parameters: position uncertainty (meters), altitude uncertainty, velocity uncertainty.
   - **Section 4: Geofence Zone Association**:
     - Multi-select registered geofences to attach (`geofence_ids: list[str]`) for automated boundary breach evaluation.
2. **Template Cloner**:
   - "Clone Scenario" action that duplicates an existing scenario configuration into a new editable draft with appended name suffix (e.g. `SCENARIO_NAME (Copy)`).
3. **Scenario Management & Destructive Safety**:
   - Edit scenario configuration (`PUT /api/v1/scenarios/{id}`).
   - Deletion safety: Two-step confirmation for `DELETE /api/v1/scenarios/{id}`.
   - Hard execution guard: Scenarios in `RUNNING` or `PAUSED` state cannot be deleted or have their configuration mutated while active.

### C. Unsaved-Draft Protection & Safety
- Dirty-state tracking (`isDirty`) on all authoring forms.
- If an operator attempts to close the authoring modal, switch tabs, or cancel with unsaved modifications, an "Unsaved Changes Warning" dialog prompts to Confirm Discard or Continue Editing.

### D. Navigation & Global Integration
- Add route `/app/geofences` (`scenarios.read`) in `AppRoutes.tsx`.
- Update `AppSidebar.tsx` with "Defense Zones" navigation item.
- Add Command Palette navigation shortcut (`g z` for Defense Zones).

---

## 5. Explicit Exclusions
- **No In-Flight Kinematic Mutation**: Active simulations (`RUNNING` or `PAUSED`) cannot have their target trajectories or sensor positions edited mid-run.
- **No External Map SDKs**: Preserves the lightweight pure SVG/CSS TacticalMap architecture.
- **No Offensive/Weapon Functions**: Zone breaches trigger defensive alerts and threat assessments only.
- **No WebSockets or SSE Streams**: Mutation feedback uses existing REST patterns.

---

## 6. Existing Backend Dependencies

| Endpoint | Method | Permission | Request Contract | Response Contract | Backend Handler |
|---|---|---|---|---|---|
| `/api/v1/geofences` | `GET` | `scenarios.read` | None | `list[GeofenceResponse]` | `geofences.py:list_geofences` |
| `/api/v1/geofences` | `POST` | `scenarios.create` | `GeofenceCreateRequest` | `GeofenceResponse` | `geofences.py:create_geofence` |
| `/api/v1/geofences/{id}` | `GET` | `scenarios.read` | Path `id: str` | `GeofenceResponse` | `geofences.py:get_geofence` |
| `/api/v1/geofences/{id}` | `PUT` | `scenarios.update` | `GeofenceUpdateRequest` | `GeofenceResponse` | `geofences.py:update_geofence` |
| `/api/v1/geofences/{id}` | `DELETE` | `scenarios.delete` | Path `id: str` | `204 No Content` | `geofences.py:delete_geofence` |
| `/api/v1/scenarios` | `GET` | `scenarios.read` | None | `list[ScenarioResponse]` | `scenarios.py:list_scenarios` |
| `/api/v1/scenarios` | `POST` | `scenarios.create` | `ScenarioCreateRequest` | `ScenarioResponse` | `scenarios.py:create_scenario` |
| `/api/v1/scenarios/{id}` | `GET` | `scenarios.read` | Path `id: str` | `ScenarioResponse` | `scenarios.py:get_scenario` |
| `/api/v1/scenarios/{id}` | `PUT` | `scenarios.update` | `ScenarioUpdateRequest` | `ScenarioResponse` | `scenarios.py:update_scenario` |
| `/api/v1/scenarios/{id}` | `DELETE` | `scenarios.delete` | Path `id: str` | `204 No Content` | `scenarios.py:delete_scenario` |

---

## 7. Frontend Architecture

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                          STAGE UI5 MISSION AUTHORING STUDIO                 │
├─────────────────────────────────────────────────────────────────────────────┤
│  GEOFENCE ZONE STUDIO             │  SCENARIO SIMULATION BUILDER            │
│  • GeofencesPage Directory        │  • ScenarioEditorModal (4-Tab Studio)   │
│  • GeofenceEditor (BBox & Poly)   │  • Target Kinematics & Waypoint List    │
│  • Live SVG Boundary Preview      │  • Sensor Modality & FOV Attachments    │
│  • Unsaved-Draft Protection       │  • Template Cloner & Execution Guard    │
│  • Two-Step Delete Confirmation   │  • Two-Step Delete Confirmation         │
└───────────────────────────────────┴─────────────────────────────────────────┘
```

---

## 8. State Ownership
- **Drafting State**: Local component state (`useGeofenceDraft`, `useScenarioDraft`) tracking field changes and `isDirty` status.
- **Map Synchronization**: The active draft geometry is shared with `TacticalMap` via an optional `draftGeometry` prop to render live dashed boundary previews.
- **Server Cache Invalidation**: Upon successful `POST`, `PUT`, or `DELETE`, active queries are invalidated and re-fetched immediately.

---

## 9. Data Fetching Strategy
- Standard centralized REST client using `request()` with `credentials: 'include'`.
- Parallel loading of prerequisite assets (geofences, existing scenarios, sensors) using `Promise.all()`.
- Explicit mutation status feedback with success/error alerts.

---

## 10. Loading / Error / Stale States
- Standard `LoadingState` spinner during entity creation and update submission.
- Standard `ErrorState` with actionable retry on API validation failures (e.g. invalid polygon winding, negative altitude, or duplicate scenario name).
- Non-blocking confirmation prompts on destructive operations (zone/scenario deletion).

---

## 11. RBAC Matrix

| Path / Action | Required Permission |
|---|---|
| View Geofences & Scenarios | `scenarios.read` |
| Create Geofence | `scenarios.create` |
| Update Geofence | `scenarios.update` |
| Delete Geofence | `scenarios.delete` |
| Create Scenario | `scenarios.create` |
| Edit Scenario Configuration | `scenarios.update` |
| Delete Scenario | `scenarios.delete` |

---

## 12. Accessibility Requirements
- All modal dialogs implement `role="dialog"`, `aria-modal="true"`, `aria-labelledby`, and `Escape` key close handlers (intercepted by unsaved changes check if dirty).
- Coordinate input fields have explicit semantic `<label>` tags and numeric step constraints.
- Form validation errors are announced via accessible error banners.
- Keyboard navigation supported across all form controls and waypoint lists.

---

## 13. Responsive Requirements
- Modal authoring drawers adapt smoothly to desktop and reduced-width layouts (min-width 320px).
- Complex forms use two-column responsive grids that collapse to single-column on narrower viewports.

---

## 14. Performance Requirements
- Pure SVG rendering of draft polygons without DOM element thrashing.
- Debounced coordinate input validation to prevent unnecessary re-computations.
- Zero client-side computation of great-circle distance (delegated to backend).

---

## 15. New Files (6 files)
1. `apps/operator/src/components/geofence/GeofenceEditor.tsx` — Modal/drawer for creating and updating 2D bounding boxes and polygon geofences.
2. `apps/operator/src/components/scenario/ScenarioEditorModal.tsx` — Multi-step authoring modal for synthetic targets, waypoints, sensors, and parameters.
3. `apps/operator/src/components/scenario/TargetConfigForm.tsx` — Dedicated form for configuring target kinematics and waypoint trajectories.
4. `apps/operator/src/components/scenario/SensorConfigForm.tsx` — Dedicated form for configuring sensor modalities, range, and FOV.
5. `apps/operator/src/pages/GeofencesPage.tsx` — Dedicated Geofence management page.
6. `apps/operator/src/test/authoring.test.ts` — Comprehensive unit test suite for geofence geometry validation, scenario schema serialization, and waypoint computation.

---

## 16. Modified Files (8 files)
1. `apps/operator/src/api/geofences.ts` — Add `createGeofence`, `updateGeofence`, `deleteGeofence`.
2. `apps/operator/src/api/scenarios.ts` — Add `createScenario`, `updateScenario`.
3. `apps/operator/src/types/geofence.ts` — Add `GeofenceCreate`, `GeofenceUpdate` types.
4. `apps/operator/src/types/scenario.ts` — Add `ScenarioCreate`, `ScenarioUpdate`, `SyntheticTargetCreate`, `SyntheticSensorCreate`, `WaypointCreate` types.
5. `apps/operator/src/components/inspector/GeofenceInspector.tsx` — Add Edit and Delete action controls.
6. `apps/operator/src/components/scenario/ScenarioPanel.tsx` — Add "+ New Scenario" and "Edit Configuration" actions.
7. `apps/operator/src/pages/ScenariosPage.tsx` — Integrate scenario creation and clone triggers.
8. `apps/operator/src/routes/AppRoutes.tsx` & `AppSidebar.tsx` & `CommandPalette.tsx` — Register `/app/geofences` route and navigation shortcuts.

---

## 17. API Changes
**No backend changes required.** All 10 required REST endpoints and data contracts already exist and are 100% tested in `backend/app/api/v1/routes/geofences.py` and `backend/app/api/v1/routes/scenarios.py`.

---

## 18. Test Strategy

### Behavioral Unit Tests (`apps/operator/src/test/authoring.test.ts`):
1. **Geofence BBox Coordinate Validation**:
   - Validates `min_lat < max_lat` and `min_lon < max_lon`.
   - Validates latitude in `[-90, 90]` and longitude in `[-180, 180]`.
2. **Polygon Vertex List Validation**:
   - Rejects polygon definitions with `< 3` vertex coordinate pairs.
   - Validates coordinate numbers and array formatting `[[lat, lon], ...]`.
3. **Altitude Range Validation**:
   - Validates `min_altitude >= 0` and `max_altitude >= min_altitude`.
4. **Scenario Configuration Serialization**:
   - Validates `duration_seconds > 0` and `tick_rate_hz > 0`.
   - Serializes synthetic targets with constant-velocity vectors vs ordered waypoints.
   - Serializes synthetic sensor definitions with FOV spans and detection probabilities.
   - Validates uniqueness of target IDs and sensor IDs in configuration payload.
5. **Unsaved-Draft Dirty State Detection**:
   - Detects modifications from initial state and triggers confirmation warning on close.
6. **Destructive Action & Execution Safety**:
   - Validates two-step delete confirmation guard.
   - Enforces block on deleting or modifying scenarios in `RUNNING` or `PAUSED` status.
7. **RBAC Permission Gating**:
   - Asserts action availability based on `scenarios.create`, `scenarios.update`, and `scenarios.delete`.

---

## 19. Security Verification
- Verify zero token storage:
  `git grep -n -i -E "jwt|bearer|localStorage|sessionStorage|indexedDB" -- apps/operator` -> 0 matches.
- Verify zero offensive terminology:
  `git grep -n -i -E "weapon|jamming|countermeasure|intercept|pytorch" -- apps/operator` -> 0 matches.

---

## 20. Documentation Changes
- Create `docs/UI5_MISSION_AUTHORING.md`.
- Update `docs/ARCHITECTURE.md`, `docs/PHASE1_IMPLEMENTATION.md`, and `docs/ROADMAP.md`.

---

## 21. Acceptance Criteria
1. Users with `scenarios.create` can create new 2D bounding box and polygon geofences with altitude bounds.
2. Users with `scenarios.update` and `scenarios.delete` can edit and delete existing geofences with two-step confirmation.
3. Users with `scenarios.create` can create new deterministic simulation scenarios with synthetic targets, waypoint trajectories, and synthetic sensors.
4. Users with `scenarios.update` and `scenarios.delete` can edit scenario parameters, clone templates, and delete custom scenarios.
5. Unsaved modifications trigger a warning prompt before discard or dialog dismissal.
6. Scenarios in `RUNNING` or `PAUSED` state cannot be deleted or re-configured.
7. All authoring operations enforce backend RBAC permissions and provide immediate visual confirmation.
8. All automated unit tests, typechecks, production builds, and backend pytest suites pass with 0 errors.

---

## 22. Definition of Done
- 6 new files created and 8 modified files.
- `npm test` passes with >= 68 unit tests.
- `npm --prefix apps/operator run typecheck` passes with 0 errors.
- `npm --prefix apps/operator run build` builds cleanly.
- `pytest -v` passes 145/145 backend tests.
- Zero token storage and zero offensive terms.
