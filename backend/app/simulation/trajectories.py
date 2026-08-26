"""Deterministic target trajectory generation and geographic motion modeling."""

from dataclasses import dataclass, field
import math

from app.schemas.scenario import ScenarioTargetDefinition, ScenarioWaypoint

EARTH_RADIUS_METERS = 6371000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate horizontal Great-Circle distance in meters."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_phi = math.radians(lat2 - lat1)
    delta_lambda = math.radians(lon2 - lon1)

    a = (
        math.sin(delta_phi / 2.0) ** 2
        + math.cos(phi1) * math.cos(phi2) * math.sin(delta_lambda / 2.0) ** 2
    )
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return EARTH_RADIUS_METERS * c


def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate forward initial bearing in degrees in [0, 360) from (lat1, lon1) to (lat2, lon2)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing_rad = math.atan2(y, x)
    return (math.degrees(bearing_rad) + 360.0) % 360.0


def advance_position_wgs84(
    lat: float, lon: float, heading_deg: float, speed_mps: float, dt_seconds: float
) -> tuple[float, float]:
    """Advance latitude and longitude along a great-circle path given heading, speed, and dt."""
    dist_meters = speed_mps * dt_seconds
    if dist_meters <= 0.0:
        return lat, lon

    delta = dist_meters / EARTH_RADIUS_METERS
    theta = math.radians(heading_deg)
    phi1 = math.radians(lat)
    lambda1 = math.radians(lon)

    phi2 = math.asin(
        math.sin(phi1) * math.cos(delta) + math.cos(phi1) * math.sin(delta) * math.cos(theta)
    )
    lambda2 = lambda1 + math.atan2(
        math.sin(theta) * math.sin(delta) * math.cos(phi1),
        math.cos(delta) - math.sin(phi1) * math.sin(phi2),
    )

    # Normalize lon to [-180, 180]
    lon_deg = (math.degrees(lambda2) + 540.0) % 360.0 - 180.0
    lat_deg = max(-90.0, min(90.0, math.degrees(phi2)))

    return round(lat_deg, 7), round(lon_deg, 7)


@dataclass
class TargetKinematicState:
    target_id: str
    latitude: float
    longitude: float
    altitude: float | None
    velocity: float
    heading: float
    classification: str | None
    waypoint_index: int = 0
    is_active: bool = True
    waypoints: list[ScenarioWaypoint] = field(default_factory=list)


class TrajectoryEngine:
    def __init__(self, target_definitions: list[ScenarioTargetDefinition]):
        self._targets: dict[str, TargetKinematicState] = {}
        for t in target_definitions:
            self._targets[t.target_id] = TargetKinematicState(
                target_id=t.target_id,
                latitude=float(t.initial_latitude),
                longitude=float(t.initial_longitude),
                altitude=float(t.initial_altitude) if t.initial_altitude is not None else None,
                velocity=float(t.velocity),
                heading=float(t.heading),
                classification=t.classification,
                waypoint_index=0,
                is_active=True,
                waypoints=list(t.waypoints),
            )

    @property
    def targets(self) -> dict[str, TargetKinematicState]:
        return self._targets

    def get_target_state(self, target_id: str) -> TargetKinematicState | None:
        return self._targets.get(target_id)

    def advance(self, dt_seconds: float) -> list[TargetKinematicState]:
        """Advance all active targets deterministically by dt_seconds."""
        if dt_seconds <= 0:
            return list(self._targets.values())

        for target in self._targets.values():
            if not target.is_active:
                continue

            # Waypoint Navigation mode
            if target.waypoints and target.waypoint_index < len(target.waypoints):
                wp = target.waypoints[target.waypoint_index]
                dist_to_wp = haversine_distance(target.latitude, target.longitude, float(wp.latitude), float(wp.longitude))
                speed = float(wp.speed) if wp.speed is not None else target.velocity
                target.velocity = speed

                arrival_threshold = max(speed * dt_seconds, 15.0)
                if dist_to_wp <= arrival_threshold:
                    # Arrived at waypoint -> snap to waypoint and advance index
                    target.latitude = float(wp.latitude)
                    target.longitude = float(wp.longitude)
                    if wp.altitude is not None:
                        target.altitude = float(wp.altitude)
                    target.waypoint_index += 1

                    if target.waypoint_index < len(target.waypoints):
                        next_wp = target.waypoints[target.waypoint_index]
                        target.heading = round(
                            calculate_bearing_deg(
                                target.latitude, target.longitude, float(next_wp.latitude), float(next_wp.longitude)
                            ),
                            2,
                        )
                else:
                    # Steer towards current waypoint
                    target.heading = round(
                        calculate_bearing_deg(
                            target.latitude, target.longitude, float(wp.latitude), float(wp.longitude)
                        ),
                        2,
                    )
                    target.latitude, target.longitude = advance_position_wgs84(
                        target.latitude, target.longitude, target.heading, target.velocity, dt_seconds
                    )
                    # Vertical climb/descent
                    if wp.altitude is not None and target.altitude is not None:
                        alt_diff = float(wp.altitude) - target.altitude
                        # Climb rate proportional to horizontal progression
                        step_climb = (speed * dt_seconds / max(dist_to_wp, 1.0)) * alt_diff
                        target.altitude = round(target.altitude + step_climb, 2)
            else:
                # Constant Velocity / Constant Heading mode
                target.latitude, target.longitude = advance_position_wgs84(
                    target.latitude, target.longitude, target.heading, target.velocity, dt_seconds
                )

        return sorted(self._targets.values(), key=lambda t: t.target_id)
