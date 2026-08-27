"""Performance benchmarks for AeroGuard AI defensive intelligence pipeline."""

from datetime import UTC, datetime, timedelta
import time
import pytest

from ai.anomaly.scoring import evaluate_anomaly
from ai.confidence.sensor import compute_sensor_confidence
from ai.features.kinematics import extract_kinematic_features
from ai.schemas import TrackPoint
from ai.trajectory.predictor import estimate_geofence_ingress, predict_trajectory
from app.models.geofence import Geofence


def _generate_synthetic_track_history(track_id: str, count: int = 15) -> list[TrackPoint]:
    """Generate realistic synthetic track points for benchmark evaluation."""
    now = datetime.now(UTC)
    points = []
    base_lat = 37.7749
    base_lon = -122.4194

    for i in range(count):
        t = now - timedelta(seconds=(count - i) * 2)
        points.append(
            TrackPoint(
                timestamp=t,
                latitude=base_lat + (i * 0.0003),
                longitude=base_lon + (i * 0.0003),
                altitude=100.0 + (i * 2.0),
                velocity=20.0 + (i % 3),
                heading=45.0 + (i * 2.0),
                confidence=0.92,
            )
        )
    return points


def test_kinematic_feature_extraction_benchmarks():
    """Benchmark feature extraction across increasing batch sizes."""
    sizes = [10, 50, 100, 500]
    results = {}

    for size in sizes:
        batch = [_generate_synthetic_track_history(f"TRK-{i}", count=20) for i in range(size)]

        t_start = time.perf_counter()
        for pts in batch:
            extract_kinematic_features(pts)
        t_elapsed = time.perf_counter() - t_start

        avg_latency_us = (t_elapsed / size) * 1_000_000
        throughput = size / t_elapsed
        results[size] = (avg_latency_us, throughput)

        # Invariant: Each extraction must take less than 1ms (1000 µs)
        assert avg_latency_us < 1000.0, f"Extraction for batch size {size} took {avg_latency_us:.2f}µs"

    print("\n--- Kinematic Feature Extraction Benchmarks ---")
    for size, (lat, rate) in results.items():
        print(f"Batch {size:3d} tracks: {lat:6.2f} µs/track ({rate:8.0f} tracks/sec)")


def test_anomaly_scoring_benchmarks():
    """Benchmark explainable anomaly scoring across increasing batch sizes."""
    sizes = [10, 50, 100, 500]
    results = {}

    for size in sizes:
        tracks_data = []
        for i in range(size):
            pts = _generate_synthetic_track_history(f"TRK-{i}", count=15)
            feat = extract_kinematic_features(pts)
            conf = compute_sensor_confidence(provenance="RADAR", source_count=2, speed_variance=feat.speed_variance)
            tracks_data.append((f"TRK-{i}", feat, conf))

        t_start = time.perf_counter()
        for track_id, feat, conf in tracks_data:
            evaluate_anomaly(track_id, feat, conf)
        t_elapsed = time.perf_counter() - t_start

        avg_latency_us = (t_elapsed / size) * 1_000_000
        throughput = size / t_elapsed
        results[size] = (avg_latency_us, throughput)

        # Invariant: Each scoring evaluation must take less than 500 µs
        assert avg_latency_us < 500.0, f"Scoring for batch size {size} took {avg_latency_us:.2f}µs"

    print("\n--- Anomaly Scoring Benchmarks ---")
    for size, (lat, rate) in results.items():
        print(f"Batch {size:3d} tracks: {lat:6.2f} µs/track ({rate:8.0f} tracks/sec)")


def test_trajectory_and_geofence_ingress_benchmarks():
    """Benchmark 60s trajectory projection and geofence ingress estimation."""
    sizes = [10, 50, 100, 500]
    results = {}

    geofence = Geofence(
        id="GEO-BENCH-1",
        name="Benchmark Zone",
        geometry={"type": "BBOX", "min_lat": 37.780, "max_lat": 37.800, "min_lon": -122.420, "max_lon": -122.400},
        enabled=True,
    )

    for size in sizes:
        tracks_data = []
        for i in range(size):
            pts = _generate_synthetic_track_history(f"TRK-{i}", count=15)
            feat = extract_kinematic_features(pts)
            tracks_data.append((f"TRK-{i}", pts, feat))

        t_start = time.perf_counter()
        for track_id, pts, feat in tracks_data:
            last = pts[-1]
            traj = predict_trajectory(
                track_id=track_id,
                current_lat=last.latitude,
                current_lon=last.longitude,
                current_alt=last.altitude or 100.0,
                speed_mps=feat.speed_mps,
                heading_deg=feat.heading_deg or 45.0,
                turn_rate_dps=feat.turn_rate_dps,
                acceleration_mps2=feat.acceleration_mps2,
                vertical_speed_mps=feat.vertical_speed_mps,
                horizon_seconds=60.0,
                step_interval_seconds=5.0,
            )
            estimate_geofence_ingress(
                track_id=track_id,
                trajectory=traj,
                geofences=[geofence],
                current_lat=last.latitude,
                current_lon=last.longitude,
            )
        t_elapsed = time.perf_counter() - t_start

        avg_latency_us = (t_elapsed / size) * 1_000_000
        throughput = size / t_elapsed
        results[size] = (avg_latency_us, throughput)

        # Invariant: Trajectory + Ingress must take less than 1000 µs (1ms)
        assert avg_latency_us < 1000.0, f"Trajectory prediction for batch size {size} took {avg_latency_us:.2f}µs"

    print("\n--- Trajectory Prediction & Ingress Benchmarks ---")
    for size, (lat, rate) in results.items():
        print(f"Batch {size:3d} tracks: {lat:6.2f} µs/track ({rate:8.0f} tracks/sec)")


def test_end_to_end_single_track_evaluation_latency():
    """Verify single track end-to-end evaluation latency is sub-millisecond."""
    pts = _generate_synthetic_track_history("TRK-E2E", count=25)
    geofence = Geofence(
        id="GEO-E2E-1",
        name="Sector Alpha",
        geometry={"type": "BBOX", "min_lat": 37.780, "max_lat": 37.800, "min_lon": -122.420, "max_lon": -122.400},
        enabled=True,
    )

    iterations = 200
    t_start = time.perf_counter()
    for _ in range(iterations):
        feat = extract_kinematic_features(pts)
        conf = compute_sensor_confidence(provenance="RADAR", source_count=2, speed_variance=feat.speed_variance)
        evaluate_anomaly("TRK-E2E", feat, conf)
        traj = predict_trajectory(
            track_id="TRK-E2E",
            current_lat=pts[-1].latitude,
            current_lon=pts[-1].longitude,
            current_alt=pts[-1].altitude or 100.0,
            speed_mps=feat.speed_mps,
            heading_deg=feat.heading_deg or 45.0,
            turn_rate_dps=feat.turn_rate_dps,
            acceleration_mps2=feat.acceleration_mps2,
            vertical_speed_mps=feat.vertical_speed_mps,
            horizon_seconds=60.0,
            step_interval_seconds=5.0,
        )
        estimate_geofence_ingress(
            track_id="TRK-E2E",
            trajectory=traj,
            geofences=[geofence],
            current_lat=pts[-1].latitude,
            current_lon=pts[-1].longitude,
        )
    t_elapsed = time.perf_counter() - t_start
    avg_latency_ms = (t_elapsed / iterations) * 1000

    print(f"\n--- End-to-End Evaluation Latency: {avg_latency_ms:.3f} ms per track ---")
    assert avg_latency_ms < 2.0, f"End-to-end evaluation must be sub-2ms, took {avg_latency_ms:.3f}ms"
