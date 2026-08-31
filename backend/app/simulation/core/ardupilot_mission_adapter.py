"""Stage S7 ArduPilot SITL Mission Adapter Engine.

Translates CompiledMission specifications into ArduCopter-compatible MAVLink MAV_CMD mission item packets.
"""

from typing import List
from app.schemas.mission import CompiledMission, ArduPilotMissionItem


# MAVLink Command Constants
MAV_CMD_NAV_WAYPOINT = 16
MAV_CMD_NAV_LOITER_TIME = 19
MAV_CMD_NAV_RETURN_TO_LAUNCH = 20
MAV_CMD_NAV_LAND = 21
MAV_CMD_NAV_TAKEOFF = 22
MAV_FRAME_GLOBAL_RELATIVE_ALT = 3


class ArduPilotMissionAdapter:
    """Translates CompiledMission to ArduCopter MAVLink mission representation."""

    @classmethod
    def translate_to_ardupilot(cls, compiled: CompiledMission) -> List[ArduPilotMissionItem]:
        ardupilot_items: List[ArduPilotMissionItem] = []

        for idx, item in enumerate(compiled.items):
            seq = idx
            lat_int = int(item.latitude * 1e7)
            lon_int = int(item.longitude * 1e7)

            if item.command_type == "TAKEOFF":
                cmd = MAV_CMD_NAV_TAKEOFF
                p1 = 0.0
                p2 = 0.0
            elif item.command_type == "WAYPOINT":
                cmd = MAV_CMD_NAV_WAYPOINT
                p1 = 0.0
                p2 = item.acceptance_radius_m
            elif item.command_type == "LOITER":
                cmd = MAV_CMD_NAV_LOITER_TIME
                p1 = item.loiter_duration_s
                p2 = item.acceptance_radius_m
            elif item.command_type == "RETURN_TO_HOME":
                cmd = MAV_CMD_NAV_RETURN_TO_LAUNCH
                p1 = 0.0
                p2 = 0.0
            elif item.command_type == "LAND":
                cmd = MAV_CMD_NAV_LAND
                p1 = 0.0
                p2 = 0.0
            else:
                cmd = MAV_CMD_NAV_WAYPOINT
                p1 = 0.0
                p2 = item.acceptance_radius_m

            ardupilot_items.append(
                ArduPilotMissionItem(
                    seq=seq,
                    frame=MAV_FRAME_GLOBAL_RELATIVE_ALT,
                    command=cmd,
                    current=1 if idx == 0 else 0,
                    autocontinue=1,
                    param1=p1,
                    param2=p2,
                    param3=0.0,
                    param4=0.0,
                    x_lat=lat_int,
                    y_lon=lon_int,
                    z_alt=item.altitude_m,
                )
            )

        return ardupilot_items
