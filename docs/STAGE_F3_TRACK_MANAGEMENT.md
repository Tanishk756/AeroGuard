# Stage F3 Detection Association and Track Management

Stage F3 implements deterministic detection association, track lifecycle management, and append-only track history:

```text
Persisted Detection
        ↓
Candidate Generation
        ↓
Gating
        ↓
Association Scoring
        ↓
Deterministic Assignment
        ↓
Track Creation / Update
        ↓
Association Record
        ↓
Track History
        ↓
Track Lifecycle
```

F3 processes persisted F2 `Detection` records, updates or creates persistent `Track` entities, records explainable `TrackAssociation` rows, appends `TrackHistory`, advances track lifecycle states, and exposes read-only query APIs. Alert evaluation, threat scoring, countermeasures, scenario execution, WebSockets, background workers, AI/ML, and frontend interfaces are strictly deferred to future stages.

## 1. Association Architecture

The association engine is structured into modular, decoupled components:

- **Distance & Kinematics (`app.tracking.association`)**:
  - Horizontal distance uses the standard-library Great-Circle Haversine formula on WGS84 coordinates ($R = 6,371,000\,\text{m}$). Raw Euclidean lat/lon distance is not used.
  - Vertical distance is calculated as $\text{abs}(\text{alt}_1 - \text{alt}_2)$ when both altitudes exist. When missing, vertical distance is `None` and altitude is never fabricated.
  - Angular difference computes the minimal difference in degrees across the $0^\circ / 360^\circ$ boundary.
- **Candidate Generation (`DetectionCandidateProvider`)**:
  - Queries active candidate tracks in `NEW`, `ACTIVE`, or `STALE` states within a configurable temporal window.
  - Excludes `LOST` and `ARCHIVED` tracks.
- **Gating (`AssociationGate`)**:
  - Validates candidates against configurable maximum boundaries:
    - Time delta $\le 10.0\,\text{s}$
    - Horizontal distance $\le 500.0\,\text{m}$ (expanded by $1.5\times$ to $750.0\,\text{m}$ for `STALE` coasting tracks)
    - Vertical distance $\le 150.0\,\text{m}$ (expanded by $1.5\times$ to $225.0\,\text{m}$ for `STALE` coasting tracks, when both present)
    - Velocity delta $\le 50.0\,\text{m/s}$ (optional gate, evaluated when both present)
    - Heading delta $\le 90.0^\circ$ (optional gate, evaluated when both present)
  - Candidates failing any applicable gate are rejected with deterministic, explainable reasons.
- **Scoring (`AssociationScorer`)**:
  - Computes a deterministic normalized score in $[0.0, 1.0]$.
  - Default component weights:
    - Spatial proximity: $50\%$
    - Temporal proximity: $20\%$
    - Velocity compatibility: $15\%$
    - Heading compatibility: $10\%$
    - Confidence compatibility: $5\%$
  - When optional kinematic values (velocity, heading, altitude) are absent, the score is **renormalized** across available components without arbitrary penalties.
  - Minimum association score threshold is $0.60$.
- **Deterministic Tie-Breaking**:
  - Evaluated candidates are sorted deterministically by:
    1. Highest score (`-score`)
    2. Smallest horizontal distance
    3. Smallest absolute time delta
    4. Oldest `first_seen_at`
    5. Lexical track UUID (`track.id`)
- **Track Creation & ID Generation**:
  - Unmatched detections create a new track in `TrackState.NEW` with `source_count = 1`. A single detection never creates `ACTIVE`.
  - Track IDs are deterministic UUID5 values generated via `uuid5(NAMESPACE_URL, "aeroguard:track:track:<detection.id>")`, enabling perfectly reproducible replays.
- **Track Update & Smoothing**:
  - Confidence is smoothed deterministically: $\text{conf}_{\text{new}} = 0.7 \times \text{conf}_{\text{old}} + 0.3 \times \text{conf}_{\text{det}}$.
  - The first non-null classification is preserved.
  - `source_count` is incremented only when a new, distinct sensor contributes to the track.

## 2. Track Lifecycle

Tracks transition through explicit states:

```text
NEW (tentative)
  ↓ confirmation threshold (3 qualifying detections within 30s)
ACTIVE (confirmed)
  ↓ missed-detection timeout (10s coast timeout)
STALE (coasting)
  ↓ lost timeout (60s)
LOST (lost)
  ↓ archive delay (24h)
ARCHIVED (closed)
```

- **Confirmation**: Requires 3 qualifying associated detections within a 30-second confirmation window from `first_seen_at`.
- **Coasting (`STALE`)**: Occurs when no detection is received for $> 10\,\text{s}$. Coasting tracks maintain last known coordinates and allow wider ($1.5\times$) spatial gates. An associated detection reconfirms the track back to `ACTIVE`.
- **Closed Tracks**: `ARCHIVED` tracks never reopen, and track IDs are never reused. Late or out-of-order detections do not reopen closed tracks or move active track timestamps backwards in time.
- **Lifecycle Advancement**: Handled explicitly by `TrackLifecycleService.advance(now)`. History entries are appended only upon meaningful state transitions.

## 3. Database Migration and Schema

Migration `0006_track_management` revises `0005_operational_core` and adds the `track_associations` table:

- `id`: `String(36)` primary key (UUID).
- `detection_id`: `String(36)` foreign key to `detections.id` with `UNIQUE` constraint.
- `track_id`: `String(36)` foreign key to `tracks.id` (`CASCADE`).
- `sensor_id`: `String(36)` foreign key to `sensors.id` (`RESTRICT`).
- `timestamp`: `DateTime` observation timestamp.
- `distance_meters`, `vertical_distance_meters`, `time_delta_seconds`: Non-negative geometric deltas.
- `score`: Bounded float in $[0.0, 1.0]$.
- `decision`: Explicit enum (`ASSOCIATED`, `NEW_TRACK`, `NO_CANDIDATE`, `GATE_REJECTED`, `STALE_DETECTION`, `CLOSED_TRACK`, `DUPLICATE`).
- `reason`: Bounded explanation string.
- `gate_result`: Gate status (`PASSED` or failure code).
- `created_at`: Naive UTC timestamp.
- Indexes on `(track_id, timestamp)`, `(sensor_id, timestamp)`, `(decision, timestamp)`, and `(detection_id)`.

Detection records remain strictly immutable; `Detection.track_id` is not mutated. `TrackAssociation` and `TrackHistory` are immutable and append-only at the ORM layer.

## 4. API and RBAC

Stage F3 exposes read-only track query endpoints under `/api/v1`:

- `GET /api/v1/tracks`: List tracks with bounded pagination (`limit`, `cursor`) and filters (`state`, `classification`, `last_seen_from`, `last_seen_to`).
- `GET /api/v1/tracks/{track_id}`: Retrieve detailed track state.
- `GET /api/v1/tracks/{track_id}/history`: Retrieve chronological history entries for a track with bounded pagination (`limit`, `cursor`, `sequence_from`).

All three endpoints require the existing `tracks.read` RBAC permission. Processing remains internal; no public mutation or processing endpoints are exposed.

## 5. Security, Audit, and Operational Boundaries

- **Audit Boundary**: Telemetry association and track updates do not create Stage E `AuditEvent` records. An in-process `DetectionAssociated` operational event is returned for internal coordination.
- **Idempotency & Concurrency**: Duplicate detection submissions are idempotent and return `DUPLICATE` without creating redundant tracks or history records. Database transactions use nested savepoints to safely catch concurrent duplicate insertion races under SQLite.
- **Replay**: Chronological replay (`timestamp ASC, detection_id ASC`) against a clean database produces identical track IDs, states, and history sequences.
- **Deferred Systems**: Alerts, threat scoring, countermeasures, background task queues, and realtime WebSocket feeds remain deferred.
