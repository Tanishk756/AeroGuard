"""Deterministic spatial and kinematic multi-sensor consensus algorithms."""

from dataclasses import dataclass
import math

from app.models.detection import Detection
from app.models.track import Track


def angular_difference(h1: float, h2: float) -> float:
    """Calculate the minimal angular difference in degrees between two headings in [0, 360)."""
    diff = abs(h1 - h2) % 360.0
    if diff > 180.0:
        diff = 360.0 - diff
    return diff


@dataclass(frozen=True)
class FusedKinematics:
    latitude: float
    longitude: float
    altitude: float | None
    velocity: float | None
    heading: float | None
    weight_applied: float


def fuse_kinematics(track: Track, detection: Detection) -> FusedKinematics:
    """Fuse an associated detection's measurements into current track kinematics.

    Uses uncertainty/confidence-weighted convex combination for coordinates and
    kinematics without fabricating missing dimensions.
    """
    # 1. Calculate detection weight
    if detection.horizontal_uncertainty is not None and detection.horizontal_uncertainty > 0:
        det_weight = detection.confidence / max(detection.horizontal_uncertainty**2, 1.0)
    else:
        det_weight = detection.confidence

    track_weight = max(track.confidence, 0.1)
    total_w = det_weight + track_weight
    alpha = max(0.01, min(0.5, det_weight / total_w))

    # 2. Position consensus
    fused_lat = round((1.0 - alpha) * track.latitude + alpha * detection.latitude, 7)
    fused_lon = round((1.0 - alpha) * track.longitude + alpha * detection.longitude, 7)

    # 3. Altitude consensus (only when available, never fabricated)
    fused_alt: float | None = None
    if detection.altitude is not None and track.altitude is not None:
        fused_alt = round((1.0 - alpha) * track.altitude + alpha * detection.altitude, 2)
    elif detection.altitude is not None:
        fused_alt = round(detection.altitude, 2)
    elif track.altitude is not None:
        fused_alt = track.altitude

    # 4. Velocity consensus
    fused_vel: float | None = None
    if detection.velocity is not None and track.velocity is not None:
        fused_vel = round((1.0 - alpha) * track.velocity + alpha * detection.velocity, 2)
    elif detection.velocity is not None:
        fused_vel = round(detection.velocity, 2)
    elif track.velocity is not None:
        fused_vel = track.velocity

    # 5. Heading consensus (minimal angular arc interpolation)
    fused_head: float | None = None
    if detection.heading is not None and track.heading is not None:
        diff = ((detection.heading - track.heading + 180.0) % 360.0) - 180.0
        interpolated = (track.heading + alpha * diff) % 360.0
        fused_head = round(interpolated, 2)
    elif detection.heading is not None:
        fused_head = round(detection.heading, 2)
    elif track.heading is not None:
        fused_head = track.heading

    return FusedKinematics(
        latitude=fused_lat,
        longitude=fused_lon,
        altitude=fused_alt,
        velocity=fused_vel,
        heading=fused_head,
        weight_applied=round(alpha, 4),
    )
