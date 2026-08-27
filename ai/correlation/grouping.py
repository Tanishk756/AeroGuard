"""Deterministic multi-track spatial and temporal correlation and grouping engine.

This engine clusters active airspace tracks into correlated groups based on:
1. Horizontal spatial distance <= 500 meters (Haversine geodesic)
2. Absolute velocity difference <= 10 m/s
3. Circular heading difference <= 30 degrees (with 360-degree wraparound)
4. Temporal compatibility window <= 10.0 seconds

This subsystem is strictly an informational and decision-support situational awareness
layer. It does NOT perform weapon targeting, interception guidance, jamming, or fire control.
"""

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import math
from typing import Any, Sequence

from ai.features.kinematics import angular_difference_deg, haversine_distance
from ai.schemas import BehavioralState, TrackGroup


@dataclass(frozen=True)
class TrackObservation:
    """Normalized observation of a track for multi-track correlation."""

    id: str
    latitude: float
    longitude: float
    altitude: float | None = None
    velocity: float | None = None
    heading: float | None = None
    confidence: float = 1.0
    timestamp: datetime | None = None


@dataclass(frozen=True)
class GroupingConfig:
    """Configuration thresholds for deterministic multi-track grouping."""

    max_distance_meters: float = 500.0
    max_velocity_delta_mps: float = 10.0
    max_heading_delta_deg: float = 30.0
    max_temporal_delta_seconds: float = 10.0
    min_group_size: int = 2
    hysteresis_overlap_threshold: float = 0.50


@dataclass(frozen=True)
class PairwiseCorrelation:
    """Structured explainability evidence for pairwise track correlation."""

    track1_id: str
    track2_id: str
    is_correlated: bool
    distance_meters: float
    velocity_delta_mps: float | None
    heading_delta_deg: float | None
    temporal_delta_seconds: float | None
    reason: str


def to_track_observation(obj: Any) -> TrackObservation:
    """Convert a domain Track, dict, or TrackObservation into a TrackObservation dataclass."""
    if isinstance(obj, TrackObservation):
        return obj

    if isinstance(obj, dict):
        ts = obj.get("timestamp") or obj.get("last_seen_at")
        if isinstance(ts, str):
            try:
                ts = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            except Exception:
                ts = None

        return TrackObservation(
            id=str(obj["id"]),
            latitude=float(obj["latitude"]),
            longitude=float(obj["longitude"]),
            altitude=float(obj["altitude"]) if obj.get("altitude") is not None else None,
            velocity=float(obj["velocity"]) if obj.get("velocity") is not None else None,
            heading=float(obj["heading"]) if obj.get("heading") is not None else None,
            confidence=float(obj.get("confidence", 1.0)),
            timestamp=ts,
        )

    # Assume object has attributes (e.g. SQLAlchemy Track model)
    ts = getattr(obj, "last_seen_at", None) or getattr(obj, "timestamp", None)
    return TrackObservation(
        id=str(getattr(obj, "id")),
        latitude=float(getattr(obj, "latitude")),
        longitude=float(getattr(obj, "longitude")),
        altitude=float(obj.altitude) if getattr(obj, "altitude", None) is not None else None,
        velocity=float(obj.velocity) if getattr(obj, "velocity", None) is not None else None,
        heading=float(obj.heading) if getattr(obj, "heading", None) is not None else None,
        confidence=float(getattr(obj, "confidence", 1.0)),
        timestamp=ts,
    )


def evaluate_pairwise_correlation(
    t1: TrackObservation,
    t2: TrackObservation,
    config: GroupingConfig | None = None,
) -> PairwiseCorrelation:
    """Evaluate whether two track observations satisfy all 4 correlation criteria.

    1. Geodesic horizontal distance <= config.max_distance_meters
    2. Velocity delta <= config.max_velocity_delta_mps (if both available)
    3. Smallest circular angular heading delta <= config.max_heading_delta_deg (if both available)
    4. Temporal delta <= config.max_temporal_delta_seconds (if both available)
    """
    cfg = config or GroupingConfig()

    # 1. Spatial distance (Great-Circle Haversine)
    dist_m = haversine_distance(t1.latitude, t1.longitude, t2.latitude, t2.longitude)
    if dist_m > cfg.max_distance_meters:
        return PairwiseCorrelation(
            track1_id=t1.id,
            track2_id=t2.id,
            is_correlated=False,
            distance_meters=dist_m,
            velocity_delta_mps=None,
            heading_delta_deg=None,
            temporal_delta_seconds=None,
            reason=f"Spatial separation ({dist_m:.1f}m) exceeds threshold ({cfg.max_distance_meters:.1f}m)",
        )

    # 2. Velocity delta
    vel_delta: float | None = None
    if t1.velocity is not None and t2.velocity is not None:
        vel_delta = abs(t1.velocity - t2.velocity)
        if vel_delta > cfg.max_velocity_delta_mps:
            return PairwiseCorrelation(
                track1_id=t1.id,
                track2_id=t2.id,
                is_correlated=False,
                distance_meters=dist_m,
                velocity_delta_mps=vel_delta,
                heading_delta_deg=None,
                temporal_delta_seconds=None,
                reason=f"Velocity delta ({vel_delta:.1f} m/s) exceeds threshold ({cfg.max_velocity_delta_mps:.1f} m/s)",
            )

    # 3. Circular heading delta
    heading_delta: float | None = None
    if t1.heading is not None and t2.heading is not None:
        heading_delta = abs(angular_difference_deg(t1.heading, t2.heading))
        if heading_delta > cfg.max_heading_delta_deg:
            return PairwiseCorrelation(
                track1_id=t1.id,
                track2_id=t2.id,
                is_correlated=False,
                distance_meters=dist_m,
                velocity_delta_mps=vel_delta,
                heading_delta_deg=heading_delta,
                temporal_delta_seconds=None,
                reason=f"Heading delta ({heading_delta:.1f} deg) exceeds threshold ({cfg.max_heading_delta_deg:.1f} deg)",
            )

    # 4. Temporal compatibility
    temp_delta: float | None = None
    if t1.timestamp is not None and t2.timestamp is not None:
        temp_delta = abs((t1.timestamp - t2.timestamp).total_seconds())
        if temp_delta > cfg.max_temporal_delta_seconds:
            return PairwiseCorrelation(
                track1_id=t1.id,
                track2_id=t2.id,
                is_correlated=False,
                distance_meters=dist_m,
                velocity_delta_mps=vel_delta,
                heading_delta_deg=heading_delta,
                temporal_delta_seconds=temp_delta,
                reason=f"Temporal delta ({temp_delta:.1f}s) exceeds threshold ({cfg.max_temporal_delta_seconds:.1f}s)",
            )

    return PairwiseCorrelation(
        track1_id=t1.id,
        track2_id=t2.id,
        is_correlated=True,
        distance_meters=dist_m,
        velocity_delta_mps=vel_delta,
        heading_delta_deg=heading_delta,
        temporal_delta_seconds=temp_delta,
        reason="Tracks meet all spatial, kinematic, and temporal correlation criteria",
    )


def calculate_centroid(observations: list[TrackObservation]) -> tuple[float, float, float | None]:
    """Calculate deterministic group centroid (lat, lon, alt).

    Uses circular trigonometric mean for longitude to handle antimeridian crossing correctly.
    """
    if not observations:
        return 0.0, 0.0, None

    n = len(observations)
    mean_lat = sum(o.latitude for o in observations) / n

    # Circular mean for longitude: atan2(sum(sin(lon)), sum(cos(lon)))
    sum_sin = sum(math.sin(math.radians(o.longitude)) for o in observations)
    sum_cos = sum(math.cos(math.radians(o.longitude)) for o in observations)
    mean_lon = math.degrees(math.atan2(sum_sin, sum_cos))

    # Normalize longitude to [-180, 180]
    mean_lon = (mean_lon + 180.0) % 360.0 - 180.0

    # Mean altitude if any available
    alts = [o.altitude for o in observations if o.altitude is not None]
    mean_alt = sum(alts) / len(alts) if alts else None

    return mean_lat, mean_lon, mean_alt


def calculate_radius_of_gyration(
    observations: list[TrackObservation],
    centroid_lat: float,
    centroid_lon: float,
) -> float:
    """Calculate the spatial radius of gyration (RMS geodesic distance to centroid) in meters.

    Rg = sqrt( (1/N) * sum( d(t_i, centroid)^2 ) )
    """
    if not observations:
        return 0.0

    sum_sq_dist = 0.0
    for o in observations:
        dist = haversine_distance(o.latitude, o.longitude, centroid_lat, centroid_lon)
        sum_sq_dist += dist * dist

    return math.sqrt(sum_sq_dist / len(observations))


def assign_group_id(
    member_ids: list[str],
    existing_groups: Sequence[TrackGroup] | None = None,
    hysteresis_threshold: float = 0.50,
) -> str:
    """Derive stable group identifier with join/leave hysteresis matching.

    If an existing group shares >= hysteresis_threshold Jaccard overlap of member IDs,
    its stable group ID is preserved. Otherwise, a deterministic hash of sorted member IDs is used.
    """
    sorted_members = sorted(set(member_ids))
    member_set = set(sorted_members)

    if existing_groups:
        best_id: str | None = None
        best_jaccard = 0.0

        for eg in existing_groups:
            eg_members = set(eg.member_track_ids)
            intersection = len(member_set & eg_members)
            union = len(member_set | eg_members)
            if union > 0:
                jaccard = intersection / union
                if jaccard > best_jaccard and jaccard >= hysteresis_threshold:
                    best_jaccard = jaccard
                    best_id = eg.group_id

        if best_id is not None:
            return best_id

    # Fallback to deterministic member hash
    hash_str = "-".join(sorted_members)
    hex_digest = hashlib.sha256(hash_str.encode("utf-8")).hexdigest()[:10].upper()
    return f"GRP-{hex_digest}"


def calculate_group_confidence(
    observations: list[TrackObservation],
    radius_meters: float,
    max_radius: float = 500.0,
) -> float:
    """Derive deterministic grouping confidence based on member track quality and spatial compactness."""
    if not observations:
        return 1.0

    mean_track_conf = sum(o.confidence for o in observations) / len(observations)
    # Compactness penalty: larger clusters have slight confidence moderation
    compactness_ratio = min(1.0, radius_meters / max(1.0, max_radius))
    confidence = mean_track_conf * (1.0 - 0.20 * compactness_ratio)

    return max(0.1, min(1.0, round(confidence, 3)))


def correlate_tracks(
    tracks: Sequence[Any],
    config: GroupingConfig | None = None,
    existing_groups: Sequence[TrackGroup] | None = None,
    now: datetime | None = None,
) -> list[TrackGroup]:
    """Execute deterministic multi-track correlation and connected-component grouping.

    Guarantees:
    - Order-independent deterministic results (sorting input by track ID).
    - Connected components: if A correlated with B and B correlated with C, [A, B, C] are grouped.
    - Noise resistance: singletons (< min_group_size) are not emitted as groups.
    - Stable Group IDs with join/leave hysteresis.
    - Correct radius of gyration and circular longitude centroid calculation.
    """
    cfg = config or GroupingConfig()
    eval_time = now or datetime.now(UTC)

    # 1. Normalize and sort observations deterministically by ID
    observations_map: dict[str, TrackObservation] = {}
    for t in tracks:
        obs = to_track_observation(t)
        observations_map[obs.id] = obs

    sorted_obs = sorted(observations_map.values(), key=lambda o: o.id)
    n = len(sorted_obs)

    if n < cfg.min_group_size:
        return []

    # 2. Build adjacency graph
    adj: dict[str, set[str]] = {o.id: set() for o in sorted_obs}
    for i in range(n):
        for j in range(i + 1, n):
            t1 = sorted_obs[i]
            t2 = sorted_obs[j]
            corr = evaluate_pairwise_correlation(t1, t2, cfg)
            if corr.is_correlated:
                adj[t1.id].add(t2.id)
                adj[t2.id].add(t1.id)

    # 3. Find connected components deterministically
    visited: set[str] = set()
    groups: list[TrackGroup] = []

    for obs in sorted_obs:
        if obs.id in visited:
            continue

        # BFS / DFS traversal
        component_ids: list[str] = []
        queue = [obs.id]
        visited.add(obs.id)

        while queue:
            curr_id = queue.pop(0)
            component_ids.append(curr_id)

            # Deterministic traversal order
            neighbors = sorted(adj[curr_id])
            for neighbor in neighbors:
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append(neighbor)

        component_ids.sort()

        # 4. Filter singletons (< min_group_size)
        if len(component_ids) >= cfg.min_group_size:
            member_obs = [observations_map[mid] for mid in component_ids]
            centroid_lat, centroid_lon, centroid_alt = calculate_centroid(member_obs)
            radius_m = calculate_radius_of_gyration(member_obs, centroid_lat, centroid_lon)
            group_id = assign_group_id(
                component_ids,
                existing_groups=existing_groups,
                hysteresis_threshold=cfg.hysteresis_overlap_threshold,
            )
            confidence = calculate_group_confidence(member_obs, radius_m, cfg.max_distance_meters)

            groups.append(
                TrackGroup(
                    group_id=group_id,
                    member_track_ids=component_ids,
                    centroid_lat=centroid_lat,
                    centroid_lon=centroid_lon,
                    centroid_alt=centroid_alt,
                    radius_meters=radius_m,
                    member_count=len(component_ids),
                    confidence=confidence,
                    behavioral_state=BehavioralState.NORMAL,  # Neutral default in AI2-B
                    updated_at=eval_time,
                )
            )

    # Sort groups deterministically by group_id
    groups.sort(key=lambda g: g.group_id)
    return groups
