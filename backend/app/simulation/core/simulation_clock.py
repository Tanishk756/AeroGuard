"""Stage S12 Deterministic Simulation Clock Engine.

Provides a canonical, deterministic simulation clock supporting Realtime, Accelerated,
Paused, Single-Step, and Fixed-Timestep deterministic modes.
"""

from enum import Enum
import time
from typing import Optional


class ClockMode(str, Enum):
    REALTIME = "REALTIME"
    ACCELERATED = "ACCELERATED"
    PAUSED = "PAUSED"
    SINGLE_STEP = "SINGLE_STEP"
    DETERMINISTIC = "DETERMINISTIC"


class SimulationClock:
    """Canonical simulation clock governing all simulation subsystem ticks."""

    def __init__(
        self,
        dt_seconds: float = 0.1,
        mode: ClockMode = ClockMode.DETERMINISTIC,
        speed_multiplier: float = 1.0,
        random_seed: int = 42,
    ):
        self.dt_seconds: float = dt_seconds
        self.mode: ClockMode = mode
        self.speed_multiplier: float = speed_multiplier
        self.random_seed: int = random_seed

        self.sim_time_seconds: float = 0.0
        self.tick_count: int = 0
        self.is_running: bool = False
        self.start_wall_time: Optional[float] = None
        self.last_wall_time: Optional[float] = None

    def start(self, initial_sim_time: float = 0.0) -> None:
        """Start or restart simulation clock."""
        self.sim_time_seconds = initial_sim_time
        self.tick_count = int(initial_sim_time / self.dt_seconds)
        self.is_running = True
        self.start_wall_time = time.time()
        self.last_wall_time = self.start_wall_time

    def pause(self) -> None:
        """Pause simulation clock."""
        self.is_running = False
        self.mode = ClockMode.PAUSED

    def resume(self) -> None:
        """Resume simulation clock."""
        self.is_running = True
        self.last_wall_time = time.time()
        if self.mode == ClockMode.PAUSED:
            self.mode = ClockMode.DETERMINISTIC

    def reset(self) -> None:
        """Reset simulation clock to zero."""
        self.sim_time_seconds = 0.0
        self.tick_count = 0
        self.is_running = False
        self.start_wall_time = None
        self.last_wall_time = None

    def tick(self) -> float:
        """Advance simulation clock by exactly dt_seconds.

        Returns:
            Updated sim_time_seconds.
        """
        if not self.is_running and self.mode != ClockMode.SINGLE_STEP:
            return self.sim_time_seconds

        self.tick_count += 1
        self.sim_time_seconds = round(self.tick_count * self.dt_seconds, 6)

        if self.mode == ClockMode.SINGLE_STEP:
            self.is_running = False
            self.mode = ClockMode.PAUSED

        return self.sim_time_seconds

    def step(self, count: int = 1) -> float:
        """Advance simulation clock by specified number of single steps."""
        for _ in range(count):
            self.tick_count += 1
            self.sim_time_seconds = round(self.tick_count * self.dt_seconds, 6)
        self.is_running = False
        self.mode = ClockMode.PAUSED
        return self.sim_time_seconds

    def seek(self, target_sim_time: float) -> float:
        """Seek simulation clock directly to target simulation time."""
        target_sim_time = max(0.0, target_sim_time)
        self.tick_count = int(round(target_sim_time / self.dt_seconds))
        self.sim_time_seconds = round(self.tick_count * self.dt_seconds, 6)
        return self.sim_time_seconds
