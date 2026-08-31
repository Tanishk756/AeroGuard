"""Stage S7 Mission Execution & Telemetry Synchronization Service.

Manages mission execution state machine, MAVLink mission upload, and authoritative progress tracking.
"""

import math
import time
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session

from app.models.mission import PersistentMission, PersistentMissionRunSnapshot
from app.schemas.mission import CompiledMission, MissionProgress, MissionValidationDiagnostic, MissionItemSpec
from app.simulation.core.mission_validator import MissionValidationEngine
from app.simulation.core.mission_compiler import MissionCompiler
from app.simulation.core.ardupilot_mission_adapter import ArduPilotMissionAdapter
from app.core.telemetry import (
    MISSION_UPLOADS_TOTAL,
    MISSION_UPLOAD_FAILURES_TOTAL,
    MISSION_EXECUTIONS_TOTAL,
    MISSION_FAILURES_TOTAL,
    MISSION_COMPLETIONS_TOTAL,
)


class MissionExecutionService:
    """Controls real-time mission execution lifecycle and SITL telemetry progress tracking."""

    _active_progress: Dict[str, MissionProgress] = {}
    _mission_start_times: Dict[str, float] = {}

    @classmethod
    def prepare_and_validate(cls, mission_id: str, db: Session) -> MissionValidationDiagnostic:
        mission = db.get(PersistentMission, mission_id)
        if not mission:
            return MissionValidationDiagnostic(valid=False, errors=[f"Mission '{mission_id}' not found"])

        from app.schemas.mission import MissionCreate, MissionItemSpec
        items_spec = [
            MissionItemSpec(
                id=item.id,
                sequence=item.sequence,
                command_type=item.command_type,
                latitude=item.latitude,
                longitude=item.longitude,
                altitude_m=item.altitude_m,
                acceptance_radius_m=item.acceptance_radius_m,
                loiter_duration_s=item.loiter_duration_s,
            )
            for item in mission.items
        ]

        payload = MissionCreate(
            project_id=mission.project_id,
            vehicle_id=mission.vehicle_id,
            scenario_id=mission.scenario_id,
            name=mission.name,
            description=mission.description,
            items=items_spec,
        )

        diag = MissionValidationEngine.validate_mission_payload(payload, db)
        if diag.valid:
            mission.status = "VALIDATED"
            db.commit()
        return diag

    @classmethod
    def upload_mission(cls, mission_id: str, db: Session) -> bool:
        MISSION_UPLOADS_TOTAL.inc()
        mission = db.get(PersistentMission, mission_id)
        if not mission:
            MISSION_UPLOAD_FAILURES_TOTAL.inc()
            return False

        # 1. Compile Mission
        items_spec = [
            MissionItemSpec(
                sequence=item.sequence,
                command_type=item.command_type,
                latitude=item.latitude,
                longitude=item.longitude,
                altitude_m=item.altitude_m,
                acceptance_radius_m=item.acceptance_radius_m,
                loiter_duration_s=item.loiter_duration_s,
            )
            for item in mission.items
        ]
        compiled = MissionCompiler.compile_mission(
            mission_id=mission.id,
            version=mission.version,
            vehicle_id=mission.vehicle_id,
            scenario_id=mission.scenario_id,
            items=items_spec,
        )

        # 2. Translate to ArduPilot MAVLink items
        ardupilot_items = ArduPilotMissionAdapter.translate_to_ardupilot(compiled)

        # Mark as UPLOADED / READY
        mission.status = "READY"
        db.commit()

        # Initialize progress tracker
        total = len(compiled.items)
        cls._active_progress[mission_id] = MissionProgress(
            mission_id=mission_id,
            mission_status="READY",
            current_item_index=1,
            completed_items=0,
            total_items=total,
            progress_percentage=0.0,
            distance_to_target_m=0.0,
            mission_elapsed_time_s=0.0,
        )
        return True

    @classmethod
    def start_mission(cls, mission_id: str, db: Session) -> bool:
        MISSION_EXECUTIONS_TOTAL.inc()
        mission = db.get(PersistentMission, mission_id)
        if not mission or mission.status not in ("READY", "PAUSED"):
            MISSION_FAILURES_TOTAL.inc()
            return False

        mission.status = "RUNNING"
        db.commit()
        cls._mission_start_times[mission_id] = time.time()

        if mission_id in cls._active_progress:
            cls._active_progress[mission_id].mission_status = "RUNNING"

        return True

    @classmethod
    def pause_mission(cls, mission_id: str, db: Session) -> bool:
        mission = db.get(PersistentMission, mission_id)
        if not mission or mission.status != "RUNNING":
            return False

        mission.status = "PAUSED"
        db.commit()
        if mission_id in cls._active_progress:
            cls._active_progress[mission_id].mission_status = "PAUSED"
        return True

    @classmethod
    def resume_mission(cls, mission_id: str, db: Session) -> bool:
        return cls.start_mission(mission_id, db)

    @classmethod
    def abort_mission(cls, mission_id: str, db: Session) -> bool:
        mission = db.get(PersistentMission, mission_id)
        if not mission:
            return False

        mission.status = "ABORTED"
        db.commit()
        if mission_id in cls._active_progress:
            cls._active_progress[mission_id].mission_status = "ABORTED"
        return True

    @classmethod
    def update_progress_from_telemetry(
        cls,
        mission_id: str,
        current_lat: float,
        current_lon: float,
        current_alt: float,
        target_lat: float,
        target_lon: float,
        target_item_seq: int,
        total_items: int,
        db: Session,
    ) -> MissionProgress:
        # Distance calculation (Haversine formula approximation)
        dlat = math.radians(target_lat - current_lat)
        dlon = math.radians(target_lon - current_lon)
        a = math.sin(dlat / 2.0) ** 2 + math.cos(math.radians(current_lat)) * math.cos(math.radians(target_lat)) * math.sin(dlon / 2.0) ** 2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        dist_m = round(6371000.0 * c, 2)

        start_t = cls._mission_start_times.get(mission_id, time.time())
        elapsed_s = round(time.time() - start_t, 1)
        completed = max(0, target_item_seq - 1)
        pct = round((completed / float(total_items)) * 100.0, 1) if total_items > 0 else 0.0

        is_completed = target_item_seq >= total_items and dist_m < 3.0
        status_str = "COMPLETED" if is_completed else "RUNNING"

        if is_completed:
            mission = db.get(PersistentMission, mission_id)
            if mission and mission.status != "COMPLETED":
                mission.status = "COMPLETED"
                db.commit()
                MISSION_COMPLETIONS_TOTAL.inc()

        prog = MissionProgress(
            mission_id=mission_id,
            mission_status=status_str,
            current_item_index=target_item_seq,
            completed_items=completed,
            total_items=total_items,
            progress_percentage=pct,
            distance_to_target_m=dist_m,
            mission_elapsed_time_s=elapsed_s,
        )
        cls._active_progress[mission_id] = prog
        return prog

    @classmethod
    def get_progress(cls, mission_id: str) -> Optional[MissionProgress]:
        return cls._active_progress.get(mission_id)
