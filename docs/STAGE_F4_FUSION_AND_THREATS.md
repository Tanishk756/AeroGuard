# Stage F4: Multi-Sensor Fusion, Track Quality, Geofencing, Threat Assessment, and Operational Alerts

Stage F4 implements multi-sensor consensus, continuous track quality evaluation, 2D/3D geofence volume containment, deterministic operational threat prioritization, alert candidate evaluation and deduplication, and read-only query APIs for alerts, threats, and geofences.

## 1. Scope & Architectural Boundaries

Stage F4 operates strictly on top of Stage F3 track management and detection association:
- **No AI/ML / No Weaponization**: Operates entirely via deterministic algorithms and explainable factor models. Threat scoring evaluates defensive operational prioritization, not attack probability.
- **In-Process Telemetry Pipeline**: Multi-sensor consensus, classification reconciliation, and alert evaluation execute synchronously within the transaction boundary of detection ingestion and track lifecycle progression.
- **Idempotency & Deduplication**: Threat assessments use track-level upserts. Alerts deduplicate against open/acknowledged active alerts to eliminate alert storming.
- **No Routine Telemetry Auditing**: Routine kinematic updates, threat evaluations, and operational alerts do NOT create `AuditEvent` records.

```
Detection Ingestion (F2) -> Association & Gating (F3) -> Multi-Sensor Fusion & Quality (F4) -> Geofence & Threats (F4) -> Operational Alerts (F4)
```

## 2. Multi-Sensor Spatial and Kinematic Consensus

Located in `backend/app/fusion/consensus.py`:
- **Uncertainty & Confidence Weighting**: Associated detections update track coordinates $(lat, lon)$ using convex combination weights determined by detection confidence and horizontal uncertainty inverse variance:
  $$\alpha = \max\left(0.01, \min\left(0.50, \frac{w_{\text{det}}}{w_{\text{det}} + w_{\text{track}}}\right)\right)$$
- **No Dimension Fabrication**: Missing dimensions (such as altitude, velocity, or heading) from single-modality sensors are preserved when existing or adopted when newly observed, but never fabricated.
- **Minimal Angular Arc Interpolation**: Heading fusion takes the shortest angular distance across the $0^\circ / 360^\circ$ meridian.

## 3. Track Quality Scoring & Source Diversity

Located in `backend/app/fusion/quality.py`:
- **Source Diversity**: Computed from distinct contributing sensors ($N$) and sensing modalities ($M$, e.g. Radar, Optical, RF):
  $$D = \min(1.0, 0.40 \cdot N + 0.30 \cdot M)$$
- **Composite Track Quality**:
  $$Q = 0.40 \cdot C + 0.25 \cdot D + 0.20 \cdot T + 0.15 \cdot R$$
  where $C$ is smoothed confidence ($0.40$), $D$ is source diversity ($0.25$), $T$ is temporal continuity ($0.20$), and $R$ is spatial residual agreement ($0.15$).
- **Coasting Confidence Decay**:
  $$C(t) = C_0 \cdot 2^{-\Delta t / \tau_{\text{half}}}$$
  Applied when tracks transition to `STALE` without new observations.

## 4. Multi-Source Classification Reconciliation

Located in `backend/app/fusion/classification.py`:
- Gathers classification labels from all associated detections within the historical confirmation window.
- Computes confidence-weighted voting scores per label.
- Employs deterministic lexicographical tie-breaking for equal evidence scores.

## 5. 2D / 3D Geofence Spatial Engine

Located in `backend/app/geofencing/engine.py`:
- **Bounding Box Containment**: Validates horizontal coordinates within $[min\_lat, max\_lat]$ and $[min\_lon, max\_lon]$.
- **Polygon Containment**: Uses a deterministic ray-casting algorithm with bounding box pre-filtering.
- **3D Altitude Containment**: Checks vertical bounds $[min\_altitude, max\_altitude]$. Detections lacking altitude measurements are flagged with `altitude_indeterminate=True`.
- **Perimeter Proximity**: Computes approximate Haversine distance in meters to the nearest perimeter boundary.

## 6. Deterministic Operational Threat Prioritization

Located in `backend/app/threats/`:
- **Operational Purpose**: Quantifies defensive triage urgency (0 to 100) and operational threat levels (`LOW`, `MEDIUM`, `HIGH`, `CRITICAL`), not attack intent or hostility likelihood.
- **Explainable Factors**:
  - $F_{\text{geofence}}$: 1.0 if inside active perimeter; proximity-decayed score if near perimeter.
  - $F_{\text{kinematic}}$: Speed normalized to baseline operational envelope ($50\text{ m/s}$).
  - $F_{\text{classification}}$: Configurable risk weighting (e.g. UAV=0.85, Plane=0.40, Bird=0.05).
  - Composite Score:
    $$\text{Score} = 100.0 \cdot (w_g F_g + w_k F_k + w_c F_c) \cdot Q$$
- **Persistence**: Stored in `threat_assessments` table with structured, explainable JSON factors. Upserted per track.

## 7. Operational Alert Generation & Deduplication

Located in `backend/app/alerts/`:
- **Rule Triggers**:
  - `TRACK_DETECTED`: Tentative track confirmed to `ACTIVE`.
  - `GEOFENCE_BREACH`: Track penetrates active geofence volume. Severity escalates to `CRITICAL` for high-priority threats.
  - `TRACK_LOST`: Track transitions to `LOST` after coasting timeout.
  - `DATA_QUALITY_LOW`: Active track quality drops below 0.30.
- **Deduplication**: Checks database for active `OPEN` or `ACKNOWLEDGED` alerts for the same track and alert condition before creating new records.
- **Resolution**: Automatically marks open alerts as `RESOLVED` upon track archival.

## 8. Read-Only Query APIs

Mounted under `/api/v1`:
- `GET /api/v1/threats` (requires `threats.read`): List threat assessments with filters (`level`, `min_score`) and cursor pagination.
- `GET /api/v1/threats/{track_id}` (requires `threats.read`): Detail view for a track's threat evaluation.
- `GET /api/v1/alerts` (requires `alerts.read`): List alerts with filters (`status`, `severity`, `type`, `track_id`, `sensor_id`, `created_from`, `created_to`) and cursor pagination.
- `GET /api/v1/alerts/{alert_id}` (requires `alerts.read`): Detail view of an operational alert.
- `GET /api/v1/geofences` (requires `scenarios.read`): List geofence perimeters with `enabled` filter and cursor pagination.
- `GET /api/v1/geofences/{geofence_id}` (requires `scenarios.read`): Detail view of a geofence geometry.
