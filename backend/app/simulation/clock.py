"""Deterministic virtual simulation clock without wall-clock dependencies."""

from datetime import UTC, datetime, timedelta


class SimulationClock:
    def __init__(
        self,
        start_time: datetime | None = None,
        tick_rate_hz: float = 1.0,
    ):
        if tick_rate_hz <= 0:
            raise ValueError("tick_rate_hz must be positive")

        if start_time is None:
            self._start_time = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        elif start_time.tzinfo is None:
            self._start_time = start_time.replace(tzinfo=UTC)
        else:
            self._start_time = start_time.astimezone(UTC)

        self._tick_rate_hz = float(tick_rate_hz)
        self._dt_seconds = 1.0 / self._tick_rate_hz
        self._current_time = self._start_time
        self._tick_count = 0
        self._is_paused = False
        self._is_stopped = False

    @property
    def start_time(self) -> datetime:
        return self._start_time

    @property
    def current_time(self) -> datetime:
        return self._current_time

    @property
    def tick_count(self) -> int:
        return self._tick_count

    @property
    def tick_rate_hz(self) -> float:
        return self._tick_rate_hz

    @property
    def dt_seconds(self) -> float:
        return self._dt_seconds

    @property
    def is_paused(self) -> bool:
        return self._is_paused

    @property
    def is_stopped(self) -> bool:
        return self._is_stopped

    @property
    def is_running(self) -> bool:
        return not self._is_paused and not self._is_stopped

    def step(self, ticks: int = 1) -> tuple[datetime, int]:
        """Advance the simulation clock deterministically by N ticks."""
        if ticks < 1:
            raise ValueError("ticks must be at least 1")
        if self._is_stopped:
            raise RuntimeError("Cannot step a stopped simulation clock")

        self._tick_count += ticks
        self._current_time = self._start_time + timedelta(seconds=self._tick_count * self._dt_seconds)
        return self._current_time, self._tick_count

    def pause(self) -> None:
        self._is_paused = True

    def resume(self) -> None:
        if self._is_stopped:
            raise RuntimeError("Cannot resume a stopped simulation clock")
        self._is_paused = False

    def stop(self) -> None:
        self._is_stopped = True
        self._is_paused = False

    def reset(self) -> None:
        """Reset the clock back to its initial start time and zero tick count."""
        self._current_time = self._start_time
        self._tick_count = 0
        self._is_paused = False
        self._is_stopped = False
