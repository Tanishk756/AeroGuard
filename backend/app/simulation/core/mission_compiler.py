"""Stage S7 Mission Compiler Engine.

Compiles simulator-neutral mission item specifications into deterministic compiled mission objects with SHA256 checksums.
"""

import hashlib
import json
from typing import List
from app.models.mission import PersistentMission, PersistentMissionItem
from app.schemas.mission import CompiledMission, CompiledMissionItem, MissionItemSpec


class MissionCompiler:
    """Compiles canonical mission items into a deterministic CompiledMission with cryptographic SHA256 hash."""

    @classmethod
    def compile_mission(
        cls,
        mission_id: str,
        version: int,
        vehicle_id: str,
        scenario_id: str,
        items: List[MissionItemSpec],
        home_lat: float = 37.7749,
        home_lon: float = -122.4194,
    ) -> CompiledMission:
        sorted_items = sorted(items, key=lambda x: x.sequence)
        compiled_items: List[CompiledMissionItem] = []

        for item in sorted_items:
            lat = item.latitude if item.latitude is not None else home_lat
            lon = item.longitude if item.longitude is not None else home_lon

            compiled_items.append(
                CompiledMissionItem(
                    sequence=item.sequence,
                    command_type=item.command_type,
                    latitude=round(lat, 7),
                    longitude=round(lon, 7),
                    altitude_m=round(item.altitude_m, 2),
                    acceptance_radius_m=round(item.acceptance_radius_m, 2),
                    loiter_duration_s=round(item.loiter_duration_s, 2),
                )
            )

        # Compute Cryptographic SHA256 Hash
        dict_payload = {
            "mission_id": mission_id,
            "version": version,
            "vehicle_id": vehicle_id,
            "scenario_id": scenario_id,
            "items": [item.model_dump() for item in compiled_items],
        }
        json_bytes = json.dumps(dict_payload, sort_keys=True).encode("utf-8")
        compiled_hash = hashlib.sha256(json_bytes).hexdigest()

        return CompiledMission(
            mission_id=mission_id,
            version=version,
            vehicle_id=vehicle_id,
            scenario_id=scenario_id,
            items=compiled_items,
            compiled_mission_hash=compiled_hash,
        )
