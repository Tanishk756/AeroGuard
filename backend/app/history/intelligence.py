"""Defensive intelligence historical persistence service.

AeroGuard Stage HI1 — Historical Intelligence Persistence, Swarm Replay & AI Analytics.

ARCHITECTURAL PRINCIPLES:
1. Non-blocking & Throttled: Snapshot persistence is throttled to approximately 1 Hz, while
   semantic group lifecycle changes and behavioral transitions are persisted immediately.
2. Failure Isolation: Database errors or transaction failures are caught, logged, and tracked
   via telemetry metrics without raising exceptions to the live telemetry path.
3. Determinism: Preserves exact timestamp metadata and deterministic JSON ordering.
"""

from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
import logging
import queue
import threading
from typing import Any
from uuid import uuid4

from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from ai.schemas import MultiTrackIntelligenceSummary, TrackGroup
from app.database.session import SessionLocal
from app.history.queries import normalize_timestamp
from app.models.intelligence_history import (
    BehaviorEventHistory,
    IntelligenceSnapshot,
    TrackGroupHistory,
)

logger = logging.getLogger(__name__)


class IntelligencePersistenceService:
    """Service managing buffered, throttled, and resilient persistence of AI intelligence history."""

    def __init__(
        self,
        snapshot_min_interval_seconds: float = 1.0,
        max_queue_size: int = 2000,
    ) -> None:
        self.snapshot_min_interval = timedelta(seconds=snapshot_min_interval_seconds)
        self.queue: queue.Queue[tuple[str, Any]] = queue.Queue(maxsize=max_queue_size)
        self._lock = threading.RLock()
        self._last_snapshot_time: datetime | None = None
        self._last_group_signatures: dict[str, str] = {}
        self._dropped_count: int = 0
        self._persisted_count: int = 0

    @property
    def dropped_count(self) -> int:
        """Total number of items dropped due to queue pressure or persistence failures."""
        with self._lock:
            return self._dropped_count

    @property
    def persisted_count(self) -> int:
        """Total number of intelligence history records committed to database."""
        with self._lock:
            return self._persisted_count

    def record_summary_snapshot(
        self,
        summary: MultiTrackIntelligenceSummary,
        force: bool = False,
        now: datetime | None = None,
    ) -> bool:
        """Enqueue a full MultiTrackIntelligenceSummary snapshot if throttle interval has elapsed."""
        eval_time = normalize_timestamp(now or summary.evaluated_at or datetime.now(UTC))

        with self._lock:
            if not force and self._last_snapshot_time is not None:
                if (eval_time - self._last_snapshot_time) < self.snapshot_min_interval:
                    return False

            peak_prio = 0.0
            if summary.priorities:
                peak_prio = max(p.priority_score for p in summary.priorities)

            payload = {
                "id": str(uuid4()),
                "timestamp": eval_time,
                "active_track_count": len(summary.priorities),
                "group_count": len(summary.groups),
                "formation_count": len(summary.formations),
                "peak_threat_score": round(float(peak_prio), 2),
                "summary_json": summary.model_dump(mode="json"),
                "created_at": datetime.now(UTC).replace(tzinfo=None),
            }

            try:
                self.queue.put_nowait(("snapshot", payload))
                self._last_snapshot_time = eval_time
                return True
            except queue.Full:
                self._dropped_count += 1
                logger.warning("[IntelligencePersistence] Snapshot dropped due to queue saturation")
                return False

    def record_group_history(
        self,
        group: TrackGroup,
        coordination_index: float | None = None,
        formation_type: str | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Enqueue a track group history record representing a group state or structural change."""
        ts = normalize_timestamp(now or group.created_at or datetime.now(UTC))

        # Change detection signature: group_id + sorted members + state
        sorted_members = sorted(group.member_track_ids)
        sig = f"{group.group_id}:{','.join(sorted_members)}:{group.behavioral_state}:{group.centroid_lat:.5f}:{group.centroid_lon:.5f}"

        with self._lock:
            if self._last_group_signatures.get(group.group_id) == sig:
                return False  # Unchanged group state

            payload = {
                "id": str(uuid4()),
                "group_id": group.group_id,
                "timestamp": ts,
                "member_track_ids": sorted_members,
                "member_count": len(sorted_members),
                "centroid_lat": group.centroid_lat,
                "centroid_lon": group.centroid_lon,
                "radius_meters": group.radius_meters,
                "behavioral_state": str(group.behavioral_state),
                "coordination_index": float(coordination_index) if coordination_index is not None else None,
                "formation_type": str(formation_type) if formation_type is not None else None,
                "created_at": datetime.now(UTC).replace(tzinfo=None),
            }

            try:
                self.queue.put_nowait(("group", payload))
                self._last_group_signatures[group.group_id] = sig
                return True
            except queue.Full:
                self._dropped_count += 1
                logger.warning("[IntelligencePersistence] Group history dropped due to queue saturation")
                return False

    def record_behavior_event(
        self,
        track_id: str,
        new_state: str,
        previous_state: str | None = None,
        duration_seconds: float = 0.0,
        confidence: float = 1.0,
        reasons: list[str] | None = None,
        now: datetime | None = None,
    ) -> bool:
        """Enqueue a behavioral classification transition event."""
        ts = normalize_timestamp(now or datetime.now(UTC))

        payload = {
            "id": str(uuid4()),
            "track_id": str(track_id),
            "timestamp": ts,
            "previous_state": str(previous_state) if previous_state else None,
            "new_state": str(new_state),
            "duration_seconds": max(0.0, float(duration_seconds)),
            "confidence": min(1.0, max(0.0, float(confidence))),
            "reasons": list(reasons or []),
            "created_at": datetime.now(UTC).replace(tzinfo=None),
        }

        with self._lock:
            try:
                self.queue.put_nowait(("behavior", payload))
                return True
            except queue.Full:
                self._dropped_count += 1
                logger.warning("[IntelligencePersistence] Behavior event dropped due to queue saturation")
                return False

    def flush(self, db: Session | None = None) -> int:
        """Drain all pending queued intelligence records and commit them to the database."""
        items: list[tuple[str, Any]] = []
        while True:
            try:
                items.append(self.queue.get_nowait())
            except queue.Empty:
                break

        if not items:
            return 0

        session = db or SessionLocal()
        close_session = db is None

        committed_count = 0
        try:
            for item_type, data in items:
                if item_type == "snapshot":
                    session.add(IntelligenceSnapshot(**data))
                elif item_type == "group":
                    session.add(TrackGroupHistory(**data))
                elif item_type == "behavior":
                    session.add(BehaviorEventHistory(**data))

            session.commit()
            committed_count = len(items)
            with self._lock:
                self._persisted_count += committed_count
            return committed_count
        except SQLAlchemyError as exc:
            session.rollback()
            with self._lock:
                self._dropped_count += len(items)
            logger.warning("[IntelligencePersistence] Failed to commit %d items to database: %s", len(items), exc)
            return 0
        finally:
            for _ in items:
                self.queue.task_done()
            if close_session:
                session.close()

    def clear(self) -> None:
        """Reset internal queues, caches, and metric counters."""
        with self._lock:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except (queue.Empty, ValueError):
                    break
            self._last_snapshot_time = None
            self._last_group_signatures.clear()
            self._dropped_count = 0
            self._persisted_count = 0


# Global singleton persistence service instance
_persistence_instance: IntelligencePersistenceService | None = None
_persistence_lock = threading.Lock()


def get_intelligence_persistence() -> IntelligencePersistenceService:
    """Retrieve the global singleton IntelligencePersistenceService instance."""
    global _persistence_instance
    if _persistence_instance is None:
        with _persistence_lock:
            if _persistence_instance is None:
                _persistence_instance = IntelligencePersistenceService()
    return _persistence_instance


def reset_intelligence_persistence() -> None:
    """Reset the global singleton persistence instance (used in test fixtures)."""
    global _persistence_instance
    with _persistence_lock:
        if _persistence_instance is not None:
            _persistence_instance.clear()
        _persistence_instance = None
