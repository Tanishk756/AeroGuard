"""Stage S11 Swarm State Aggregation Engine.

Calculates deterministic spatial statistics (centroid, bounding box, bounding sphere),
formation deviation metrics, pairwise separation extremes, health breakdowns, and communication quality summaries.
"""

import math
from typing import Dict, List, Optional, Tuple
from app.schemas.swarm_telemetry import (
    CommunicationQualitySummary,
    FormationDeviationStats,
    PairwiseSeparationStats,
    SwarmBoundingBoxENU,
    SwarmTelemetrySnapshot,
    SwarmVehicleTelemetry,
    TelemetryFreshnessSummary,
    VehicleHealthSummary,
)


class SwarmAggregationEngine:
    """Deterministic spatial and telemetry state aggregator for multi-vehicle swarms."""

    @classmethod
    def compute_swarm_snapshot(
        cls,
        swarm_id: str,
        snapshot_sequence: int,
        telemetry_map: Dict[str, SwarmVehicleTelemetry],
        desired_positions_enu: Optional[Dict[str, Tuple[float, float, float]]] = None,
        current_time_s: Optional[float] = None,
    ) -> SwarmTelemetrySnapshot:
        """Compute coherent SwarmTelemetrySnapshot from fused vehicle telemetry map."""
        if not telemetry_map:
            return SwarmTelemetrySnapshot(swarm_id=swarm_id, snapshot_sequence=snapshot_sequence)

        active_vids = sorted(list(telemetry_map.keys()))
        n = len(active_vids)

        # 1. Swarm Centroid & Bounding Box calculation in ENU
        sum_x = sum_y = sum_z = 0.0
        sum_vx = sum_vy = sum_vz = 0.0

        min_x = min_y = min_z = float("inf")
        max_x = max_y = max_z = float("-inf")

        healthy_c = degraded_c = critical_c = disc_c = 0
        sum_age = 0.0
        max_age = 0.0
        sum_qual = 0.0
        min_qual = 100.0

        positions_enu: Dict[str, Tuple[float, float, float]] = {}

        for vid in active_vids:
            vt = telemetry_map[vid]

            # Approximate local ENU coordinates (longitude * 111320m, latitude * 111320m, alt_rel)
            x = vt.position.longitude * 111320.0
            y = vt.position.latitude * 111320.0
            z = vt.position.altitude_relative

            positions_enu[vid] = (x, y, z)

            sum_x += x
            sum_y += y
            sum_z += z

            sum_vx += vt.velocity.vx
            sum_vy += vt.velocity.vy
            sum_vz += vt.velocity.vz

            min_x = min(min_x, x)
            max_x = max(max_x, x)
            min_y = min(min_y, y)
            max_y = max(max_y, y)
            min_z = min(min_z, z)
            max_z = max(max_z, z)

            # Health classification
            h = vt.vehicle_health.upper()
            if h == "HEALTHY":
                healthy_c += 1
            elif h == "DEGRADED":
                degraded_c += 1
            elif h == "CRITICAL":
                critical_c += 1
            else:
                disc_c += 1

            sum_age += vt.telemetry_age_s
            max_age = max(max_age, vt.telemetry_age_s)

            # Communication Link Quality
            qual = 100.0 - vt.link_status.packet_loss_percent
            sum_qual += qual
            min_qual = min(min_qual, qual)

        centroid_enu = (sum_x / n, sum_y / n, sum_z / n)
        average_velocity_enu = (sum_vx / n, sum_vy / n, sum_vz / n)

        # Bounding sphere radius from centroid
        max_dist_to_centroid = 0.0
        for vid in active_vids:
            px, py, pz = positions_enu[vid]
            dx = px - centroid_enu[0]
            dy = py - centroid_enu[1]
            dz = pz - centroid_enu[2]
            d = math.sqrt(dx * dx + dy * dy + dz * dz)
            max_dist_to_centroid = max(max_dist_to_centroid, d)

        # 2. Pairwise Separation Statistics
        min_pair_dist = float("inf")
        max_pair_dist = 0.0
        closest_pair: Optional[Tuple[str, str]] = None

        for i in range(n):
            for j in range(i + 1, n):
                v1 = active_vids[i]
                v2 = active_vids[j]
                p1 = positions_enu[v1]
                p2 = positions_enu[v2]

                dist = math.sqrt(
                    (p1[0] - p2[0]) ** 2 + (p1[1] - p2[1]) ** 2 + (p1[2] - p2[2]) ** 2
                )

                if dist < min_pair_dist:
                    min_pair_dist = dist
                    closest_pair = (v1, v2)
                max_pair_dist = max(max_pair_dist, dist)

        if min_pair_dist == float("inf"):
            min_pair_dist = 0.0

        # 3. Formation Deviation Statistics
        dev_errors: List[float] = []
        if desired_positions_enu:
            for vid in active_vids:
                if vid in desired_positions_enu:
                    d_pos = desired_positions_enu[vid]
                    c_pos = positions_enu[vid]
                    err = math.sqrt(
                        (c_pos[0] - d_pos[0]) ** 2 + (c_pos[1] - d_pos[1]) ** 2 + (c_pos[2] - d_pos[2]) ** 2
                    )
                    dev_errors.append(err)

        mean_err = sum(dev_errors) / len(dev_errors) if dev_errors else 0.0
        max_err = max(dev_errors) if dev_errors else 0.0
        std_err = (
            math.sqrt(sum((e - mean_err) ** 2 for e in dev_errors) / len(dev_errors))
            if dev_errors
            else 0.0
        )

        from datetime import datetime, timezone
        ts_utc = datetime.fromtimestamp(current_time_s or 0.0, tz=timezone.utc).isoformat()

        return SwarmTelemetrySnapshot(
            swarm_id=swarm_id,
            snapshot_sequence=snapshot_sequence,
            timestamp_utc=ts_utc,
            sim_time_seconds=current_time_s or 0.0,
            active_vehicle_ids=active_vids,
            vehicles_telemetry=telemetry_map,
            centroid_enu=centroid_enu,
            bounding_box_enu=SwarmBoundingBoxENU(
                min_x=min_x, max_x=max_x, min_y=min_y, max_y=max_y, min_z=min_z, max_z=max_z
            ),
            bounding_sphere_radius_m=max_dist_to_centroid,
            average_velocity_enu=average_velocity_enu,
            formation_centroid_enu=centroid_enu,
            formation_deviation_stats=FormationDeviationStats(
                mean_error_m=mean_err, max_error_m=max_err, std_dev_m=std_err
            ),
            pairwise_separation_stats=PairwiseSeparationStats(
                min_distance_m=min_pair_dist,
                max_distance_m=max_pair_dist,
                closest_pair=closest_pair,
            ),
            vehicle_health_summary=VehicleHealthSummary(
                healthy_count=healthy_c,
                degraded_count=degraded_c,
                critical_count=critical_c,
                disconnected_count=disc_c,
            ),
            telemetry_freshness_summary=TelemetryFreshnessSummary(
                avg_age_s=sum_age / n, max_age_s=max_age
            ),
            communication_quality_summary=CommunicationQualitySummary(
                avg_quality_percent=sum_qual / n, min_quality_percent=min_qual
            ),
        )
