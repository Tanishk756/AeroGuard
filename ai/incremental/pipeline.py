"""Defensive intelligence pipeline coordinating incremental state, event publishing, and REST queries.

AeroGuard Stage AI3-D — Event-Driven Telemetry & REST Route Acceleration.

ARCHITECTURE
------------
1. Authoritative in-memory state: IncrementalIntelligenceStore.
2. Startup bootstrap: Loads initial active tracks from PostgreSQL/SQLite database into memory.
3. Event-driven track lifecycle: Detections and track updates incrementally mutate store state.
4. Deterministic change detection: Granular and summary events published only when state changes.
5. Instantaneous REST queries: GET /api/v1/intelligence/summary reads directly from the store in O(1) time.
"""

from collections.abc import Sequence
from datetime import UTC, datetime
import logging
import threading
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.correlation.grouping import to_track_observation
from ai.incremental.store import IncrementalIntelligenceStore, IncrementalStoreConfig
from ai.schemas import (
    BehaviorClassification,
    CoordinatedFormation,
    MultiTrackIntelligenceSummary,
    ThreatPriorityAssessment,
    TrackGroup,
)
from app.core.events import get_event_bus
from app.database.session import SessionLocal
from app.models.track import Track, TrackState
from app.schemas.events import RealtimeChannel, RealtimeEventType

logger = logging.getLogger(__name__)

PRIORITY_LEVEL_ORDER = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3,
}


class IntelligencePipeline:
    """Singleton service orchestrating incremental defensive intelligence state and telemetry."""

    def __init__(self, store: IncrementalIntelligenceStore | None = None) -> None:
        self._store = store or IncrementalIntelligenceStore()
        self._bootstrapped: bool = False
        self._lock = threading.RLock()

        # Cache for change detection: track_id / group_id -> previous state summary
        self._last_priority_scores: dict[str, float] = {}
        self._last_priority_levels: dict[str, str] = {}
        self._last_behavior_states: dict[str, str] = {}
        self._last_group_members: dict[str, list[str]] = {}

    @property
    def store(self) -> IncrementalIntelligenceStore:
        """Direct read access to the underlying IncrementalIntelligenceStore."""
        return self._store

    @property
    def is_bootstrapped(self) -> bool:
        """Whether the pipeline has completed initial bootstrap from active database tracks."""
        with self._lock:
            return self._bootstrapped

    def bootstrap_from_database(self, db: Session | None = None) -> int:
        """Load active tracks from database into the incremental intelligence store."""
        with self._lock:
            session = db or SessionLocal()
            close_session = db is None
            try:
                stmt = select(Track).where(
                    Track.state.in_([TrackState.ACTIVE, TrackState.NEW, TrackState.STALE])
                )
                active_tracks = list(session.scalars(stmt).all())
                observations = [to_track_observation(t) for t in active_tracks]

                if observations:
                    self._store.update_tracks_batch(observations)
                else:
                    self._store.clear()

                self._bootstrapped = True
                logger.info(
                    "[IntelligencePipeline] Bootstrapped %d active tracks into in-memory store",
                    len(observations),
                )
                return len(observations)
            finally:
                if close_session:
                    session.close()

    def process_track_update(
        self,
        track_or_dict: Any,
        instantaneous_anomaly_score: float | None = None,
        publish_events: bool = True,
        now: datetime | None = None,
    ) -> ThreatPriorityAssessment:
        """Incrementally update track in store and publish granular & summary events upon state change."""
        with self._lock:
            # Auto-mark bootstrapped if not explicitly run
            if not self._bootstrapped:
                self._bootstrapped = True

            obs = to_track_observation(track_or_dict)
            tid = obs.id

            # Capture prior state for change detection
            prev_score = self._last_priority_scores.get(tid)
            prev_level = self._last_priority_levels.get(tid)
            prev_bstate = self._last_behavior_states.get(tid)
            prev_grp = self._store.get_track_group(tid)
            prev_grp_id = prev_grp.group_id if prev_grp else None

            # Mutate store state
            priority = self._store.update_track(
                observation=obs,
                instantaneous_anomaly_score=instantaneous_anomaly_score,
                now=now,
            )

            # Retrieve updated entities
            curr_b = self._store.get_behavior(tid)
            curr_grp = self._store.get_track_group(tid)
            curr_grp_id = curr_grp.group_id if curr_grp else None

            # Record latest states
            self._last_priority_scores[tid] = priority.priority_score
            self._last_priority_levels[tid] = priority.priority_level
            if curr_b:
                self._last_behavior_states[tid] = curr_b.state.value

            # Change detection checks
            priority_changed = (
                prev_score is None
                or abs(prev_score - priority.priority_score) >= 0.1
                or prev_level != priority.priority_level
            )
            behavior_changed = (
                curr_b is not None
                and (prev_bstate is None or prev_bstate != curr_b.state.value)
            )
            group_changed = (
                (prev_grp_id != curr_grp_id)
                or (
                    curr_grp is not None
                    and self._last_group_members.get(curr_grp_id) != curr_grp.member_track_ids
                )
            )

            if curr_grp:
                self._last_group_members[curr_grp.group_id] = list(curr_grp.member_track_ids)
            elif prev_grp_id and prev_grp_id in self._last_group_members:
                self._last_group_members.pop(prev_grp_id, None)

            # Stage HI1: Record historical intelligence persistence
            try:
                from app.history.intelligence import get_intelligence_persistence

                persistence = get_intelligence_persistence()
                if group_changed and curr_grp:
                    curr_fmt = self._store.get_formation(curr_grp.group_id)
                    persistence.record_group_history(
                        group=curr_grp,
                        coordination_index=curr_fmt.synchronization_index if curr_fmt else None,
                        formation_type=getattr(curr_fmt, "formation_type", None),
                        now=now,
                    )

                if behavior_changed and curr_b:
                    persistence.record_behavior_event(
                        track_id=tid,
                        new_state=curr_b.state.value,
                        previous_state=prev_bstate,
                        duration_seconds=curr_b.duration_seconds,
                        confidence=curr_b.confidence,
                        reasons=curr_b.contributing_factors or [curr_b.reason],
                        now=now,
                    )

                if priority_changed or behavior_changed or group_changed:
                    persistence.record_summary_snapshot(
                        summary=self._store.get_summary_snapshot(),
                        force=False,
                        now=now,
                    )
            except Exception as persist_err:
                logger.debug(f"[IntelligencePipeline] Non-blocking persistence enqueue skipped: {persist_err}")

            if publish_events:
                bus = get_event_bus()

                if priority_changed:
                    bus.publish(
                        event_type=RealtimeEventType.AI_PRIORITY,
                        channel=RealtimeChannel.OPERATIONAL,
                        payload=priority.model_dump(mode="json"),
                        resource_type="threat_priority",
                        resource_id=tid,
                    )

                if behavior_changed and curr_b:
                    bus.publish(
                        event_type=RealtimeEventType.AI_BEHAVIOR,
                        channel=RealtimeChannel.OPERATIONAL,
                        payload=curr_b.model_dump(mode="json"),
                        resource_type="behavior_classification",
                        resource_id=tid,
                    )

                if group_changed and curr_grp:
                    bus.publish(
                        event_type=RealtimeEventType.AI_GROUP,
                        channel=RealtimeChannel.OPERATIONAL,
                        payload=curr_grp.model_dump(mode="json"),
                        resource_type="track_group",
                        resource_id=curr_grp.group_id,
                    )

                # Broadcast coherent multi-track summary when any derived telemetry changed
                if priority_changed or behavior_changed or group_changed:
                    snap = self._store.get_summary_snapshot()
                    bus.publish(
                        event_type=RealtimeEventType.AI_SUMMARY,
                        channel=RealtimeChannel.OPERATIONAL,
                        payload=snap.model_dump(mode="json"),
                        resource_type="multi_track_intelligence",
                        resource_id="summary",
                    )

            return priority

    def process_track_removal(
        self,
        track_id: str,
        publish_events: bool = True,
        now: datetime | None = None,
    ) -> bool:
        """Remove a track from store, clean up cached states, and publish update event."""
        tid = str(track_id)
        with self._lock:
            dropped = self._store.drop_track(tid, now=now)
            if dropped:
                self._last_priority_scores.pop(tid, None)
                self._last_priority_levels.pop(tid, None)
                self._last_behavior_states.pop(tid, None)

                # Stage HI1: Record historical summary snapshot on track removal
                try:
                    from app.history.intelligence import get_intelligence_persistence

                    get_intelligence_persistence().record_summary_snapshot(
                        summary=self._store.get_summary_snapshot(),
                        force=False,
                        now=now,
                    )
                except Exception as persist_err:
                    logger.debug(f"[IntelligencePipeline] Removal persistence enqueue skipped: {persist_err}")

                if publish_events:
                    bus = get_event_bus()
                    snap = self._store.get_summary_snapshot()
                    bus.publish(
                        event_type=RealtimeEventType.AI_SUMMARY,
                        channel=RealtimeChannel.OPERATIONAL,
                        payload=snap.model_dump(mode="json"),
                        resource_type="multi_track_intelligence",
                        resource_id="summary",
                    )
            return dropped

    def get_snapshot(
        self,
        db: Session | None = None,
        track_id: str | None = None,
        group_id: str | None = None,
        min_priority_level: str | None = None,
        min_priority_score: float | None = None,
    ) -> MultiTrackIntelligenceSummary:
        """Retrieve the cached defensive intelligence summary snapshot with instantaneous in-memory filtering."""
        with self._lock:
            if db is not None:
                stmt = select(Track).where(
                    Track.state.in_([TrackState.ACTIVE, TrackState.NEW, TrackState.STALE])
                )
                db_tracks = list(db.scalars(stmt).all())
                db_track_ids = {t.id for t in db_tracks}
                store_track_ids = set(self._store._tracks.keys())

                if not self._bootstrapped or db_track_ids != store_track_ids:
                    obs_list = [to_track_observation(t) for t in db_tracks]
                    if obs_list:
                        self._store.update_tracks_batch(obs_list)
                    else:
                        self._store.clear()
                    self._bootstrapped = True
            elif not self._bootstrapped and self._store.track_count == 0:
                self.bootstrap_from_database()
            else:
                self._bootstrapped = True

            summary = self._store.get_summary_snapshot()

            groups = summary.groups
            formations = summary.formations
            behaviors = summary.behaviors
            priorities = summary.priorities

            # Apply in-memory filters without mutating cached objects
            if track_id:
                groups = [g for g in groups if track_id in g.member_track_ids]
                formations = [f for f in formations if track_id in f.member_track_ids]
                behaviors = [b for b in behaviors if b.track_id == track_id]
                priorities = [p for p in priorities if p.track_id == track_id]

            if group_id:
                groups = [g for g in groups if g.group_id == group_id]
                formations = [f for f in formations if f.group_id == group_id]
                member_ids = {mid for g in groups for mid in g.member_track_ids}
                behaviors = [b for b in behaviors if b.track_id in member_ids]
                priorities = [p for p in priorities if p.track_id in member_ids]

            if min_priority_score is not None:
                priorities = [p for p in priorities if p.priority_score >= min_priority_score]

            if min_priority_level:
                target_rank = PRIORITY_LEVEL_ORDER.get(min_priority_level.upper(), 0)
                priorities = [
                    p for p in priorities
                    if PRIORITY_LEVEL_ORDER.get(p.priority_level, 0) >= target_rank
                ]

            return MultiTrackIntelligenceSummary(
                groups=groups,
                behaviors=behaviors,
                formations=formations,
                priorities=priorities,
                evaluated_at=summary.evaluated_at,
            )

    def reset(self) -> None:
        """Reset internal store and pipeline tracking state."""
        with self._lock:
            self._store.clear()
            self._bootstrapped = False
            self._last_priority_scores.clear()
            self._last_priority_levels.clear()
            self._last_behavior_states.clear()
            self._last_group_members.clear()

            try:
                from app.history.intelligence import get_intelligence_persistence

                get_intelligence_persistence().clear()
            except Exception:
                pass


# Global pipeline singleton
_pipeline_instance: IntelligencePipeline | None = None
_pipeline_lock = threading.Lock()


def get_intelligence_pipeline() -> IntelligencePipeline:
    """Retrieve the global singleton IntelligencePipeline instance."""
    global _pipeline_instance
    if _pipeline_instance is None:
        with _pipeline_lock:
            if _pipeline_instance is None:
                _pipeline_instance = IntelligencePipeline()
    return _pipeline_instance


def reset_intelligence_pipeline() -> None:
    """Reset the global singleton pipeline instance (used in test fixtures)."""
    global _pipeline_instance
    with _pipeline_lock:
        if _pipeline_instance is not None:
            _pipeline_instance.reset()
        _pipeline_instance = None
