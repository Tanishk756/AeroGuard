"""Stage S12 Observational Swarm Replay Engine.

Allows step-by-step, time-synchronized scrubbing, seeking, and event navigation
over recorded simulation sessions. Strictly observational — isolated from live SITL control.
"""

from typing import Dict, List, Optional
from app.schemas.simulation_snapshot import SimulationSnapshot, SimulationReplayState
from app.simulation.core.simulation_recorder import SimulationRecorder


class SwarmReplayEngine:
    """Purely observational engine for replaying recorded multi-vehicle scenarios."""

    def __init__(self, recorder: SimulationRecorder):
        self.recorder: SimulationRecorder = recorder
        self.current_index: int = 0
        self.playback_status: str = "PAUSED"  # PLAYING, PAUSED, STOPPED
        self.playback_speed: float = 1.0

    def load_recorder(self, recorder: SimulationRecorder) -> None:
        """Load a new recording into the replay engine."""
        self.recorder = recorder
        self.current_index = 0
        self.playback_status = "PAUSED"
    def play(self) -> SimulationReplayState:
        """Start replay playback."""
        if self.recorder.snapshots:
            self.playback_status = "PLAYING"
        return self.get_replay_state()

    def pause(self) -> SimulationReplayState:
        """Pause replay playback."""
        self.playback_status = "PAUSED"
        return self.get_replay_state()

    def stop(self) -> SimulationReplayState:
        """Stop replay and reset cursor to beginning."""
        self.playback_status = "STOPPED"
        self.current_index = 0
        return self.get_replay_state()

    def set_speed(self, speed: float) -> SimulationReplayState:
        """Set playback speed multiplier (e.g. 0.5x, 1.0x, 2.0x, 4.0x)."""
        self.playback_speed = max(0.1, min(10.0, speed))
        return self.get_replay_state()

    def step(self, delta_steps: int = 1) -> Optional[SimulationSnapshot]:
        """Step playback cursor forward or backward by delta_steps."""
        if not self.recorder.snapshots:
            return None
        self.current_index = max(0, min(len(self.recorder.snapshots) - 1, self.current_index + delta_steps))
        return self.get_current_snapshot()

    def seek_time(self, sim_time_s: float) -> Optional[SimulationSnapshot]:
        """Seek directly to simulation timestamp in seconds."""
        if not self.recorder.snapshots:
            return None
        snap = self.recorder.get_snapshot_by_time(sim_time_s)
        if snap:
            self.current_index = self.recorder.snapshots.index(snap)
        return self.get_current_snapshot()

    def seek_tick(self, tick_count: int) -> Optional[SimulationSnapshot]:
        """Seek directly to snapshot at specific tick count."""
        if not self.recorder.snapshots:
            return None
        snap = self.recorder.get_snapshot_by_tick(tick_count)
        if snap:
            self.current_index = self.recorder.snapshots.index(snap)
        return self.get_current_snapshot()

    def jump_to_next_safety_event(self) -> Optional[SimulationSnapshot]:
        """Jump to the next recorded safety event in timeline."""
        events = self.recorder.event_index.get("safety_events", [])
        for idx in events:
            if idx > self.current_index:
                self.current_index = idx
                return self.get_current_snapshot()
        return self.get_current_snapshot()

    def jump_to_prev_safety_event(self) -> Optional[SimulationSnapshot]:
        """Jump to previous recorded safety event in timeline."""
        events = self.recorder.event_index.get("safety_events", [])
        for idx in reversed(events):
            if idx < self.current_index:
                self.current_index = idx
                return self.get_current_snapshot()
        return self.get_current_snapshot()

    def get_current_snapshot(self) -> Optional[SimulationSnapshot]:
        """Return snapshot at current playback cursor."""
        if not self.recorder.snapshots:
            return None
        return self.recorder.snapshots[self.current_index]

    def get_replay_state(self) -> SimulationReplayState:
        """Return comprehensive status of the replay engine."""
        meta = self.recorder.get_metadata()
        curr_snap = self.get_current_snapshot()
        curr_time = curr_snap.sim_time_seconds if curr_snap else 0.0
        curr_tick = curr_snap.tick_count if curr_snap else 0

        return SimulationReplayState(
            recording_id=self.recorder.recording_id,
            playback_status=self.playback_status,
            current_sim_time_s=curr_time,
            current_tick=curr_tick,
            total_ticks=meta.total_ticks,
            total_duration_s=meta.total_duration_s,
            playback_speed=self.playback_speed,
            current_snapshot=curr_snap,
        )
