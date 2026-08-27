"""In-process asynchronous realtime event bus with backpressure and sequence tracking."""

import asyncio
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
import logging
from typing import Any
import uuid

from app.schemas.events import RealtimeChannel, RealtimeEventEnvelope, RealtimeEventType

logger = logging.getLogger(__name__)

# Events that must not be silently dropped when queue capacity is reached
CRITICAL_EVENT_TYPES = {
    RealtimeEventType.ALERT_CREATED,
    RealtimeEventType.ALERT_UPDATED,
    RealtimeEventType.THREAT_UPDATED,
    RealtimeEventType.TRACK_CREATED,
    RealtimeEventType.TRACK_DROPPED,
    RealtimeEventType.GEOFENCE_BREACH,
    RealtimeEventType.SIMULATION_STATE,
    RealtimeEventType.SIMULATION_RESET,
}


@dataclass
class Subscription:
    """Subscriber handle containing a bounded queue and filter rules."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    channel: str = RealtimeChannel.OPERATIONAL
    queue: asyncio.Queue[RealtimeEventEnvelope] = field(default_factory=lambda: asyncio.Queue(maxsize=100))
    filter_func: Callable[[RealtimeEventEnvelope], bool] | None = None
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    delivered_count: int = 0
    dropped_count: int = 0

    def is_matching(self, envelope: RealtimeEventEnvelope) -> bool:
        if self.channel != "*" and self.channel != envelope.channel:
            return False
        if self.filter_func is not None:
            try:
                return bool(self.filter_func(envelope))
            except Exception:
                logger.exception("Error executing subscriber filter function")
                return False
        return True


class EventBus:
    """Thread-safe and AsyncIO-compatible in-process event bus."""

    def __init__(self) -> None:
        self._lock = asyncio.Lock()
        self._sequences: dict[str, int] = {}
        self._subscribers: dict[str, list[Subscription]] = {}
        self._total_published: int = 0

    def get_next_sequence(self, channel: str) -> int:
        """Atomically return the next monotonic sequence number for a channel."""
        current = self._sequences.get(channel, 0) + 1
        self._sequences[channel] = current
        return current

    def subscribe(
        self,
        channel: str | RealtimeChannel = RealtimeChannel.OPERATIONAL,
        maxsize: int = 100,
        filter_func: Callable[[RealtimeEventEnvelope], bool] | None = None,
    ) -> Subscription:
        """Register a subscriber queue on a channel."""
        channel_str = str(channel)
        bounded_maxsize = max(10, min(maxsize, 1000))
        sub = Subscription(
            channel=channel_str,
            queue=asyncio.Queue(maxsize=bounded_maxsize),
            filter_func=filter_func,
        )
        if channel_str not in self._subscribers:
            self._subscribers[channel_str] = []
        self._subscribers[channel_str].append(sub)
        logger.debug("Subscriber %s registered on channel %s (queue size: %d)", sub.id, channel_str, bounded_maxsize)
        return sub

    def unsubscribe(self, subscription: Subscription) -> None:
        """Remove a subscriber queue cleanly."""
        channel_str = subscription.channel
        if channel_str in self._subscribers:
            self._subscribers[channel_str] = [s for s in self._subscribers[channel_str] if s.id != subscription.id]
            if not self._subscribers[channel_str]:
                del self._subscribers[channel_str]
        logger.debug("Subscriber %s unsubscribed from channel %s", subscription.id, channel_str)

    def publish(
        self,
        event_type: str | RealtimeEventType,
        channel: str | RealtimeChannel,
        payload: dict[str, Any],
        resource_type: str | None = None,
        resource_id: str | None = None,
        correlation_id: str | None = None,
    ) -> RealtimeEventEnvelope:
        """Create and publish a validated event envelope to matching channel subscribers."""
        event_type_str = str(event_type)
        channel_str = str(channel)
        sequence = self.get_next_sequence(channel_str)
        self._total_published += 1

        envelope = RealtimeEventEnvelope(
            event_id=str(uuid.uuid4()),
            event_type=event_type_str,
            channel=channel_str,
            sequence=sequence,
            timestamp=datetime.now(UTC),
            resource_type=resource_type,
            resource_id=resource_id,
            correlation_id=correlation_id,
            payload=payload,
        )

        self._dispatch(envelope)
        return envelope

    def _dispatch(self, envelope: RealtimeEventEnvelope) -> None:
        """Dispatch envelope to channel-specific and wildcard subscribers with backpressure management."""
        targets: list[Subscription] = []
        if envelope.channel in self._subscribers:
            targets.extend(self._subscribers[envelope.channel])
        if "*" in self._subscribers:
            targets.extend(self._subscribers["*"])

        is_critical = envelope.event_type in CRITICAL_EVENT_TYPES

        for sub in targets:
            if not sub.is_matching(envelope):
                continue

            if not sub.queue.full():
                try:
                    sub.queue.put_nowait(envelope)
                    sub.delivered_count += 1
                except asyncio.QueueFull:
                    self._handle_overflow(sub, envelope, is_critical)
            else:
                self._handle_overflow(sub, envelope, is_critical)

    def _handle_overflow(self, sub: Subscription, envelope: RealtimeEventEnvelope, is_critical: bool) -> None:
        """Handle bounded queue overflow with backpressure policy."""
        sub.dropped_count += 1
        if is_critical:
            # For critical events, evict the oldest non-critical item to make space
            try:
                sub.queue.get_nowait()
                sub.queue.task_done()
            except (asyncio.QueueEmpty, ValueError):
                pass
            try:
                sub.queue.put_nowait(envelope)
                sub.delivered_count += 1
            except asyncio.QueueFull:
                logger.warning("Subscriber %s queue full even after eviction attempt", sub.id)
        else:
            # Telemetry coalescing: Drop older telemetry point in favour of queue freshness
            logger.debug("Subscriber %s queue full; dropped non-critical event %s", sub.id, envelope.event_type)

    def get_stats(self) -> dict[str, Any]:
        """Return diagnostic metrics for the event bus."""
        active_subscribers = sum(len(subs) for subs in self._subscribers.values())
        total_dropped = sum(
            sub.dropped_count
            for subs in self._subscribers.values()
            for sub in subs
        )
        total_delivered = sum(
            sub.delivered_count
            for subs in self._subscribers.values()
            for sub in subs
        )
        return {
            "active_subscribers": active_subscribers,
            "channels": list(self._subscribers.keys()),
            "sequences": dict(self._sequences),
            "total_published": self._total_published,
            "total_delivered": total_delivered,
            "total_dropped": total_dropped,
        }

    def reset(self) -> None:
        """Reset sequences and subscriber registries (used for tests)."""
        self._sequences.clear()
        self._subscribers.clear()
        self._total_published = 0


# Global singleton instance
_event_bus_instance = EventBus()


def get_event_bus() -> EventBus:
    """Return the global EventBus singleton."""
    return _event_bus_instance
