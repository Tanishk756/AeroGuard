"""MAVLink Message Normalizer and Telemetry Transport Engine.

Parses incoming MAVLink packets (ATTITUDE, GLOBAL_POSITION_INT, VFR_HUD, SYS_STATUS, GPS_RAW_INT, HEARTBEAT)
into normalized simulator-neutral VehicleState vectors.
"""

import math
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from app.schemas.simulation_platform import (
    VehicleState,
    PositionVector,
    VelocityVector,
    AttitudeVector,
    AngularVelocityVector,
    AccelerationVector,
    BatteryState,
    GPSState,
    LinkStatus,
)

logger = logging.getLogger("aeroguard.telemetry.mavlink")


class MAVLinkNormalizer:
    """Normalizes raw MAVLink message fields into a unified VehicleState instance."""

    def __init__(self, vehicle_id: str = "quad-x-001"):
        self.vehicle_id = vehicle_id
        self._current_state = VehicleState(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            sim_time_seconds=0.0,
            vehicle_id=vehicle_id,
        )

    def process_message(self, msg_type: str, msg_data: Dict[str, Any], sim_time: float = 0.0) -> VehicleState:
        """Update internal state snapshot from received MAVLink message fields."""
        now_str = datetime.now(timezone.utc).isoformat()
        self._current_state.timestamp_utc = now_str
        self._current_state.sim_time_seconds = sim_time

        if msg_type == "HEARTBEAT":
            # Map custom flight mode & armed state
            custom_mode = msg_data.get("custom_mode", 0)
            base_mode = msg_data.get("base_mode", 0)
            self._current_state.armed = bool(base_mode & 128)  # MAV_MODE_FLAG_SAFETY_ARMED
            self._current_state.flight_mode = f"MODE_{custom_mode}"

        elif msg_type == "ATTITUDE":
            roll = msg_data.get("roll", 0.0) * (180.0 / math.pi)
            pitch = msg_data.get("pitch", 0.0) * (180.0 / math.pi)
            yaw = msg_data.get("yaw", 0.0) * (180.0 / math.pi)
            self._current_state.attitude = AttitudeVector(
                roll_deg=round(roll, 2),
                pitch_deg=round(pitch, 2),
                yaw_deg=round(yaw, 2),
            )
            self._current_state.angular_velocity = AngularVelocityVector(
                roll_rate=round(msg_data.get("rollspeed", 0.0), 3),
                pitch_rate=round(msg_data.get("pitchspeed", 0.0), 3),
                yaw_rate=round(msg_data.get("yawspeed", 0.0), 3),
            )

        elif msg_type == "GLOBAL_POSITION_INT":
            lat = msg_data.get("lat", 0) / 1e7
            lon = msg_data.get("lon", 0) / 1e7
            alt_msl = msg_data.get("alt", 0) / 1000.0
            alt_rel = msg_data.get("relative_alt", 0) / 1000.0
            vx = msg_data.get("vx", 0) / 100.0
            vy = msg_data.get("vy", 0) / 100.0
            vz = msg_data.get("vz", 0) / 100.0
            ground_spd = math.sqrt(vx * vx + vy * vy)

            self._current_state.position = PositionVector(
                latitude=round(lat, 7),
                longitude=round(lon, 7),
                altitude_msl=round(alt_msl, 2),
                altitude_relative=round(alt_rel, 2),
            )
            self._current_state.velocity = VelocityVector(
                vx=round(vx, 2),
                vy=round(vy, 2),
                vz=round(vz, 2),
                ground_speed=round(ground_spd, 2),
            )

        elif msg_type == "SYS_STATUS":
            voltage = msg_data.get("voltage_battery", 14800) / 1000.0
            current = msg_data.get("current_battery", 0) / 100.0
            remaining = msg_data.get("battery_remaining", 100)
            self._current_state.battery = BatteryState(
                voltage_v=round(voltage, 2),
                current_a=round(current, 2),
                remaining_percent=float(remaining),
            )

        elif msg_type == "GPS_RAW_INT":
            self._current_state.gps = GPSState(
                fix_type=msg_data.get("fix_type", 3),
                satellites_visible=msg_data.get("satellites_visible", 12),
                hdop=msg_data.get("eph", 100) / 100.0,
                vdop=msg_data.get("epv", 100) / 100.0,
            )

        return self._current_state


class TelemetryTransport:
    """Telemetry Transport Abstraction reading MAVLink packets or Mock packets."""

    def __init__(self, vehicle_id: str = "quad-x-001"):
        self.normalizer = MAVLinkNormalizer(vehicle_id)
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, endpoint: str = "udpin:127.0.0.1:14550") -> bool:
        try:
            from pymavlink import mavutil  # noqa: F401
            logger.info(f"Connecting MAVLink transport to {endpoint}...")
            self._connected = True
            return True
        except ImportError:
            logger.warning("pymavlink package not installed; falling back to Mock transport mode")
            self._connected = False
            return False
