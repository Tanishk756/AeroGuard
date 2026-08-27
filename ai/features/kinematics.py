"""Deterministic kinematic and flight pattern feature extraction."""

from datetime import datetime
import math
from ai.schemas import KinematicFeatures, TrackPoint

EARTH_RADIUS_METERS = 6371000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate horizontal Great-Circle distance in meters between two WGS84 coordinates."""
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


def calculate_bearing_deg(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate forward initial bearing in degrees in [0, 360) from (lat1, lon1) to (lat2, lon2)."""
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    delta_lambda = math.radians(lon2 - lon1)

    y = math.sin(delta_lambda) * math.cos(phi2)
    x = math.cos(phi1) * math.sin(phi2) - math.sin(phi1) * math.cos(phi2) * math.cos(delta_lambda)
    bearing_rad = math.atan2(y, x)
    return (math.degrees(bearing_rad) + 360.0) % 360.0


def angular_difference_deg(heading1: float, heading2: float) -> float:
    """Calculate the shortest signed angular difference (heading2 - heading1) in [-180, 180] degrees."""
    diff = (heading2 - heading1 + 180.0) % 360.0 - 180.0
    return diff


def _variance(values: list[float]) -> float:
    """Compute sample variance safely."""
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    return sum((x - mean) ** 2 for x in values) / (len(values) - 1)


def extract_kinematic_features(points: list[TrackPoint]) -> KinematicFeatures:
    """Extract deterministic, explainable kinematic features from chronological track points.

    Handles zero points, single points, irregular time intervals, stationary targets,
    and missing altitude observations safely without exceptions.
    """
    if not points:
        return KinematicFeatures(sample_count=0)

    # Sort chronologically
    sorted_points = sorted(points, key=lambda p: p.timestamp)

    # Filter invalid points
    valid_points: list[TrackPoint] = []
    for p in sorted_points:
        if (
            p.latitude is not None
            and not math.isnan(p.latitude)
            and -90.0 <= p.latitude <= 90.0
            and p.longitude is not None
            and not math.isnan(p.longitude)
            and -180.0 <= p.longitude <= 180.0
        ):
            valid_points.append(p)

    if not valid_points:
        return KinematicFeatures(sample_count=0)

    latest = valid_points[-1]
    if len(valid_points) == 1:
        return KinematicFeatures(
            speed_mps=float(latest.velocity or 0.0),
            heading_deg=float(latest.heading) if latest.heading is not None else None,
            sample_count=1,
            timespan_seconds=0.0,
            directional_consistency=1.0,
        )

    # Deduplicate points with zero or negative time deltas
    deduped: list[TrackPoint] = [valid_points[0]]
    for p in valid_points[1:]:
        if (p.timestamp - deduped[-1].timestamp).total_seconds() > 0.001:
            deduped.append(p)

    if len(deduped) == 1:
        return KinematicFeatures(
            speed_mps=float(latest.velocity or 0.0),
            heading_deg=float(latest.heading) if latest.heading is not None else None,
            sample_count=len(valid_points),
            timespan_seconds=0.0,
            directional_consistency=1.0,
        )

    timespan = (deduped[-1].timestamp - deduped[0].timestamp).total_seconds()

    speeds: list[float] = []
    headings: list[float] = []
    altitudes: list[float] = []
    vertical_rates: list[float] = []
    accelerations: list[float] = []
    turn_rates: list[float] = []
    step_distances: list[float] = []

    for i in range(1, len(deduped)):
        p_prev = deduped[i - 1]
        p_curr = deduped[i]
        dt = (p_curr.timestamp - p_prev.timestamp).total_seconds()
        if dt <= 0:
            continue

        step_dist = haversine_distance(
            p_prev.latitude, p_prev.longitude, p_curr.latitude, p_curr.longitude
        )
        step_distances.append(step_dist)

        # Speed: prefer velocity attribute if provided and > 0, else compute from distance
        if p_curr.velocity is not None and p_curr.velocity >= 0:
            speed = float(p_curr.velocity)
        else:
            speed = step_dist / dt
        speeds.append(speed)

        # Heading: prefer explicit heading, else compute bearing
        if p_curr.heading is not None and 0.0 <= p_curr.heading < 360.0:
            heading = float(p_curr.heading)
        elif step_dist > 0.5:
            heading = calculate_bearing_deg(
                p_prev.latitude, p_prev.longitude, p_curr.latitude, p_curr.longitude
            )
        elif headings:
            heading = headings[-1]
        else:
            heading = 0.0
        headings.append(heading)

        # Altitude and vertical speed
        if p_curr.altitude is not None:
            altitudes.append(float(p_curr.altitude))
            if p_prev.altitude is not None:
                v_rate = (float(p_curr.altitude) - float(p_prev.altitude)) / dt
                vertical_rates.append(v_rate)

        # Turn rate
        if len(headings) >= 2:
            d_heading = abs(angular_difference_deg(headings[-2], headings[-1]))
            turn_rate = d_heading / dt
            turn_rates.append(turn_rate)

        # Acceleration
        if len(speeds) >= 2:
            acc = (speeds[-1] - speeds[-2]) / dt
            accelerations.append(acc)

    # Current instantaneous estimates (latest valid)
    current_speed = speeds[-1] if speeds else float(latest.velocity or 0.0)
    current_heading = headings[-1] if headings else (float(latest.heading) if latest.heading is not None else None)
    current_acceleration = accelerations[-1] if accelerations else 0.0
    current_vertical_speed = vertical_rates[-1] if vertical_rates else 0.0
    current_turn_rate = turn_rates[-1] if turn_rates else 0.0

    # Variances
    speed_var = _variance(speeds)
    altitude_var = _variance(altitudes) if len(altitudes) >= 2 else 0.0
    acceleration_var = _variance(accelerations) if len(accelerations) >= 2 else 0.0

    # Total path length & net displacement
    total_path_length = sum(step_distances)
    net_displacement = haversine_distance(
        deduped[0].latitude, deduped[0].longitude,
        deduped[-1].latitude, deduped[-1].longitude
    )

    if total_path_length < 5.0:
        directional_consistency = 1.0
        trajectory_curvature = 0.0
    else:
        directional_consistency = max(0.0, min(1.0, net_displacement / total_path_length))
        # Curvature: total angular deviation (in radians) per meter traveled
        total_angle_rad = sum(math.radians(tr * dt) for tr in turn_rates) if turn_rates else 0.0
        trajectory_curvature = total_angle_rad / total_path_length

    # Loitering Detection
    loiter_radius: float | None = None
    if directional_consistency < 0.6 and len(deduped) >= 4 and total_path_length >= 30.0:
        # Compute geographic centroid
        mean_lat = sum(p.latitude for p in deduped) / len(deduped)
        mean_lon = sum(p.longitude for p in deduped) / len(deduped)
        radii = [haversine_distance(p.latitude, p.longitude, mean_lat, mean_lon) for p in deduped]
        # Radius of gyration
        mean_r = math.sqrt(sum(r ** 2 for r in radii) / len(radii))
        if mean_r <= 5000.0:
            loiter_radius = round(mean_r, 1)

    return KinematicFeatures(
        speed_mps=round(current_speed, 2),
        acceleration_mps2=round(current_acceleration, 2),
        vertical_speed_mps=round(current_vertical_speed, 2),
        heading_deg=round(current_heading, 2) if current_heading is not None else None,
        turn_rate_dps=round(current_turn_rate, 2),
        speed_variance=round(speed_var, 3),
        altitude_variance=round(altitude_var, 3),
        acceleration_variance=round(acceleration_var, 3),
        trajectory_curvature=round(trajectory_curvature, 5),
        loiter_radius_meters=loiter_radius,
        directional_consistency=round(directional_consistency, 3),
        sample_count=len(valid_points),
        timespan_seconds=round(timespan, 2),
    )
