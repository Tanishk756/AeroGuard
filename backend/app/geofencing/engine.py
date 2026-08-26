"""Deterministic 2D/3D geofence containment and proximity evaluation engine."""

from dataclasses import dataclass
import math

from app.models.geofence import Geofence

EARTH_RADIUS_METERS = 6371000.0


def haversine_distance(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate great-circle horizontal distance in meters between two WGS84 coordinates."""
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


@dataclass(frozen=True)
class GeofenceEvaluationResult:
    geofence_id: str
    geofence_name: str
    inside: bool
    horizontal_inside: bool
    vertical_inside: bool
    altitude_indeterminate: bool
    distance_to_boundary_meters: float
    reason: str


def _point_in_bbox(lat: float, lon: float, geom: dict) -> bool:
    """Check if point is inside a bounding box."""
    min_lat = geom.get("min_lat")
    max_lat = geom.get("max_lat")
    min_lon = geom.get("min_lon")
    max_lon = geom.get("max_lon")

    if None in (min_lat, max_lat, min_lon, max_lon):
        return False

    return float(min_lat) <= lat <= float(max_lat) and float(min_lon) <= lon <= float(max_lon)


def _point_in_polygon(lat: float, lon: float, coords: list) -> bool:
    """Ray-casting algorithm to determine if point (lat, lon) is inside polygon coordinates.

    Accepts coordinates formatted as list of [lon, lat] pairs (GeoJSON convention)
    or [lat, lon] pairs.
    """
    if len(coords) < 3:
        return False

    vertices: list[tuple[float, float]] = []
    for pt in coords:
        if isinstance(pt, (list, tuple)) and len(pt) >= 2:
            c1, c2 = float(pt[0]), float(pt[1])
            if -180 <= c1 <= 180 and -90 <= c2 <= 90 and not (-90 <= c1 <= 90 and -180 <= c2 <= 180 and abs(c1) > 90):
                vertices.append((c1, c2))  # [lon, lat]
            else:
                vertices.append((c2, c1))  # [lat, lon] -> (lon, lat)

    if len(vertices) < 3:
        return False

    # Bounding box pre-filter
    lons = [v[0] for v in vertices]
    lats = [v[1] for v in vertices]
    if not (min(lons) <= lon <= max(lons) and min(lats) <= lat <= max(lats)):
        return False

    # Ray-casting crossing count
    inside = False
    n = len(vertices)
    j = n - 1
    for i in range(n):
        xi, yi = vertices[i]
        xj, yj = vertices[j]
        if ((yi > lat) != (yj > lat)) and (
            lon < (xj - xi) * (lat - yi) / (yj - yi + 1e-12) + xi
        ):
            inside = not inside
        j = i

    return inside


def _distance_to_bbox_boundary(lat: float, lon: float, geom: dict) -> float:
    """Calculate approximate minimum Haversine distance in meters to bounding box boundary."""
    min_lat = float(geom.get("min_lat", 0.0))
    max_lat = float(geom.get("max_lat", 0.0))
    min_lon = float(geom.get("min_lon", 0.0))
    max_lon = float(geom.get("max_lon", 0.0))

    closest_lat = max(min_lat, min(lat, max_lat))
    closest_lon = max(min_lon, min(lon, max_lon))

    if min_lat <= lat <= max_lat and min_lon <= lon <= max_lon:
        d_south = haversine_distance(lat, lon, min_lat, lon)
        d_north = haversine_distance(lat, lon, max_lat, lon)
        d_west = haversine_distance(lat, lon, lat, min_lon)
        d_east = haversine_distance(lat, lon, lat, max_lon)
        return round(min(d_south, d_north, d_west, d_east), 1)

    return round(haversine_distance(lat, lon, closest_lat, closest_lon), 1)


def evaluate_geofence(
    lat: float,
    lon: float,
    altitude: float | None,
    geofence: Geofence,
) -> GeofenceEvaluationResult:
    """Evaluate a track position against a configured Geofence volume."""
    if not geofence.enabled:
        return GeofenceEvaluationResult(
            geofence_id=geofence.id,
            geofence_name=geofence.name,
            inside=False,
            horizontal_inside=False,
            vertical_inside=False,
            altitude_indeterminate=False,
            distance_to_boundary_meters=999999.0,
            reason="GEOFENCE_DISABLED",
        )

    geom = geofence.geometry
    if not isinstance(geom, dict):
        return GeofenceEvaluationResult(
            geofence_id=geofence.id,
            geofence_name=geofence.name,
            inside=False,
            horizontal_inside=False,
            vertical_inside=False,
            altitude_indeterminate=False,
            distance_to_boundary_meters=999999.0,
            reason="MALFORMED_GEOMETRY",
        )

    gtype = geom.get("type", "").lower()
    h_inside = False
    dist_boundary = 999999.0

    if gtype == "bbox":
        h_inside = _point_in_bbox(lat, lon, geom)
        dist_boundary = _distance_to_bbox_boundary(lat, lon, geom)
    elif gtype == "polygon":
        coords = geom.get("coordinates", [])
        if coords and isinstance(coords[0], list) and isinstance(coords[0][0], list):
            coords = coords[0]
        h_inside = _point_in_polygon(lat, lon, coords)
        lons = [p[0] for p in coords if isinstance(p, (list, tuple)) and len(p) >= 2]
        lats = [p[1] for p in coords if isinstance(p, (list, tuple)) and len(p) >= 2]
        if lats and lons:
            dist_boundary = _distance_to_bbox_boundary(
                lat, lon, {"min_lat": min(lats), "max_lat": max(lats), "min_lon": min(lons), "max_lon": max(lons)}
            )
    else:
        return GeofenceEvaluationResult(
            geofence_id=geofence.id,
            geofence_name=geofence.name,
            inside=False,
            horizontal_inside=False,
            vertical_inside=False,
            altitude_indeterminate=False,
            distance_to_boundary_meters=999999.0,
            reason=f"UNSUPPORTED_GEOMETRY_TYPE: {gtype}",
        )

    # Vertical altitude containment
    has_alt_limits = geofence.min_altitude is not None or geofence.max_altitude is not None
    v_inside = True
    alt_indeterminate = False

    if has_alt_limits:
        if altitude is None:
            alt_indeterminate = True
            v_inside = True
        else:
            if geofence.min_altitude is not None and altitude < geofence.min_altitude:
                v_inside = False
            if geofence.max_altitude is not None and altitude > geofence.max_altitude:
                v_inside = False

    inside = h_inside and v_inside

    reason = "INSIDE_GEOFENCE" if inside else ("OUTSIDE_ALTITUDE" if h_inside else "OUTSIDE_HORIZONTAL")
    if alt_indeterminate and h_inside:
        reason = "INSIDE_HORIZONTAL_ALTITUDE_INDETERMINATE"

    return GeofenceEvaluationResult(
        geofence_id=geofence.id,
        geofence_name=geofence.name,
        inside=inside,
        horizontal_inside=h_inside,
        vertical_inside=v_inside,
        altitude_indeterminate=alt_indeterminate,
        distance_to_boundary_meters=dist_boundary,
        reason=reason,
    )
