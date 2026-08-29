# Stage HI1 — Historical Intelligence Persistence, Swarm Replay & AI Analytics

**Status**: Verified & Complete  
**Architecture Layer**: Historical Truth Store & Deterministic Analytics  
**Primary Developers**: AeroGuard Engineering  
**Scope**: Defensive Situational Awareness & Research Only  

---

## 1. Executive Summary

Prior to Stage HI1, AeroGuard's multi-track defensive intelligence (spatial correlation groups, coordinated formations, behavioral state classifications, and explainable threat priorities) resided exclusively in the volatile RAM state of the `IncrementalIntelligenceStore`. While the live AI3 pipeline achieved sub-millisecond execution and sub-microsecond REST snapshot reads, historical replay and analytical systems could not reconstruct swarm behaviors or explain past situational transitions once tracks were archived.

**Stage HI1 solves this architectural gap** by establishing:
1. **Asynchronous Non-Blocking Historical Persistence**: Throttled snapshot enqueuing ($1.0\text{ s}$ intervals) and change-driven event persistence for swarm groups and behavioral transitions without touching or degrading the hot live telemetry path.
2. **Deterministic Swarm Replay (`ReplayEngine`)**: Virtual-clock reconstruction of multi-track swarm bounding hulls, formation coordination indexes, and threat priorities alongside kinematics.
3. **Historical AI Analytics (`GET /api/v1/analytics/intelligence`)**: Bounded analytical query aggregations over group structures, coordination peaks, and behavioral distribution over historical operational windows.
4. **Unified Operator UI**: Live and historical map rendering (`TacticalMap` + WebGPU/Canvas 2D) of swarm group hulls and detailed inspection panels in both Replay and Analytics consoles.

---

## 2. Architecture & Data Contracts

### 2.1 Database Models & Truth Tables

Three dedicated SQLAlchemy models manage persistent defensive intelligence under Alembic migration `0007_intelligence_history`:

```text
┌─────────────────────────────────────────────────────────────────────────────┐
│                             Database Schema                                 │
├──────────────────────────┬──────────────────────────┬───────────────────────┤
│  intelligence_snapshots  │   track_group_history    │ behavior_event_history│
├──────────────────────────┼──────────────────────────┼───────────────────────┤
│ id (UUID PK)             │ id (UUID PK)             │ id (UUID PK)          │
│ timestamp (DateTime IX)  │ group_id (String IX)     │ track_id (String IX)  │
│ active_track_count (Int) │ timestamp (DateTime IX)  │ timestamp (DateTime)  │
│ group_count (Int)        │ member_track_ids (JSON)  │ previous_state (Str)  │
│ formation_count (Int)    │ member_count (Int)       │ new_state (Str)       │
│ peak_threat_score (Float)│ centroid_lat (Float)     │ duration_seconds (Flt)│
│ summary_json (JSON)      │ centroid_lon (Float)     │ confidence (Float)    │
│ created_at (DateTime)    │ radius_meters (Float)    │ reasons (JSON)        │
│                          │ behavioral_state (Str)   │ created_at (DateTime) │
│                          │ coordination_index (Flt) │                       │
│                          │ formation_type (Str)     │                       │
│                          │ created_at (DateTime)    │                       │
└──────────────────────────┴──────────────────────────┴───────────────────────┘
```

### 2.2 Non-Blocking Ingestion Architecture

Live track updates pass into `IntelligencePipeline.process_track_update()`, which detects state transitions in-memory and pushes payload tuples into a bounded `queue.Queue` within `IntelligencePersistenceService`.

```mermaid
flowchart TD
    TrackUpdate[Track Update] --> Store[IncrementalIntelligenceStore (In-Memory RAM)]
    Store --> ChangeDetect{State / Topology Change?}
    ChangeDetect -- Yes --> Enqueue[Queue.put_nowait() < 1 µs]
    ChangeDetect -- No --> Skip[Skip Event Enqueue]
    Store --> ThrottledSnapshot{Throttled (>= 1.0s)?}
    ThrottledSnapshot -- Yes --> EnqueueSnap[Queue.put_nowait(Snapshot)]
    ThrottledSnapshot -- No --> SkipSnap[Skip Snapshot]
    Enqueue --> BackgroundWorker[Persistence Flush Worker]
    EnqueueSnap --> BackgroundWorker
    BackgroundWorker --> DB[(SQLite / PostgreSQL Truth Store)]
```

---

## 3. Replay Engine Integration

`ReplayEngine.get_snapshot_at(target_time)` reconstructs historical situational awareness deterministically:
1. Reconstructs kinematic track positions via `TrackHistory` sequence.
2. Queries the closest `IntelligenceSnapshot` at or before `target_time` within lookback window $\Delta t$.
3. Falls back to `TrackGroupHistory` deduplicated group reconstructions if snapshots are sparse.
4. Applies track filters (`ReplayFilter.track_ids`) to prune swarm groups, formations, and threat priorities to the selected subset.
5. Populates `ReplaySnapshot.intelligence` and `ReplaySnapshot.group_hulls` for tactical visualization.

---

## 4. Analytical Aggregations & Metrics

The analytics endpoint `GET /api/v1/analytics/intelligence` executes bounded SQL queries over the truth tables:
- **`total_snapshots`**: Total multi-track states captured.
- **`total_group_events`**: Group creation, split, merge, and dissolution count.
- **`total_behavior_transitions`**: Classified behavioral shifts (`NORMAL` $\to$ `COORDINATED` $\to$ `APPROACHING`).
- **`behavior_distribution`**: State transition histogram.
- **`group_state_distribution`**: Swarm state histogram.
- **`avg_group_size`** & **`max_group_size`**: Swarm size distribution.
- **`avg_coordination_index`**: Mean kinematic synchronization score.
- **`coordination_peaks`**: Filtered list of highest-synchronization formations ($\ge 70\%$).
- **`threat_score_time_series`**: Sampled temporal trajectory of swarm priority progression.

---

## 5. Security & RBAC Invariants

1. **Defensive-Only Compliance**: All historical intelligence calculations strictly inform defensive situational awareness. No fire control, engagement, weapon targeting, jamming, or destructive action functionality is implemented.
2. **Access Control**: Replay and Analytics endpoints enforce role-based access control (`tracks.read`, `threats.read`, `scenarios.read`).
3. **Failure Isolation**: Database outages or disk write bottlenecks cannot crash the live tracking pipeline. `IntelligencePersistenceService` catches all database operational errors, increments `dropped_count`, and preserves the real-time operational loop.
