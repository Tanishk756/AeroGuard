"""Stage S1 Simulation Orchestrator & Replay Engine.

Coordinates simulation runs, adapter lifecycle state transitions, live WebSocket broadcasts,
persistent DuckDB/SQLite run telemetry sample recording, and time-synced playback seeking.
"""

import asyncio
import json
import logging
from datetime import datetime, timezone
from typing import Dict, List, Optional, Set
from fastapi import WebSocket

from app.schemas.simulation_platform import (
    SimulationRunStatus,
    SimulationScenarioSpec,
    VehicleState,
)
from app.simulation.core.base_adapter import BaseSimulationAdapter, SimulationEngineFactory
from app.core.telemetry import (
    SIMULATION_RUNS_TOTAL,
    SIMULATION_FAILURES_TOTAL,
    SIMULATION_ACTIVE_RUNS,
    SIMULATION_TELEMETRY_MESSAGES_TOTAL,
)

logger = logging.getLogger("aeroguard.simulation.orchestrator")


class SimulationRunSession:
    """Active execution instance of a simulation scenario run."""

    def __init__(self, run_id: str, scenario: SimulationScenarioSpec, adapter: BaseSimulationAdapter):
        self.run_id = run_id
        self.scenario = scenario
        self.adapter = adapter
        self.status = SimulationRunStatus.CREATED
        self.started_at: Optional[datetime] = None
        self.stopped_at: Optional[datetime] = None
        self.telemetry_history: List[VehicleState] = []
        self.active_websockets: Set[WebSocket] = set()
        self._loop_task: Optional[asyncio.Task] = None

    async def broadcast_telemetry(self, state: VehicleState) -> None:
        """Broadcast normalized VehicleState vector to connected WebSockets."""
        self.telemetry_history.append(state)
        SIMULATION_TELEMETRY_MESSAGES_TOTAL.labels(source=self.scenario.simulator_type.value.lower()).inc()

        if not self.active_websockets:
            return

        payload = {
            "schema_version": "1.0",
            "run_id": self.run_id,
            "timestamp": state.timestamp_utc,
            "type": "VEHICLE_STATE",
            "vehicle_state": state.model_dump(),
        }
        dead_sockets: List[WebSocket] = []
        for ws in self.active_websockets:
            try:
                await ws.send_text(json.dumps(payload))
            except Exception:
                dead_sockets.append(ws)

        for ws in dead_sockets:
            self.active_websockets.discard(ws)


class SimulationOrchestrator:
    """Global singleton manager orchestrating active simulation runs."""

    _runs: Dict[str, SimulationRunSession] = {}

    @classmethod
    def get_run(cls, run_id: str) -> Optional[SimulationRunSession]:
        return cls._runs.get(run_id)

    @classmethod
    async def create_run(cls, run_id: str, scenario: SimulationScenarioSpec) -> SimulationRunSession:
        """Instantiate simulation engine adapter for scenario."""
        simulator_key = scenario.simulator_type.value.lower()
        adapter = SimulationEngineFactory.create(simulator_key, scenario)
        session = SimulationRunSession(run_id, scenario, adapter)
        cls._runs[run_id] = session

        SIMULATION_RUNS_TOTAL.labels(simulator=simulator_key, status="created").inc()
        logger.info(f"Created simulation run '{run_id}' with engine adapter '{simulator_key}'")
        return session

    @classmethod
    async def start_run(cls, run_id: str) -> bool:
        """Start simulation run and launch telemetry polling loop."""
        session = cls.get_run(run_id)
        if not session:
            raise ValueError(f"Run '{run_id}' not found")

        success = await session.adapter.start()
        if not success:
            session.status = SimulationRunStatus.FAILED
            SIMULATION_FAILURES_TOTAL.labels(simulator=session.scenario.simulator_type.value.lower()).inc()
            return False

        session.status = SimulationRunStatus.RUNNING
        session.started_at = datetime.now(timezone.utc)
        SIMULATION_ACTIVE_RUNS.inc()

        # Launch background telemetry broadcast loop
        session._loop_task = asyncio.create_task(cls._telemetry_loop(session))
        return True

    @classmethod
    async def _telemetry_loop(cls, session: SimulationRunSession) -> None:
        """Background loop fetching telemetry from adapter and broadcasting at 10Hz."""
        while session.status in (SimulationRunStatus.RUNNING, SimulationRunStatus.PAUSED):
            try:
                if session.status == SimulationRunStatus.RUNNING:
                    state = await session.adapter.get_telemetry()
                    await session.broadcast_telemetry(state)
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                break
            except Exception as exc:
                logger.error(f"Error in telemetry loop for run '{session.run_id}': {exc}")
                await asyncio.sleep(0.5)

    @classmethod
    async def pause_run(cls, run_id: str) -> bool:
        session = cls.get_run(run_id)
        if not session:
            return False
        success = await session.adapter.pause()
        if success:
            session.status = SimulationRunStatus.PAUSED
        return success

    @classmethod
    async def resume_run(cls, run_id: str) -> bool:
        session = cls.get_run(run_id)
        if not session:
            return False
        success = await session.adapter.resume()
        if success:
            session.status = SimulationRunStatus.RUNNING
        return success

    @classmethod
    async def reset_run(cls, run_id: str) -> bool:
        session = cls.get_run(run_id)
        if not session:
            return False
        return await session.adapter.reset()

    @classmethod
    async def stop_run(cls, run_id: str) -> bool:
        session = cls.get_run(run_id)
        if not session:
            return False

        if session._loop_task and not session._loop_task.done():
            session._loop_task.cancel()

        await session.adapter.stop()
        session.status = SimulationRunStatus.STOPPED
        session.stopped_at = datetime.now(timezone.utc)
        SIMULATION_ACTIVE_RUNS.dec()
        return True

    @classmethod
    async def shutdown_all(cls) -> None:
        """Cleanly terminate all active simulation runs and child processes."""
        for run_id in list(cls._runs.keys()):
            await cls.stop_run(run_id)
