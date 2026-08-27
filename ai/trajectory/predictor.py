"""Deterministic defensive trajectory prediction and geofence ingress estimation.

Computes forward flight path projections and time-to-perimeter ingress
under constant-velocity and constant-acceleration motion models.
"""

from datetime import UTC, datetime, timedelta
import math
from typing import Any

from ai.schemas import (
    GeofenceIngressEstimate,
    TrajectoryPrediction,
    TrajectoryWayPoint,
)

EARTH_RADIUS_METERS = 6371000.0


def advance_position_wgs84(
    lat: float, lon: float, heading_deg: float, distance_meters: float
) -> tuple[float, float]:
    """Advance latitude and longitude along a great-circle path given heading and distance in meters."""
    if distance_meters <= 0.0:
        return round(lat, 7), round(lon, 7)

    delta = distance_meters / EARTH_RADIUS_METERS
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

    lon_deg = (math.degrees(lambda2) + 540.0) % 360.0 - 180.0
    lat_deg = max(-90.0, min(90.0, math.degrees(phi2)))
    return round(lat_deg, 7), round(lon_deg, 7)


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
    c = 2.0 * math.atan2(math.sqrt(max(0.0, a)), math.sqrt(max(0.0, 1.0 - a)))
    return EARTH_RADIUS_METERS * c


def _is_point_inside_geofence(
    lat: float, lon: float, alt: float | None, geofence: Any
) -> bool:
    """Check if point (lat, lon, alt) is inside a geofence definition."""
    # Extract properties whether ORM model or dict
    if isinstance(geofence, dict):
        geom_type = geofence.get("geometry_type") or geofence.get("type", "BBOX")
        geom = geofence.get("geometry", {})
        min_alt = geofence.get("min_altitude_meters") or geofence.get("min_altitude")
        max_alt = geofence.get("max_altitude_meters") or geofence.get("max_altitude")
    else:
        geom_type = getattr(geofence, "geometry_type", "BBOX")
        geom = getattr(geofence, "geometry", {}) or {}
        min_alt = getattr(geofence, "min_altitude_meters", None)
        max_alt = getattr(geofence, "max_altitude_meters", None)

    # 1. Vertical check
    if alt is not None:
        if min_alt is not None and alt < float(min_alt):
            return False
        if max_alt is not None and alt > float(max_alt):
            return False

    # 2. Horizontal check
    g_type = str(geom_type).upper()
    if "BBOX" in g_type:
        min_lat = geom.get("min_lat")
        max_lat = geom.get("max_lat")
        min_lon = geom.get("min_lon")
        max_lon = geom.get("max_lon")
        if None in (min_lat, max_lat, min_lon, max_lon):
            return False
        return float(min_lat) <= lat <= float(max_lat) and float(min_lon) <= lon <= float(max_lon)

    if "POLYGON" in g_type:
        coords = geom.get("coordinates") or geom.get("vertices") or []
        if not coords or len(coords) < 3:
            return False
        vertices: list[tuple[float, float]] = []
        for c in coords:
            if isinstance(c, (list, tuple)) and len(c) >= 2:
                # GeoJSON convention is [lon, lat]
                if abs(c[0]) > 90.0 and abs(c[1]) <= 90.0:
                    vertices.append((float(c[1]), float(c[0])))
                else:
                    vertices.append((float(c[0]), float(c[1])))
        if len(vertices) < 3:
            return False

        # Ray-casting algorithm
        inside = False
        n = len(vertices)
        for i in range(n):
            j = (i + 1) % n
            xi, yi = vertices[i]
            xj, yj = vertices[j]
            if ((yi > lon) != (yj > lon)) and (
                lat < (xj - xi) * (lon - yi) / ((yj - yi) or 1e-12) + xi
            ):
                inside = not inside
        return inside

    if "CIRCLE" in g_type or "CYLINDER" in g_type:
        center_lat = geom.get("center_lat") or geom.get("lat")
        center_lon = geom.get("center_lon") or geom.get("lon")
        radius = geom.get("radius_meters") or geom.get("radius", 0.0)
        if center_lat is None or center_lon is None or radius <= 0:
            return False
        dist = haversine_distance(lat, lon, float(center_lat), float(center_lon))
        return dist <= float(radius)

    return False


def predict_trajectory(
    track_id: str,
    current_lat: float,
    current_lon: float,
    current_alt: float | None = None,
    speed_mps: float = 0.0,
    heading_deg: float | None = None,
    acceleration_mps2: float = 0.0,
    vertical_speed_mps: float = 0.0,
    horizon_seconds: float = 60.0,
    step_interval_seconds: float = 5.0,
    turn_rate_dps: float = 0.0,
    start_time: datetime | None = None,
) -> TrajectoryPrediction:
    """Compute forward trajectory prediction and expanding spatial uncertainty envelopes.

    Uses constant-velocity or constant-acceleration with turn extrapolation.
    """
    ref_time = start_time or datetime.now(UTC)
    waypoints: list[TrajectoryWayPoint] = []

    model_type = "CONSTANT_ACCELERATION" if abs(acceleration_mps2) > 0.1 else "CONSTANT_VELOCITY"
    effective_heading = heading_deg if heading_deg is not None else 0.0
    has_heading = heading_deg is not None and (speed_mps > 0.5 or abs(acceleration_mps2) > 0.1)

    steps = max(1, int(horizon_seconds / max(1.0, step_interval_seconds)))
    curr_lat = current_lat
    curr_lon = current_lon
    curr_alt = current_alt
    curr_speed = max(0.0, speed_mps)
    curr_heading = effective_heading

    for step_idx in range(1, steps + 1):
        t_offset = step_idx * step_interval_seconds
        dt = step_interval_seconds

        # Kinematic advancement
        if model_type == "CONSTANT_ACCELERATION":
            # d = v*dt + 0.5*a*dt^2
            dist_step = (curr_speed * dt) + (0.5 * acceleration_mps2 * (dt ** 2))
            curr_speed = max(0.0, curr_speed + (acceleration_mps2 * dt))
        else:
            dist_step = curr_speed * dt

        if has_heading and dist_step > 0.0:
            if abs(turn_rate_dps) > 0.1:
                curr_heading = (curr_heading + (turn_rate_dps * dt)) % 360.0
            next_lat, next_lon = advance_position_wgs84(curr_lat, curr_lon, curr_heading, dist_step)
            curr_lat, curr_lon = next_lat, next_lon

        # Altitude extrapolation
        if curr_alt is not None:
            curr_alt = max(0.0, curr_alt + (vertical_speed_mps * dt))

        # Spatial uncertainty envelope: expands over time
        # base_uncertainty (10m) + velocity jitter + acceleration variance
        uncertainty = 10.0 + (0.08 * (curr_speed or 5.0) * t_offset) + (0.05 * abs(acceleration_mps2) * (t_offset ** 1.5))
        if not has_heading:
            uncertainty += 5.0 * t_offset

        waypoints.append(
            TrajectoryWayPoint(
                timestamp=ref_time + timedelta(seconds=t_offset),
                time_offset_seconds=round(t_offset, 1),
                latitude=curr_lat,
                longitude=curr_lon,
                altitude=round(curr_alt, 1) if curr_alt is not None else None,
                uncertainty_radius_meters=round(uncertainty, 1),
            )
        )

    return TrajectoryPrediction(
        track_id=track_id,
        prediction_horizon_seconds=round(horizon_seconds, 1),
        model_type=model_type,
        waypoints=waypoints,
        generated_at=ref_time,
    )


def estimate_geofence_ingress(
    track_id: str,
    trajectory: TrajectoryPrediction,
    geofences: list[Any],
    current_lat: float | None = None,
    current_lon: float | None = None,
    current_alt: float | None = None,
) -> list[GeofenceIngressEstimate]:
    """Estimate time-to-breach and ingress intersection points against active geofences."""
    estimates: list[GeofenceIngressEstimate] = []
    now = datetime.now(UTC)

    # Initial position from first waypoint or current coordinate
    first_lat = current_lat if current_lat is not None else (trajectory.waypoints[0].latitude if trajectory.waypoints else 0.0)
    first_lon = current_lon if current_lon is not None else (trajectory.waypoints[0].longitude if trajectory.waypoints else 0.0)
    first_alt = current_alt if current_alt is not None else (trajectory.waypoints[0].altitude if trajectory.waypoints else None)

    for geofence in geofences:
        gid = geofence.get("id") if isinstance(geofence, dict) else getattr(geofence, "id", "UNKNOWN")
        gname = geofence.get("name") if isinstance(geofence, dict) else getattr(geofence, "name", f"Geofence {gid}")

        # 1. Check if already inside
        if _is_point_inside_geofence(first_lat, first_lon, first_alt, geofence):
            estimates.append(
                GeofenceIngressEstimate(
                    track_id=track_id,
                    geofence_id=str(gid),
                    geofence_name=str(gname),
                    estimated_time_to_breach_seconds=0.0,
                    intersection_latitude=first_lat,
                    intersection_longitude=first_lon,
                    status="INSIDE",
                    evaluated_at=now,
                )
            )
            continue

        # 2. Trace along trajectory waypoints
        breach_found = False
        for wp in trajectory.waypoints:
            if _is_point_inside_geofence(wp.latitude, wp.longitude, wp.altitude, geofence):
                estimates.append(
                    GeofenceIngressEstimate(
                        track_id=track_id,
                        geofence_id=str(gid),
                        geofence_name=str(gname),
                        estimated_time_to_breach_seconds=wp.time_offset_seconds,
                        intersection_latitude=wp.latitude,
                        intersection_longitude=wp.longitude,
                        status="APPROACHING",
                        evaluated_at=now,
                    )
                )
                breach_found = True
                break

        if not breach_found:
            # Check if diverging vs no intersection
            estimates.append(
                GeofenceIngressEstimate(
                    track_id=track_id,
                    geofence_id=str(gid),
                    geofence_name=str(gname),
                    estimated_time_to_breach_seconds=None,
                    intersection_latitude=None,
                    intersection_longitude=None,
                    status="NO_INTERSECTION",
                    evaluated_at=now,
                )
            )

    return estimates
