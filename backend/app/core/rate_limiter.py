"""Rate limiting store abstraction, sliding-window engine, and middleware integration."""

from abc import ABC, abstractmethod
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
import logging
import time

from fastapi import HTTPException, Request, Response

from app.core.config import Settings, get_settings
from app.core.ip import get_client_ip

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    allowed: bool
    limit: int
    remaining: int
    reset_seconds: int


class RateLimitStore(ABC):
    """Abstract rate limit store interface."""

    @abstractmethod
    def check_and_increment(self, key: str, max_requests: int, window_seconds: int) -> RateLimitResult:
        """Check if request under key exceeds limit within sliding window."""
        pass


class InMemoryRateLimitStore(RateLimitStore):
    """In-memory sliding window rate limit store for development and testing."""

    def __init__(self):
        # Key -> list of request timestamps (floats)
        self._hits: dict[str, list[float]] = defaultdict(list)

    def check_and_increment(self, key: str, max_requests: int, window_seconds: int) -> RateLimitResult:
        now = time.time()
        cutoff = now - window_seconds
        timestamps = self._hits[key]

        # Evict old hits outside sliding window
        self._hits[key] = [t for t in timestamps if t > cutoff]
        hits = self._hits[key]

        if len(hits) >= max_requests:
            oldest = hits[0]
            reset_seconds = max(1, int(oldest + window_seconds - now))
            return RateLimitResult(
                allowed=False,
                limit=max_requests,
                remaining=0,
                reset_seconds=reset_seconds,
            )

        hits.append(now)
        remaining = max_requests - len(hits)
        reset_seconds = window_seconds
        return RateLimitResult(
            allowed=True,
            limit=max_requests,
            remaining=remaining,
            reset_seconds=reset_seconds,
        )


class RedisRateLimitStore(RateLimitStore):
    """Redis-backed rate limit store for production multi-worker deployment."""

    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import redis
                self._client = redis.from_url(self.redis_url, socket_timeout=2.0)
            except Exception as exc:
                logger.error(f"[RATE_LIMITER] Redis connection initialization failed: {exc}")
                raise
        return self._client

    def check_and_increment(self, key: str, max_requests: int, window_seconds: int) -> RateLimitResult:
        try:
            client = self._get_client()
            now = time.time()
            cutoff = now - window_seconds
            pipe = client.pipeline()
            pipe.zremrangebyscore(key, 0, cutoff)
            pipe.zcard(key)
            pipe.zadd(key, {str(now): now})
            pipe.expire(key, window_seconds + 5)
            pipe.zrange(key, 0, 0, withscores=True)
            results = pipe.execute()

            current_count = results[1]
            if current_count >= max_requests:
                oldest_score = results[4][0][1] if results[4] else now
                reset_seconds = max(1, int(oldest_score + window_seconds - now))
                return RateLimitResult(
                    allowed=False,
                    limit=max_requests,
                    remaining=0,
                    reset_seconds=reset_seconds,
                )

            remaining = max_requests - current_count - 1
            return RateLimitResult(
                allowed=True,
                limit=max_requests,
                remaining=remaining,
                reset_seconds=window_seconds,
            )
        except Exception as exc:
            logger.error(f"[RATE_LIMITER] Redis rate limit check failed for key '{key}': {exc}")
            raise


class RateLimiterEngine:
    """Rate limiter facade evaluating policy string rate limits against selected store."""

    def __init__(self, settings: Settings | None = None):
        self.settings = settings or get_settings()
        self.store = self._init_store()

    def _init_store(self) -> RateLimitStore:
        if self.settings.rate_limit_storage_url:
            try:
                return RedisRateLimitStore(self.settings.rate_limit_storage_url)
            except Exception as exc:
                logger.warning(f"[RATE_LIMITER] Failed to create Redis store ({exc}), falling back to in-memory store.")
        return InMemoryRateLimitStore()

    @staticmethod
    def parse_rate_limit(policy_str: str) -> tuple[int, int]:
        """Parse rate limit string like '5/minute', '100/minute', '10/second', '1000/hour'."""
        try:
            count_str, unit_str = policy_str.strip().split("/")
            count = int(count_str)
            unit_map = {
                "second": 1,
                "sec": 1,
                "s": 1,
                "minute": 60,
                "min": 60,
                "m": 60,
                "hour": 3600,
                "h": 3600,
                "day": 86400,
                "d": 86400,
            }
            unit_lower = unit_str.lower()
            if unit_lower not in unit_map:
                raise ValueError(f"Unknown time unit '{unit_str}' in rate limit specification")
            return count, unit_map[unit_lower]
        except Exception as exc:
            logger.warning(f"[RATE_LIMITER] Invalid rate limit string '{policy_str}', defaulting to 100/minute: {exc}")
            return 100, 60

    def enforce_rate_limit(
        self,
        request: Request,
        key: str,
        policy_str: str,
        is_login: bool = False,
    ) -> RateLimitResult:
        """Enforce rate limit check for given key.

        On limit exceeded: raises HTTP 429 with Retry-After header.
        On store failure: respects rate_limit_fail_open policy (login protection always fails closed).
        """
        if not self.settings.rate_limiting_enabled:
            return RateLimitResult(allowed=True, limit=999999, remaining=999999, reset_seconds=0)

        max_requests, window_seconds = self.parse_rate_limit(policy_str)
        try:
            result = self.store.check_and_increment(key, max_requests, window_seconds)
        except Exception as exc:
            logger.error(f"[RATE_LIMITER] Store check error: {exc}")
            # Login rate limiting always fails closed for security protection
            if is_login or not self.settings.rate_limit_fail_open:
                result = RateLimitResult(
                    allowed=False,
                    limit=max_requests,
                    remaining=0,
                    reset_seconds=60,
                )
            else:
                return RateLimitResult(allowed=True, limit=max_requests, remaining=max_requests, reset_seconds=0)

        if not result.allowed:
            raise HTTPException(
                status_code=429,
                detail="Too Many Requests. Please slow down.",
                headers={
                    "Retry-After": str(result.reset_seconds),
                    "X-RateLimit-Limit": str(result.limit),
                    "X-RateLimit-Remaining": "0",
                    "X-RateLimit-Reset": str(result.reset_seconds),
                },
            )

        return result


_limiter_instance: RateLimiterEngine | None = None


def get_rate_limiter() -> RateLimiterEngine:
    global _limiter_instance
    if _limiter_instance is None:
        _limiter_instance = RateLimiterEngine()
    return _limiter_instance


def reset_rate_limiter() -> None:
    global _limiter_instance
    _limiter_instance = None
