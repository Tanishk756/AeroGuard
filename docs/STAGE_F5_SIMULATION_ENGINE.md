# Stage F5 Scenario Management and Deterministic Simulation Engine

Stage F5 activates the persistent `Scenario` data model and integrates a deterministic in-process simulation engine that generates synthetic sensor observations to drive the entire AeroGuard telemetry pipeline:

```text
Scenario Configuration (Targets, Waypoints, Sensors, Seed)
        ↓
Virtual Simulation Clock (Discrete Δt Steps)
        ↓
Trajectory Engine (WGS84 Great-Circle Kinematics & Waypoint Navigation)
        ↓
Synthetic Sensor Models (Radar, Optical, RF - Range/FOV Gating & Gaussian Noise)
        ↓
Deterministic RawObservation Stream
        ↓
F2 Detection Ingestion Service
        ↓
F3 Detection Association & Track Management
        ↓
F4 Multi-Sensor Fusion, Track Quality, Geofencing, Threat Prioritization, Alerts
```

---

## 1. Architectural Principles and Safety Boundaries

- **Observational Simulation Only**: AeroGuard simulation models synthetic sensor emissions and target trajectories for defensive research, situational awareness, and system testing. It does not implement weapon guidance, engagement systems, jamming, autonomous kinetic control, or destructive actions.
- **Zero External Infrastructure**: The engine executes in-process using standard Python mathematics and seed-isolated pseudo-random number generators (`random.Random(seed)`). It introduces no external brokers (Redis, Kafka, RabbitMQ, Celery), background threads, or asynchronous task schedulers.
- **No Wall-Clock Dependency**: Simulation advances strictly in discrete time steps ($\Delta t = 1.0 / \text{tick\_rate\_hz}$) triggered by explicit user requests (`POST /api/v1/scenarios/{id}/step` or `service.step()`).
- **Bit-for-Bit Determinism**: Running an identical scenario configuration with the same seed across clean databases produces identical detection timestamps, coordinates, velocities, confidence levels, track states, threat scores, and alert notifications.

---

## 2. Virtual Simulation Clock

Located in `backend/app/simulation/clock.py`:
- Manages discrete virtual time progression from an explicit UTC `start_time`.
- Advances by $N$ ticks without invoking `time.sleep` or wall-clock timers.
- Tracks `tick_count`, `current_time`, `dt_seconds`, `is_paused`, and `is_stopped`.
- Supports deterministic `step()`, `pause()`, `resume()`, `stop()`, and `reset()`.

---

## 3. Geographic Trajectory Engine

Located in `backend/app/simulation/trajectories.py`:
- **WGS84 Great-Circle Motion**: Calculates spatial displacement using standard Earth-radius ($R = 6,371,000\,\text{m}$) great-circle forward destination formulas rather than Cartesian approximations.
- **Forward Bearing Calculation**: Determines instantaneous bearing in $[0^\circ, 360^\circ)$ between consecutive coordinates.
- **Constant Velocity Mode**: Advances target position along constant heading and speed.
- **Waypoint Navigation Mode**: Steers targets toward sequential waypoints `(lat, lon, alt, speed)`, detects waypoint arrival within adaptive thresholds ($\max(v \cdot \Delta t, 15\,\text{m})$), snaps to waypoints, and advances altitude and heading deterministically.

---

## 4. Synthetic Sensor Models & Noise

Located in `backend/app/simulation/sensors.py`:
- **Modalities Supported**: Radar, Optical, RF, Synthetic.
- **Range Gating**: Rejects targets whose great-circle distance exceeds `range_meters`.
- **Field-of-View (FOV) Azimuth Gating**: Evaluates whether target bearing falls within `[fov_start, fov_start + span]`, handling $0^\circ / 360^\circ$ angular wrap-around.
- **Detection Probability**: Compares scenario-local PRNG draws against configured `detection_probability`.
- **Deterministic Gaussian Noise**: Applies zero-mean Gaussian perturbations to latitude, longitude, altitude, and velocity based on configured uncertainty bounds without fabricating undeclared dimensions.
- **Observation Generation**: Emits strongly validated `RawDetection` instances with deterministic IDs (`sim-{sensor_id}-{target_id}-{tick}`).

---

## 5. Scenario Execution Manager & Ingestion Integration

Located in `backend/app/simulation/service.py`:
- Manages scenario lifecycle states: `DRAFT` $\rightarrow$ `READY` $\rightarrow$ `RUNNING` $\rightarrow$ `PAUSED` $\rightarrow$ `COMPLETED` / `FAILED`.
- Auto-registers synthetic sensors into `sensors` table with `SensorSourceClass.SIMULATION`.
- Dispatches emitted `RawDetection` items into `DetectionIngestionService.ingest()`, ensuring full schema normalization and persistence.
- Immediately invokes `TrackingService.process_detection()`, driving association gating, multi-sensor kinematic fusion, track quality scoring, geofence penetration checks, operational threat priority evaluation, and operational alert candidate processing.

---

## 6. REST APIs and RBAC Permissions

### Scenario Endpoints (`/api/v1/scenarios`)
- `GET /api/v1/scenarios`: List scenarios with cursor pagination (`scenarios.read`).
- `POST /api/v1/scenarios`: Create scenario with validated configuration (`scenarios.create`).
- `GET /api/v1/scenarios/{id}`: Retrieve scenario definition (`scenarios.read`).
- `PUT /api/v1/scenarios/{id}`: Update scenario definition or status (`scenarios.update`).
- `DELETE /api/v1/scenarios/{id}`: Remove scenario (`scenarios.delete`).
- `POST /api/v1/scenarios/{id}/prepare`: Initialize execution session (`scenarios.run` / `scenarios.execute`).
- `POST /api/v1/scenarios/{id}/start`: Start simulation (`scenarios.run` / `scenarios.execute`).
- `POST /api/v1/scenarios/{id}/pause`: Pause virtual clock (`scenarios.run` / `scenarios.execute`).
- `POST /api/v1/scenarios/{id}/resume`: Resume virtual clock (`scenarios.run` / `scenarios.execute`).
- `POST /api/v1/scenarios/{id}/step`: Advance $N$ deterministic ticks (`scenarios.run` / `scenarios.execute`).
- `POST /api/v1/scenarios/{id}/stop`: Stop simulation (`scenarios.run` / `scenarios.execute`).
- `POST /api/v1/scenarios/{id}/reset`: Reset to initial state (`scenarios.run` / `scenarios.execute`).
- `GET /api/v1/scenarios/{id}/status`: Query execution telemetry and status (`scenarios.read`).

### Geofence Management Endpoints (`/api/v1/geofences`)
- `GET /api/v1/geofences`: List geofences with cursor pagination (`scenarios.read`).
- `POST /api/v1/geofences`: Create geofence boundary (`scenarios.create` / `scenarios.write`).
- `GET /api/v1/geofences/{id}`: Retrieve geofence details (`scenarios.read`).
- `PUT /api/v1/geofences/{id}`: Update geofence geometry (`scenarios.update` / `scenarios.write`).
- `DELETE /api/v1/geofences/{id}`: Delete geofence (`scenarios.delete` / `scenarios.write`).

---

## 7. Audit and Telemetry Separation

High-frequency simulation telemetry and virtual clock stepping do not create Stage E `AuditEvent` records. User management actions (creating/deleting scenarios, updating geofences) use standard HTTP endpoints with RBAC authorization checks.
