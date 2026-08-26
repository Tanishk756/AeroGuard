"""Association value objects and geographic/kinematic calculations."""

import math
from dataclasses import dataclass
from uuid import NAMESPACE_URL, uuid5

from app.models.association import TrackAssociationDecision

EARTH_RADIUS_METERS = 6371000.0
TRACK_NAMESPACE = uuid5(NAMESPACE_URL, "aeroguard:track")


def generate_track_id(detection_id: str) -> str:
    """Generate a deterministic Track UUID5 from a detection ID."""
    return str(uuid5(TRACK_NAMESPACE, f"track:{detection_id}"))


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


def calculate_distance_3d(
    horizontal_dist: float, alt1: float | None, alt2: float | None
) -> tuple[float, float | None]:
    """Calculate 3D distance and vertical distance if altitudes are available.

    If either altitude is missing, returns (horizontal_dist, None). Never fabricates altitude.
    """
    if alt1 is not None and alt2 is not None:
        vert_dist = abs(alt1 - alt2)
        dist_3d = math.sqrt(horizontal_dist**2 + vert_dist**2)
        return dist_3d, vert_dist
    return horizontal_dist, None


def angular_difference(h1: float, h2: float) -> float:
    """Calculate the minimal angular difference in degrees between two headings in [0, 360)."""
    diff = abs(h1 - h2) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff


@dataclass(frozen=True)
class AssociationDecision:
    """Immutable explainability record of an association evaluation."""

    detection_id: str
    track_id: str | None
    decision: TrackAssociationDecision
    gate_result: str | None
    horizontal_distance: float | None
    vertical_distance: float | None
    time_delta: float | None
    score: float | None
    reason: str
    candidate_count: int
