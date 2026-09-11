"""Stage S10 Multi-Vehicle Swarm Mission Extension & Translator.

Translates high-level swarm directives into individual vehicle CompiledMission objects while
applying deterministic body-frame formation slot offsets to reference waypoints.
"""

from typing import Dict, List, Optional
from app.schemas.mission import CompiledMission, MissionItemSpec
from app.schemas.swarm import FormationConfiguration, SwarmConfiguration, SwarmRole
from app.simulation.core.formation_geometry import FormationGeometry
from app.simulation.core.mission_compiler import MissionCompiler


class SwarmMissionDirective:
    """High-level swarm flight mission command directive."""

    def __init__(
        self,
        command_type: str,  # TAKEOFF_ALL, FORMATION_WAYPOINT, HOLD_FORMATION, LAND_ALL
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        altitude_m: float = 10.0,
        heading_deg: float = 0.0,
        loiter_duration_s: float = 0.0,
        acceptance_radius_m: float = 2.0,
    ):
        self.command_type = command_type
        self.latitude = latitude
        self.longitude = longitude
        self.altitude_m = altitude_m
        self.heading_deg = heading_deg
        self.loiter_duration_s = loiter_duration_s
        self.acceptance_radius_m = acceptance_radius_m


class SwarmMissionTranslator:
    """Translates swarm-level directives into synchronized vehicle-specific CompiledMissions."""

    @classmethod
    def compile_swarm_mission(
        cls,
        swarm_config: SwarmConfiguration,
        scenario_id: str,
        directives: List[SwarmMissionDirective],
        ref_lat: float = 37.7749,
        ref_lon: float = -122.4194,
    ) -> Dict[str, CompiledMission]:
        """Compile synchronized vehicle missions for each member in the swarm.

        Returns:
            Dict[vehicle_id, CompiledMission]
        """
        # Generate formation slots for all members
        num_members = len(swarm_config.members)
        slots = FormationGeometry.generate_slots(
            formation_type=swarm_config.formation.formation_type,
            num_vehicles=num_members,
            spacing_m=swarm_config.formation.spacing_m,
            altitude_offset_m=swarm_config.formation.altitude_offset_m,
        )

        # Map member to slot
        member_slot_map = {}
        for member in swarm_config.members:
            member_slot_map[member.vehicle_id] = slots.get(
                member.slot_index,
                slots.get(0)
            )

        compiled_missions: Dict[str, CompiledMission] = {}

        for member in swarm_config.members:
            v_id = member.vehicle_id
            slot = member_slot_map[v_id]
            vehicle_specs: List[MissionItemSpec] = []
            seq = 1

            for directive in directives:
                cmd = directive.command_type

                if cmd == "TAKEOFF_ALL":
                    # All vehicles take off to directive altitude + slot z offset
                    alt = max(2.0, directive.altitude_m + slot.relative_offset_enu[2])
                    vehicle_specs.append(
                        MissionItemSpec(
                            sequence=seq,
                            command_type="TAKEOFF",
                            altitude_m=alt,
                            acceptance_radius_m=directive.acceptance_radius_m,
                        )
                    )
                elif cmd in ("FORMATION_WAYPOINT", "FORMATION_MOVE", "HOLD_FORMATION"):
                    # Leader target lat/lon
                    ref_waypoint_lat = directive.latitude if directive.latitude is not None else ref_lat
                    ref_waypoint_lon = directive.longitude if directive.longitude is not None else ref_lon

                    # Calculate ENU offset for follower slot relative to leader heading
                    enu_offset = FormationGeometry.body_offset_to_enu(
                        slot.relative_offset_enu,
                        directive.heading_deg,
                    )

                    v_lat, v_lon, v_alt = FormationGeometry.enu_to_geodetic(
                        ref_lat=ref_waypoint_lat,
                        ref_lon=ref_waypoint_lon,
                        ref_alt=directive.altitude_m,
                        enu_x=enu_offset[0],
                        enu_y=enu_offset[1],
                        enu_z=enu_offset[2],
                    )

                    c_type = "LOITER" if cmd == "HOLD_FORMATION" else "WAYPOINT"
                    vehicle_specs.append(
                        MissionItemSpec(
                            sequence=seq,
                            command_type=c_type,
                            latitude=v_lat,
                            longitude=v_lon,
                            altitude_m=v_alt,
                            acceptance_radius_m=directive.acceptance_radius_m,
                            loiter_duration_s=directive.loiter_duration_s,
                        )
                    )
                elif cmd == "LAND_ALL":
                    vehicle_specs.append(
                        MissionItemSpec(
                            sequence=seq,
                            command_type="LAND",
                            altitude_m=0.0,
                            acceptance_radius_m=directive.acceptance_radius_m,
                        )
                    )
                else:
                    # Fallback generic command
                    vehicle_specs.append(
                        MissionItemSpec(
                            sequence=seq,
                            command_type=cmd,
                            latitude=directive.latitude,
                            longitude=directive.longitude,
                            altitude_m=directive.altitude_m,
                            acceptance_radius_m=directive.acceptance_radius_m,
                            loiter_duration_s=directive.loiter_duration_s,
                        )
                    )
                seq += 1

            # Compile into single-vehicle CompiledMission
            compiled_missions[v_id] = MissionCompiler.compile_mission(
                mission_id=f"swarm-mission-{swarm_config.swarm_id}-{v_id}",
                version=1,
                vehicle_id=v_id,
                scenario_id=scenario_id,
                items=vehicle_specs,
                home_lat=ref_lat,
                home_lon=ref_lon,
            )

        return compiled_missions
