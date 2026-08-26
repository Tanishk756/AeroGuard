"""Unit tests for deterministic simulation clock, trajectories, synthetic sensors, and simulation engine."""

from datetime import UTC, datetime
import pytest

from app.schemas.scenario import (
    ScenarioConfiguration,
    ScenarioSensorDefinition,
    ScenarioTargetDefinition,
    ScenarioWaypoint,
)
from app.simulation.clock import SimulationClock
from app.simulation.engine import SimulationEngine
from app.simulation.sensors import SyntheticSensor, is_bearing_in_fov
from app.simulation.trajectories import (
    advance_position_wgs84,
    calculate_bearing_deg,
    haversine_distance,
    TrajectoryEngine,
)


def test_simulation_clock_discrete_stepping():
    start = datetime(2026, 6, 1, 12, 0, 0, tzinfo=UTC)
    clock = SimulationClock(start_time=start, tick_rate_hz=2.0)

    assert clock.current_time == start
    assert clock.tick_count == 0
    assert clock.dt_seconds == 0.5
    assert clock.is_running is True

    # Step 1 tick (0.5s)
    sim_time, ticks = clock.step(1)
    assert ticks == 1
    assert sim_time == datetime(2026, 6, 1, 12, 0, 0, 500000, tzinfo=UTC)

    # Step 5 ticks (2.5s)
    sim_time, ticks = clock.step(5)
    assert ticks == 6
    assert sim_time == datetime(2026, 6, 1, 12, 0, 3, tzinfo=UTC)

    # Pause and resume
    clock.pause()
    assert clock.is_paused is True
    assert clock.is_running is False

    clock.resume()
    assert clock.is_paused is False
    assert clock.is_running is True

    # Reset
    clock.reset()
    assert clock.current_time == start
    assert clock.tick_count == 0

    # Stop
    clock.stop()
    assert clock.is_stopped is True
    with pytest.raises(RuntimeError, match="Cannot step a stopped simulation clock"):
        clock.step(1)


def test_trajectory_haversine_and_bearing():
    # Equator to 1 degree North (~111.19 km)
    dist = haversine_distance(0.0, 0.0, 1.0, 0.0)
    assert 111000.0 < dist < 111500.0

    # Bearing due North
    bearing_n = calculate_bearing_deg(0.0, 0.0, 1.0, 0.0)
    assert abs(bearing_n - 0.0) < 1e-4

    # Bearing due East
    bearing_e = calculate_bearing_deg(0.0, 0.0, 0.0, 1.0)
    assert abs(bearing_e - 90.0) < 1e-4

    # Advance position 100 m due East
    lat_new, lon_new = advance_position_wgs84(0.0, 0.0, 90.0, 100.0, 1.0)
    assert abs(lat_new - 0.0) < 1e-5
    assert lon_new > 0.0


def test_trajectory_engine_constant_velocity():
    targets = [
        ScenarioTargetDefinition(
            target_id="tgt-cv-01",
            initial_latitude=37.7749,
            initial_longitude=-122.4194,
            initial_altitude=150.0,
            velocity=20.0,  # 20 m/s
            heading=0.0,    # Due North
            classification="uav",
        )
    ]
    engine = TrajectoryEngine(targets)
    # Advance 10 seconds (200 meters North)
    updated = engine.advance(10.0)

    assert len(updated) == 1
    t = updated[0]
    assert t.target_id == "tgt-cv-01"
    assert t.latitude > 37.7749  # Moved North
    assert abs(t.longitude - (-122.4194)) < 1e-4
    assert t.altitude == 150.0
    assert t.velocity == 20.0
    assert t.heading == 0.0


def test_trajectory_engine_waypoint_navigation():
    targets = [
        ScenarioTargetDefinition(
            target_id="tgt-wp-01",
            initial_latitude=37.0,
            initial_longitude=-122.0,
            initial_altitude=100.0,
            velocity=25.0,
            heading=0.0,
            waypoints=[
                ScenarioWaypoint(latitude=37.001, longitude=-122.0, altitude=200.0, speed=25.0),
                ScenarioWaypoint(latitude=37.001, longitude=-121.999, altitude=300.0, speed=30.0),
            ],
            classification="fixed_wing",
        )
    ]
    engine = TrajectoryEngine(targets)

    # Step until reaching first waypoint (~111 meters North, approx 5 seconds at 25 m/s)
    for _ in range(6):
        engine.advance(1.0)

    t = engine.get_target_state("tgt-wp-01")
    assert t is not None
    # Should have reached or be near first waypoint and adjusted heading towards second waypoint (East)
    assert t.waypoint_index >= 1
    assert t.altitude > 150.0


def test_synthetic_sensor_fov_and_range_gating():
    assert is_bearing_in_fov(45.0, 0.0, 90.0) is True
    assert is_bearing_in_fov(95.0, 0.0, 90.0) is False
    assert is_bearing_in_fov(10.0, 350.0, 30.0) is True  # Across 0 wrap-around
    assert is_bearing_in_fov(30.0, 350.0, 30.0) is False

    sensor_def = ScenarioSensorDefinition(
        sensor_id="radar-01",
        modality="radar",
        latitude=37.7749,
        longitude=-122.4194,
        altitude=10.0,
        range_meters=1000.0,
        detection_probability=1.0,
        position_uncertainty_meters=5.0,
        fov_azimuth_start_deg=0.0,
        fov_azimuth_span_deg=180.0,  # North-East-South
    )
    sensor = SyntheticSensor(sensor_def)

    import random
    prng = random.Random(42)
    now = datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)

    # Target within range and FOV (due North 200m)
    target_in = TrajectoryEngine([
        ScenarioTargetDefinition(
            target_id="tgt-in",
            initial_latitude=37.7767,
            initial_longitude=-122.4194,
            initial_altitude=50.0,
            velocity=10.0,
            heading=0.0,
        )
    ]).get_target_state("tgt-in")
    assert target_in is not None

    det = sensor.evaluate_target(target_in, now, 1, prng)
    assert det is not None
    assert det.sensor_id == "radar-01"
    assert det.classification is None
    assert det.source_type == "radar"

    # Target out of range (5000m North)
    target_out_range = TrajectoryEngine([
        ScenarioTargetDefinition(
            target_id="tgt-out-range",
            initial_latitude=37.8200,
            initial_longitude=-122.4194,
            initial_altitude=50.0,
            velocity=10.0,
            heading=0.0,
        )
    ]).get_target_state("tgt-out-range")
    assert target_out_range is not None

    det_out = sensor.evaluate_target(target_out_range, now, 1, prng)
    assert det_out is None

    # Target in range but out of FOV (West 200m -> bearing ~270)
    target_out_fov = TrajectoryEngine([
        ScenarioTargetDefinition(
            target_id="tgt-out-fov",
            initial_latitude=37.7749,
            initial_longitude=-122.4217,
            initial_altitude=50.0,
            velocity=10.0,
            heading=0.0,
        )
    ]).get_target_state("tgt-out-fov")
    assert target_out_fov is not None

    det_fov = sensor.evaluate_target(target_out_fov, now, 1, prng)
    assert det_fov is None


def test_simulation_engine_deterministic_repeatability():
    config = ScenarioConfiguration(
        seed=12345,
        duration_seconds=60.0,
        tick_rate_hz=1.0,
        targets=[
            ScenarioTargetDefinition(
                target_id="tgt-01",
                initial_latitude=37.7749,
                initial_longitude=-122.4194,
                initial_altitude=100.0,
                velocity=15.0,
                heading=45.0,
                classification="uav",
            ),
            ScenarioTargetDefinition(
                target_id="tgt-02",
                initial_latitude=37.7755,
                initial_longitude=-122.4180,
                initial_altitude=80.0,
                velocity=10.0,
                heading=180.0,
                classification="commercial",
            ),
        ],
        sensors=[
            ScenarioSensorDefinition(
                sensor_id="sensor-radar",
                modality="radar",
                latitude=37.7740,
                longitude=-122.4200,
                range_meters=5000.0,
                detection_probability=0.95,
                position_uncertainty_meters=4.0,
            ),
            ScenarioSensorDefinition(
                sensor_id="sensor-optical",
                modality="optical",
                latitude=37.7750,
                longitude=-122.4190,
                range_meters=3000.0,
                detection_probability=0.90,
                position_uncertainty_meters=2.0,
            ),
        ],
    )

    # Run 1
    engine1 = SimulationEngine(config)
    dets1 = engine1.step(ticks=10)

    # Run 2 with fresh engine and same seed
    engine2 = SimulationEngine(config)
    dets2 = engine2.step(ticks=10)

    assert len(dets1) == len(dets2)
    assert len(dets1) > 0

    for d1, d2 in zip(dets1, dets2, strict=True):
        assert d1.source_detection_id == d2.source_detection_id
        assert d1.timestamp == d2.timestamp
        assert d1.sensor_id == d2.sensor_id
        assert d1.latitude == d2.latitude
        assert d1.longitude == d2.longitude
        assert d1.altitude == d2.altitude
        assert d1.velocity == d2.velocity
        assert d1.heading == d2.heading
        assert d1.confidence == d2.confidence
