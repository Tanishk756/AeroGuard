# Stage F6 Historical Operations, Replay & Deterministic Analytics

Stage F6 introduces the historical query, timeline aggregation, descriptive analytics, and deterministic replay layer over the operational data foundation established in Stages F1–F5.

```text
Operational Foundation (F1-F5 Persisted Truth)
  ├── Detections (Raw & Normalized Sensor Observations)
  ├── Tracks (Confirmed & Correlated Objects)
  ├── Track History (Append-Only State Trajectories)
  ├── Threat Assessments (Operational Scores & Levels)
  ├── Alerts (Geofence Breaches, Sensor Drops)
  └── Scenarios (Synthetic Simulations & Ground Truth)
                     │
                     ▼
┌────────────────────────────────────────────────────────┐
│             Stage F6 Read & Analysis Layer             │
├────────────────────────────────┬───────────────────────┤
│ History & Timeline Aggregation │ Descriptive Analytics │
│ (Bounded Queries, Normalized   │ (Detections, Tracks,  │
│ Multi-Source Event Timeline)   │ Alerts, Threats Aggs) │
├────────────────────────────────┴───────────────────────┤
│            Deterministic Replay & Comparison           │
│ (Virtual Step Clock, State Reconstruction at Time T,   │
│  Structural Canonical Run Differences & Divergences)   │
└────────────────────────────────────────────────────────┘
```

---

## 1. Architectural Principles & Operational Integrity

- **Read-Only Over Canonical Operational Truth**: Stage F6 reads from the immutable operational tables (`detections`, `tracks`, `track_history`, `threat_assessments`, `alerts`, `scenarios`, `geofences`) persisted by F1–F5. It introduces **no new database tables** and **no schema migrations**.
- **Zero Simulation / Operational DB Mutations**: Replaying a historical interval, stepping virtual replay clocks, and querying analytics perform strictly read operations. Zero records are inserted, modified, or deleted in the operational tables.
- **Audit Log Isolation**: Querying historical data, computing analytics, and advancing replay clocks do **not** emit high-frequency telemetry into `audit_events`. High-level administrative/security actions continue to be audited exclusively via `app.services.audit`.
- **Operational vs Creation Timestamps**: Queries and replay use operational timestamps (`Detection.timestamp`, `TrackHistory.timestamp`, `ThreatAssessment.created_at`, `Alert.created_at`, `Alert.resolved_at`) representing event occurrence time in simulation/real-world coordinates, rather than database insertion wall-clock time.
- **Bounded Queries**: All historical endpoints enforce maximum time window limits ($\le 30$ days) and deterministic pagination to protect backend performance and prevent unbounded scans.
- **Zero External Infrastructure**: No WebSockets, SSE, Redis, Kafka, RabbitMQ, Celery, distributed task workers, or machine learning frameworks.

---

## 2. Historical Querying Layer (`app.history`)

Located in `backend/app/history/`:
- **`queries.py`**:
  - `validate_time_window(start_time, end_time)`: Validates UTC time boundaries, confirms $start \le end$, and enforces maximum window constraints.
  - `query_historical_detections(db, ...)`: Deterministic pagination (`timestamp ASC`, `id ASC`) with sensor, source type, classification, and track filters.
  - `query_historical_track_points(db, track_id, ...)`: Append-only trajectory points ordered by sequence number (`sequence ASC`, `timestamp ASC`).
  - `get_track_state_at(db, track_id, as_of_time)`: Resolves the latest historical state vector point $(\text{lat}, \text{lon}, \text{alt}, \text{vel}, \text{heading}, \text{confidence}, \text{state})$ at or immediately before virtual timestamp $T$.
  - `query_historical_alerts(db, ...)`: Alerts within time window filtered by severity, status, alert type, track, or sensor.
  - `query_historical_threats(db, ...)`: Threat assessments filtered by level, track, or minimum threat score.
- **`timeline.py`**:
  - `build_operational_timeline(db, ...)`: Normalizes disparate operational entities (`DETECTION_OBSERVED`, `TRACK_STATE_CHANGED`, `THREAT_ASSESSED`, `ALERT_RAISED`, `ALERT_RESOLVED`, `GEOFENCE_BREACHED`) into unified `TimelineItem` records.
  - **Deterministic Tie-Breaking**: When multiple events share the exact same microsecond timestamp, ordering is strictly established via:
    1. Timestamp ascending
    2. Event Type priority (`DETECTION_OBSERVED` $\rightarrow$ `TRACK_STATE_CHANGED` $\rightarrow$ `THREAT_ASSESSED` $\rightarrow$ `GEOFENCE_BREACHED` $\rightarrow$ `ALERT_RAISED` $\rightarrow$ `ALERT_RESOLVED`)
    3. Entity ID string ascending.
- **`service.py`**: `HistoryService` coordinating database access and API responses.

---

## 3. Descriptive Analytics Layer (`app.analytics`)

Located in `backend/app/analytics/`:
- **`queries.py`**:
  - Aggregates operational metrics across specified time windows using standard SQL aggregate expressions (`COUNT`, `AVG`, `MIN`, `MAX`).
  - Returns detection counts by sensor modality, track counts by classification and final lifecycle state, alert counts by type and severity, average resolution duration, and threat score distributions.
- **`metrics.py`**:
  - Assembles structured domain metrics (`DetectionMetrics`, `TrackMetrics`, `AlertMetrics`, `ThreatMetrics`) into `AnalyticsSummaryResponse`.
- **`service.py`**: `AnalyticsService` providing summary and focused analytical endpoints.

---

## 4. Deterministic Replay & Comparison Engine (`app.replay`)

Located in `backend/app/replay/`:
- **`models.py`**: `ReplayConfig` domain configuration with time normalization and replay filters.
- **`engine.py`**: `ReplayEngine`
  - Reconstructs operational situational awareness at virtual timestamp $T$.
  - **State Reconstruction**:
    - Queries active tracks at time $T$ using `get_track_state_at` (omitting tracks archived or lost before $T$).
    - Retrieves recent detections within a discrete historical delta window.
    - Retrieves active (unresolved or resolved after $T$) alerts and latest threat assessments.
  - **Virtual Stepping**: Discrete clock advancement $t_k = t_0 + k \cdot \Delta t$ without wall-clock sleep or asynchronous background tasks.
- **`comparison.py`**: `compare_replay_runs(db, request)`
  - Evaluates two replay windows/runs for structural equivalence or divergence.
  - Compares canonical operational data: detection totals, sensor modality distributions, active track counts, average confidence, peak threat scores, alert severity breakdowns.
  - Ignores ephemeral database artifacts (random UUIDs, internal DB insert timestamps).
  - Emits structured diff reports highlighting mismatches and metric deltas.

---

## 5. REST API Endpoints & RBAC Authorization

All endpoints reside under `/api/v1` and enforce RBAC permissions aligned with Stage D:

| Endpoint | Method | Required Authority | Description |
| :--- | :--- | :--- | :--- |
| `/api/v1/history/detections` | `GET` | `sensors.read` | Bounded historical detections with pagination |
| `/api/v1/history/tracks/{id}` | `GET` | `tracks.read` | Append-only historical trajectory points for a track |
| `/api/v1/history/tracks/{id}/state` | `GET` | `tracks.read` | Reconstructed track state vector at timestamp $T$ |
| `/api/v1/history/alerts` | `GET` | `alerts.read` | Historical alerts by time range, severity, status |
| `/api/v1/history/threats` | `GET` | `threats.read` | Historical threat assessments by score and level |
| `/api/v1/history/timeline` | `GET` | `sensors.read` \| `tracks.read` \| `alerts.read` \| `threats.read` | Unified multi-source operational timeline |
| `/api/v1/analytics/summary` | `GET` | `sensors.read` \| `tracks.read` \| `alerts.read` \| `threats.read` | Consolidated descriptive operational metrics |
| `/api/v1/analytics/detections` | `GET` | `sensors.read` | Detection counts by sensor and modality |
| `/api/v1/analytics/tracks` | `GET` | `tracks.read` | Track lifecycles, states, and duration metrics |
| `/api/v1/analytics/alerts` | `GET` | `alerts.read` | Alert severity distributions and resolution times |
| `/api/v1/analytics/threats` | `GET` | `threats.read` | Threat score statistics and level counts |
| `/api/v1/replay/query` | `POST` | `scenarios.read` \| `tracks.read` \| `scenarios.run` | Stateless snapshot reconstruction at timestamp $T$ |
| `/api/v1/replay/step` | `POST` | `scenarios.read` \| `tracks.read` \| `scenarios.run` | Advance virtual replay clock by $N$ steps |
| `/api/v1/replay/compare` | `POST` | `scenarios.read` \| `tracks.read` \| `scenarios.run` | Structural comparison between two replay runs |

---

## 6. Verification and Regression Testing

The test suite validates:
1. `backend/tests/test_history.py`: Window limits, bounded queries, deterministic sorting, state at $T$, alert/threat history, and end-to-end simulation consistency.
2. `backend/tests/test_timeline.py`: Multi-source event normalization and deterministic tie-breaking.
3. `backend/tests/test_analytics.py`: Aggregate metrics calculation and determinism.
4. `backend/tests/test_replay.py`: Discrete stepping, snapshot reconstruction, and read-only row-count verification.
5. `backend/tests/test_replay_comparison.py`: Identical and differing replay comparisons.
6. `backend/tests/test_history_api.py`, `backend/tests/test_analytics_api.py`, `backend/tests/test_replay_api.py`: 401 unauthenticated, 403 unauthorized, 400 validation, and authorized 200 payload structures.
