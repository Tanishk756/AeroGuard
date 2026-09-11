"""Stage S9 Multi-Autopilot Hardware Abstraction Layer REST API Routes."""

from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from app.schemas.simulation_platform import AutopilotType
from app.schemas.mission import CompiledMission
from app.simulation.core.autopilot_abstraction import (
    AutopilotCapability,
    AutopilotHealthStatus,
)
from app.simulation.core.process_manager import SimulationProcessManager
from app.simulation.core.mission_translator import MissionTranslator, MissionTranslationDiagnostic
from app.simulation.adapters.ardupilot import ArduPilotSITLAdapter
from app.simulation.adapters.px4 import PX4AutopilotAdapter
from app.schemas.simulation_platform import SimulationScenarioSpec

router = APIRouter(prefix="/simulation/autopilots", tags=["autopilots"])


class AutopilotValidationRequest(BaseModel):
    autopilot_type: AutopilotType = AutopilotType.ARDUPILOT


class MissionTranslationRequest(BaseModel):
    compiled_mission: CompiledMission
    target_autopilot: AutopilotType = AutopilotType.ARDUPILOT


@router.get("", response_model=List[Dict[str, Any]])
async def list_autopilots():
    """GET /api/v1/simulation/autopilots - List supported autopilots, capabilities, and readiness status."""
    dummy_spec = SimulationScenarioSpec(scenario_id="diagnostic", name="diagnostic")
    ardupilot_adapter = ArduPilotSITLAdapter(dummy_spec)
    px4_adapter = PX4AutopilotAdapter(dummy_spec)

    ardu_health = await ardupilot_adapter.check_health()
    px4_health = await px4_adapter.check_health()

    return [
        {
            "autopilot_type": "ARDUPILOT",
            "name": "ArduPilot (ArduCopter)",
            "capabilities": [c.value for c in ardupilot_adapter.get_capabilities()],
            "health": ardu_health.model_dump(),
        },
        {
            "autopilot_type": "PX4",
            "name": "PX4 Autopilot",
            "capabilities": [c.value for c in px4_adapter.get_capabilities()],
            "health": px4_health.model_dump(),
        },
        {
            "autopilot_type": "MOCK",
            "name": "Deterministic In-Memory Mock",
            "capabilities": [c.value for c in AutopilotCapability],
            "health": {
                "autopilot_type": "MOCK",
                "ready": True,
                "status": "READY",
                "connected": True,
                "environment_blocked": False,
            },
        },
    ]


@router.post("/validate", response_model=AutopilotHealthStatus)
async def validate_autopilot(payload: AutopilotValidationRequest):
    """POST /api/v1/simulation/autopilots/validate - Validate readiness for target autopilot."""
    dummy_spec = SimulationScenarioSpec(scenario_id="diagnostic", name="diagnostic")

    if payload.autopilot_type == AutopilotType.ARDUPILOT:
        adapter = ArduPilotSITLAdapter(dummy_spec)
        return await adapter.check_health()
    elif payload.autopilot_type == AutopilotType.PX4:
        adapter = PX4AutopilotAdapter(dummy_spec)
        return await adapter.check_health()
    elif payload.autopilot_type == AutopilotType.MOCK:
        return AutopilotHealthStatus(
            autopilot_type=AutopilotType.MOCK,
            ready=True,
            status="READY",
            connected=True,
            environment_blocked=False,
        )
    else:
        raise HTTPException(status_code=400, detail=f"Unknown autopilot type: '{payload.autopilot_type}'")


@router.post("/translate-mission", response_model=MissionTranslationDiagnostic)
def translate_mission_endpoint(payload: MissionTranslationRequest):
    """POST /api/v1/simulation/autopilots/translate-mission - Translate compiled mission to target autopilot format."""
    return MissionTranslator.translate(payload.compiled_mission, payload.target_autopilot)
