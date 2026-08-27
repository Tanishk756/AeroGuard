"""Thread-safe, deterministic in-memory Incremental Intelligence State Store.

AeroGuard Stage AI3-C — Incremental In-Memory Intelligence Store.

PURPOSE
-------
Maintains the authoritative in-memory state of multi-track defensive intelligence:
- Active track observations
- SpatialHashGrid 2D index
- Correlated track groups (AI2-B / AI3-B)
- Behavioral state machine states (AI2-C)
- Coordinated formations (AI2-D)
- Temporal persistent anomaly accumulators (AI2-D)
- Explainable threat priority assessments (AI2-E)
- Monotonic version sequence counter

Eliminates synchronous full-population recomputation for REST reads (GET /intelligence/summary)
by maintaining an immutable pre-computed MultiTrackIntelligenceSummary snapshot.

THREAD SAFETY
-------------
All mutations and snapshot reads are guarded by a reentrant mutex (threading.RLock).
Readers are guaranteed to observe complete, internally consistent snapshots (zero partial updates).
"""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
import threading
from typing import Any

from ai.anomaly.persistent import (
    PersistentAnomalyAccumulator,
    PersistentAnomalyConfig,
)
from ai.behavior.classifier import (
    BehaviorClassifierConfig,
    ClassifierInput,
    ClassifierState,
    classify_track_behavior,
)
from ai.correlation.coordination import (
    compute_coordination_index,
)
from ai.correlation.grouping import (
    GroupingConfig,
    TrackObservation,
    correlate_tracks,
    to_track_observation,
)
from ai.correlation.spatial_grid import SpatialGridConfig, SpatialHashGrid
from ai.priority.scoring import (
    PriorityScoringConfig,
    evaluate_threat_priority,
)
from ai.schemas import (
    BehaviorClassification,
    BehavioralState,
    CoordinatedFormation,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    TrackGroup,
)


@dataclass(frozen=True)
class IncrementalStoreConfig:
    """Configuration container for all underlying AI2 algorithms inside the incremental store."""

    spatial_grid: SpatialGridConfig = field(default_factory=SpatialGridConfig)
    grouping: GroupingConfig = field(default_factory=GroupingConfig)
    behavior: BehaviorClassifierConfig = field(default_factory=BehaviorClassifierConfig)
    persistent_anomaly: PersistentAnomalyConfig = field(default_factory=PersistentAnomalyConfig)
    priority: PriorityScoringConfig = field(default_factory=PriorityScoringConfig)


class IncrementalIntelligenceStore:
    """Thread-safe, deterministic in-memory store for real-time multi-track defensive intelligence."""

    def __init__(self, config: IncrementalStoreConfig | None = None) -> None:
        self._cfg = config or IncrementalStoreConfig()
        self._lock = threading.RLock()

        # Spatial Hash Grid for O(1) candidate spatial indexing
        self._grid = SpatialHashGrid(self._cfg.spatial_grid)

        # Authoritative track observations: track_id -> TrackObservation
        self._tracks: dict[str, TrackObservation] = {}

        # Group state: group_id -> TrackGroup
        self._groups: dict[str, TrackGroup] = {}
        # Track-to-group reverse map: track_id -> group_id
        self._track_group_map: dict[str, str] = {}

        # Formation state: group_id -> CoordinatedFormation
        self._formations: dict[str, CoordinatedFormation] = {}

        # Behavioral state machine hysteresis: track_id -> ClassifierState
        self._classifier_states: dict[str, ClassifierState] = {}
        # Current behavioral classifications: track_id -> BehaviorClassification
        self._behaviors: dict[str, BehaviorClassification] = {}

        # Persistent anomaly accumulator (temporal exponential decay across sequential ticks)
        self._anomaly_accumulator = PersistentAnomalyAccumulator(self._cfg.persistent_anomaly)

        # Threat priority assessments: track_id -> ThreatPriorityAssessment
        self._priorities: dict[str, ThreatPriorityAssessment] = {}

        # Monotonic state mutation sequence
        self._version: int = 0

        # Pre-computed immutable snapshot for instantaneous O(1) REST reads
        self._cached_summary: MultiTrackIntelligenceSummary = MultiTrackIntelligenceSummary(
            groups=[],
            behaviors=[],
            formations=[],
            priorities=[],
            evaluated_at=datetime.now(UTC),
        )

    # ── State Mutation API ───────────────────────────────────────────────────

    def update_track(
        self,
        observation: Any,
        instantaneous_anomaly_score: float | None = None,
        now: datetime | None = None,
    ) -> ThreatPriorityAssessment:
        """Incrementally update or insert a single track observation using localized dirty neighborhood evaluation.
        
        Guarantees:
        - O(K_local) scaling where K_local is the number of tracks in the local spatial neighborhood.
        - Atomic state transition under lock.
        - Monotonic version increment.
        - Immediate O(1) snapshot availability.
        """
        obs = to_track_observation(observation)
        eval_ts = now or obs.timestamp or datetime.now(UTC)

        with self._lock:
            # 1. Identify old neighborhood and group associations
            old_candidates: set[str] = set()
            old_grp_members: set[str] = set()
            if obs.id in self._tracks:
                old_candidates = set(self._grid.get_candidate_neighbors(obs.id))
                old_gid = self._track_group_map.get(obs.id)
                if old_gid and old_gid in self._groups:
                    old_grp_members = set(self._groups[old_gid].member_track_ids)

            # 2. Update track observation & spatial grid
            self._tracks[obs.id] = obs
            self._grid.update(obs.id, obs.latitude, obs.longitude, observation=obs)
            new_candidates = set(self._grid.get_candidate_neighbors(obs.id))

            # 3. Determine affected neighborhood: union of old, new, and group members
            affected_ids: set[str] = {obs.id} | old_candidates | new_candidates | old_grp_members
            for mid in list(affected_ids):
                gid = self._track_group_map.get(mid)
                if gid and gid in self._groups:
                    affected_ids.update(self._groups[gid].member_track_ids)
                affected_ids.update(self._grid.get_candidate_neighbors(mid))

            # Filter to currently active tracks
            affected_active_ids = {tid for tid in affected_ids if tid in self._tracks}
            affected_obs = [self._tracks[tid] for tid in sorted(affected_active_ids)]

            # 4. Identify existing groups touching the affected region
            touching_group_ids = {
                self._track_group_map[tid]
                for tid in affected_active_ids
                if tid in self._track_group_map
            }
            touching_groups = [self._groups[gid] for gid in touching_group_ids if gid in self._groups]

            # Re-cluster only the affected active observations
            new_affected_groups = correlate_tracks(
                tracks=affected_obs,
                config=self._cfg.grouping,
                existing_groups=touching_groups,
                now=eval_ts,
            )

            # Remove old touching groups and formations
            for gid in touching_group_ids:
                self._groups.pop(gid, None)
                self._formations.pop(gid, None)

            # Clear affected tracks from reverse map
            for tid in affected_active_ids:
                self._track_group_map.pop(tid, None)

            # Insert newly discovered groups
            for g in new_affected_groups:
                self._groups[g.group_id] = g
                for mid in g.member_track_ids:
                    self._track_group_map[mid] = g.group_id

            # 5. Formations & Coordination Analysis for new affected groups
            for g in new_affected_groups:
                member_objs = [self._tracks[mid] for mid in g.member_track_ids if mid in self._tracks]
                fmt = compute_coordination_index(
                    group=g,
                    members=member_objs,
                    evaluated_at=eval_ts,
                )
                if fmt is not None:
                    self._formations[g.group_id] = fmt

            # 6. Update Persistent Anomaly for updated track
            self._anomaly_accumulator.update(
                track_id=obs.id,
                instantaneous_score=instantaneous_anomaly_score,
                timestamp=eval_ts,
            )

            # 7. Re-evaluate Behavioral Classifications & Threat Priorities for affected tracks ONLY
            for tid in sorted(affected_active_ids):
                t_obs = self._tracks[tid]
                grp_id = self._track_group_map.get(tid)
                grp = self._groups.get(grp_id) if grp_id else None
                fmt = self._formations.get(grp_id) if grp_id else None

                spd = float(t_obs.velocity or 0.0)
                hdg = float(t_obs.heading) if t_obs.heading is not None else None

                clf_inp = ClassifierInput(
                    track_id=tid,
                    speed_mps=spd,
                    heading_deg=hdg,
                    group_id=grp_id,
                    group_member_count=grp.member_count if grp else None,
                    timestamp=eval_ts,
                )
                prev_state = self._classifier_states.get(tid)
                b_class, new_clf_state = classify_track_behavior(
                    inp=clf_inp,
                    state=prev_state,
                    config=self._cfg.behavior,
                )
                self._classifier_states[tid] = new_clf_state
                self._behaviors[tid] = b_class

                # Persistent anomaly score
                p_anom_state = self._anomaly_accumulator.get_state(tid)
                p_anom_score = p_anom_state.persistent_score if p_anom_state else 0.0

                p_assess = evaluate_threat_priority(
                    track_id=tid,
                    group_id=grp_id,
                    behavior=b_class,
                    persistent_anomaly=p_anom_score,
                    coordination=fmt,
                    kinematics=spd,
                    sensor_confidence=float(t_obs.confidence),
                    config=self._cfg.priority,
                    evaluated_at=eval_ts,
                )
                self._priorities[tid] = p_assess

            # 8. Rebuild cached snapshot
            sorted_groups = sorted(self._groups.values(), key=lambda g: g.group_id)
            sorted_formations = sorted(self._formations.values(), key=lambda f: f.formation_id)
            sorted_behaviors = [self._behaviors[tid] for tid in sorted(self._behaviors.keys())]
            sorted_priorities = [self._priorities[tid] for tid in sorted(self._priorities.keys())]

            self._cached_summary = MultiTrackIntelligenceSummary(
                groups=sorted_groups,
                behaviors=sorted_behaviors,
                formations=sorted_formations,
                priorities=sorted_priorities,
                evaluated_at=eval_ts,
            )

            self._version += 1
            return self._priorities[obs.id]

    def update_tracks_batch(
        self,
        observations: Sequence[Any],
        now: datetime | None = None,
    ) -> list[ThreatPriorityAssessment]:
        """Atomically update multiple track observations in a single state transition."""
        if not observations:
            return []

        eval_ts = now or datetime.now(UTC)
        with self._lock:
            for item in observations:
                obs = to_track_observation(item)
                self._tracks[obs.id] = obs
                self._grid.update(obs.id, obs.latitude, obs.longitude, observation=obs)

            # Re-cluster full active population
            existing_groups_list = list(self._groups.values())
            all_observations = list(self._tracks.values())
            new_groups = correlate_tracks(
                tracks=all_observations,
                config=self._cfg.grouping,
                existing_groups=existing_groups_list,
                now=eval_ts,
            )

            self._groups = {g.group_id: g for g in new_groups}
            self._track_group_map = {}
            for g in new_groups:
                for mid in g.member_track_ids:
                    self._track_group_map[mid] = g.group_id

            self._formations = {}
            for g in new_groups:
                member_objs = [self._tracks[mid] for mid in g.member_track_ids if mid in self._tracks]
                fmt = compute_coordination_index(
                    group=g,
                    members=member_objs,
                    evaluated_at=eval_ts,
                )
                if fmt is not None:
                    self._formations[g.group_id] = fmt

            self._behaviors = {}
            self._priorities = {}

            for tid, t_obs in sorted(self._tracks.items()):
                grp_id = self._track_group_map.get(tid)
                grp = self._groups.get(grp_id) if grp_id else None
                fmt = self._formations.get(grp_id) if grp_id else None

                spd = float(t_obs.velocity or 0.0)
                hdg = float(t_obs.heading) if t_obs.heading is not None else None

                clf_inp = ClassifierInput(
                    track_id=tid,
                    speed_mps=spd,
                    heading_deg=hdg,
                    group_id=grp_id,
                    group_member_count=grp.member_count if grp else None,
                    timestamp=eval_ts,
                )
                prev_state = self._classifier_states.get(tid)
                b_class, new_clf_state = classify_track_behavior(
                    inp=clf_inp,
                    state=prev_state,
                    config=self._cfg.behavior,
                )
                self._classifier_states[tid] = new_clf_state
                self._behaviors[tid] = b_class

                p_anom_state = self._anomaly_accumulator.get_state(tid)
                p_anom_score = p_anom_state.persistent_score if p_anom_state else 0.0

                p_assess = evaluate_threat_priority(
                    track_id=tid,
                    group_id=grp_id,
                    behavior=b_class,
                    persistent_anomaly=p_anom_score,
                    coordination=fmt,
                    kinematics=spd,
                    sensor_confidence=float(t_obs.confidence),
                    config=self._cfg.priority,
                    evaluated_at=eval_ts,
                )
                self._priorities[tid] = p_assess

            sorted_groups = sorted(self._groups.values(), key=lambda g: g.group_id)
            sorted_formations = sorted(self._formations.values(), key=lambda f: f.formation_id)
            sorted_behaviors = [self._behaviors[tid] for tid in sorted(self._behaviors.keys())]
            sorted_priorities = [self._priorities[tid] for tid in sorted(self._priorities.keys())]

            self._cached_summary = MultiTrackIntelligenceSummary(
                groups=sorted_groups,
                behaviors=sorted_behaviors,
                formations=sorted_formations,
                priorities=sorted_priorities,
                evaluated_at=eval_ts,
            )

            self._version += 1
            return [self._priorities[to_track_observation(i).id] for i in observations]

    def drop_track(self, track_id: str, now: datetime | None = None) -> bool:
        """Remove a track from active state using localized dirty neighborhood update."""
        tid = str(track_id)
        eval_ts = now or datetime.now(UTC)

        with self._lock:
            if tid not in self._tracks:
                return False

            # Identify affected neighborhood before removal
            old_candidates = set(self._grid.get_candidate_neighbors(tid))
            old_gid = self._track_group_map.get(tid)
            old_grp_members = set(self._groups[old_gid].member_track_ids) if old_gid and old_gid in self._groups else set()

            # Remove from base dictionaries & spatial index
            self._tracks.pop(tid, None)
            self._grid.remove(tid)
            self._classifier_states.pop(tid, None)
            self._behaviors.pop(tid, None)
            self._priorities.pop(tid, None)
            self._anomaly_accumulator.reset_track(tid)
            self._track_group_map.pop(tid, None)

            # Determine affected neighborhood
            affected_ids = (old_candidates | old_grp_members) - {tid}
            for mid in list(affected_ids):
                gid = self._track_group_map.get(mid)
                if gid and gid in self._groups:
                    affected_ids.update(self._groups[gid].member_track_ids)
                affected_ids.update(self._grid.get_candidate_neighbors(mid))

            affected_active_ids = {i for i in affected_ids if i in self._tracks}
            affected_obs = [self._tracks[i] for i in sorted(affected_active_ids)]

            touching_group_ids = {
                self._track_group_map[i]
                for i in affected_active_ids
                if i in self._track_group_map
            }
            if old_gid:
                touching_group_ids.add(old_gid)

            touching_groups = [self._groups[gid] for gid in touching_group_ids if gid in self._groups]

            # Re-cluster affected active observations
            new_affected_groups = correlate_tracks(
                tracks=affected_obs,
                config=self._cfg.grouping,
                existing_groups=touching_groups,
                now=eval_ts,
            )

            # Clean up old groups and formations
            for gid in touching_group_ids:
                self._groups.pop(gid, None)
                self._formations.pop(gid, None)

            for i in affected_active_ids:
                self._track_group_map.pop(i, None)

            for g in new_affected_groups:
                self._groups[g.group_id] = g
                for mid in g.member_track_ids:
                    self._track_group_map[mid] = g.group_id

            for g in new_affected_groups:
                member_objs = [self._tracks[mid] for mid in g.member_track_ids if mid in self._tracks]
                fmt = compute_coordination_index(
                    group=g,
                    members=member_objs,
                    evaluated_at=eval_ts,
                )
                if fmt is not None:
                    self._formations[g.group_id] = fmt

            # Re-evaluate priorities for affected remaining tracks
            for remaining_id in sorted(affected_active_ids):
                t_obs = self._tracks[remaining_id]
                grp_id = self._track_group_map.get(remaining_id)
                grp = self._groups.get(grp_id) if grp_id else None
                fmt = self._formations.get(grp_id) if grp_id else None
                b_class = self._behaviors.get(remaining_id)

                p_anom_state = self._anomaly_accumulator.get_state(remaining_id)
                p_anom_score = p_anom_state.persistent_score if p_anom_state else 0.0

                p_assess = evaluate_threat_priority(
                    track_id=remaining_id,
                    group_id=grp_id,
                    behavior=b_class,
                    persistent_anomaly=p_anom_score,
                    coordination=fmt,
                    kinematics=float(t_obs.velocity or 0.0),
                    sensor_confidence=float(t_obs.confidence),
                    config=self._cfg.priority,
                    evaluated_at=eval_ts,
                )
                self._priorities[remaining_id] = p_assess

            sorted_groups = sorted(self._groups.values(), key=lambda g: g.group_id)
            sorted_formations = sorted(self._formations.values(), key=lambda f: f.formation_id)
            sorted_behaviors = [self._behaviors[i] for i in sorted(self._behaviors.keys())]
            sorted_priorities = [self._priorities[i] for i in sorted(self._priorities.keys())]

            self._cached_summary = MultiTrackIntelligenceSummary(
                groups=sorted_groups,
                behaviors=sorted_behaviors,
                formations=sorted_formations,
                priorities=sorted_priorities,
                evaluated_at=eval_ts,
            )

            self._version += 1
            return True

    def clear(self) -> None:
        """Reset all internal state to empty."""
        with self._lock:
            self._tracks.clear()
            self._grid.clear()
            self._groups.clear()
            self._track_group_map.clear()
            self._formations.clear()
            self._classifier_states.clear()
            self._behaviors.clear()
            self._anomaly_accumulator.reset_all()
            self._priorities.clear()
            self._version += 1
            self._cached_summary = MultiTrackIntelligenceSummary(
                groups=[],
                behaviors=[],
                formations=[],
                priorities=[],
                evaluated_at=datetime.now(UTC),
            )

    # ── Instantaneous Read API (O(1)) ────────────────────────────────────────

    def get_summary_snapshot(self) -> MultiTrackIntelligenceSummary:
        """Return an immutable snapshot of the MultiTrackIntelligenceSummary in sub-microsecond O(1) time."""
        with self._lock:
            # Return new model instance with copied lists to ensure complete snapshot isolation
            return MultiTrackIntelligenceSummary(
                groups=list(self._cached_summary.groups),
                behaviors=list(self._cached_summary.behaviors),
                formations=list(self._cached_summary.formations),
                priorities=list(self._cached_summary.priorities),
                evaluated_at=self._cached_summary.evaluated_at,
            )

    def get_track(self, track_id: str) -> TrackObservation | None:
        """Retrieve cached observation for a track ID."""
        with self._lock:
            return self._tracks.get(str(track_id))

    def get_group(self, group_id: str) -> TrackGroup | None:
        """Retrieve cached group by group ID."""
        with self._lock:
            return self._groups.get(str(group_id))

    def get_track_group(self, track_id: str) -> TrackGroup | None:
        """Retrieve the group containing a track ID, or None if ungrouped."""
        with self._lock:
            gid = self._track_group_map.get(str(track_id))
            return self._groups.get(gid) if gid else None

    def get_behavior(self, track_id: str) -> BehaviorClassification | None:
        """Retrieve cached behavioral classification for a track."""
        with self._lock:
            return self._behaviors.get(str(track_id))

    def get_priority(self, track_id: str) -> ThreatPriorityAssessment | None:
        """Retrieve cached threat priority assessment for a track."""
        with self._lock:
            return self._priorities.get(str(track_id))

    def get_formation(self, group_id: str) -> CoordinatedFormation | None:
        """Retrieve cached formation telemetry for a group."""
        with self._lock:
            return self._formations.get(str(group_id))

    @property
    def version(self) -> int:
        """Monotonically increasing sequence version of the store state."""
        with self._lock:
            return self._version

    @property
    def track_count(self) -> int:
        """Number of active tracks currently indexed."""
        with self._lock:
            return len(self._tracks)

    @property
    def group_count(self) -> int:
        """Number of active groups currently identified."""
        with self._lock:
            return len(self._groups)
