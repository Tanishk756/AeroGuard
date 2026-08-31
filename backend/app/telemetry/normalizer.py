"""MAVLink Message Normalizer and UDP Telemetry Transport Engine.

Parses incoming MAVLink packets (ATTITUDE, GLOBAL_POSITION_INT, VFR_HUD, SYS_STATUS, GPS_RAW_INT, HEARTBEAT)
into normalized simulator-neutral VehicleState vectors with numerical sanity checks.
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
    """Normalizes raw MAVLink message fields into a unified VehicleState instance with numerical validation."""

    def __init__(self, vehicle_id: str = "quad-x-001"):
        self.vehicle_id = vehicle_id
        self._current_state = VehicleState(
            timestamp_utc=datetime.now(timezone.utc).isoformat(),
            sim_time_seconds=0.0,
            vehicle_id=vehicle_id,
        )
        self.packet_counts: Dict[str, int] = {
            "HEARTBEAT": 0,
            "ATTITUDE": 0,
            "GLOBAL_POSITION_INT": 0,
            "SYS_STATUS": 0,
            "GPS_RAW_INT": 0,
        }

    def process_message(self, msg_type: str, msg_data: Dict[str, Any], sim_time: float = 0.0) -> Optional[VehicleState]:
        """Update internal state snapshot from received MAVLink message fields after sanity checking."""
        if msg_type in self.packet_counts:
            self.packet_counts[msg_type] += 1

        now_str = datetime.now(timezone.utc).isoformat()
        self._current_state.timestamp_utc = now_str
        self._current_state.sim_time_seconds = sim_time

        if msg_type == "HEARTBEAT":
            custom_mode = msg_data.get("custom_mode", 0)
            base_mode = msg_data.get("base_mode", 0)
            self._current_state.armed = bool(base_mode & 128)
            self._current_state.flight_mode = f"MODE_{custom_mode}"

        elif msg_type == "ATTITUDE":
            roll = msg_data.get("roll", 0.0) * (180.0 / math.pi)
            pitch = msg_data.get("pitch", 0.0) * (180.0 / math.pi)
            yaw = msg_data.get("yaw", 0.0) * (180.0 / math.pi)

            # Numerical Sanity Verification
            if not (math.isfinite(roll) and math.isfinite(pitch) and math.isfinite(yaw)):
                logger.warning("Rejected malformed ATTITUDE packet containing non-finite values")
                return None

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

            # Latitude [-90, 90] & Longitude [-180, 180] Sanity Check
            if not (-90.0 <= lat <= 90.0 and -180.0 <= lon <= 180.0):
                logger.warning(f"Rejected out-of-bounds GPS coordinate: lat={lat}, lon={lon}")
                return None

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
    """Telemetry Transport Abstraction managing UDP sockets or mock fallback connections."""

    def __init__(self, vehicle_id: str = "quad-x-001"):
        self.normalizer = MAVLinkNormalizer(vehicle_id)
        self._connected = False
        self._connection: Optional[Any] = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    def connect(self, endpoint: str = "udpin:127.0.0.1:14550") -> bool:
        """Attempt socket binding via pymavlink to specified UDP endpoint."""
        try:
            from pymavlink import mavutil
            logger.info(f"Binding MAVLink UDP socket transport to {endpoint}...")
            self._connection = mavutil.mavlink_connection(endpoint)
            self._connected = True
            return True
        except Exception as exc:
            logger.warning(f"MAVLink socket binding to '{endpoint}' unfulfilled: {exc}")
            self._connected = False
            return False

    def poll_message(self) -> Optional[VehicleState]:
        """Poll non-blocking MAVLink packet from socket if connected."""
        if not self._connected or not self._connection:
            return None

        try:
            msg = self._connection.recv_match(blocking=False)
            if not msg:
                return None

            msg_type = msg.get_type()
            msg_data = msg.to_dict()
            return self.normalizer.process_message(msg_type, msg_data)
        except Exception as exc:
            logger.error(f"Error polling MAVLink packet: {exc}")
            return None
