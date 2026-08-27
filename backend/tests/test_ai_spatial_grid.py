"""Comprehensive Unit Tests & Performance Benchmark Suite for SpatialHashGrid.

Stage AI3-A — Spatial Hash Grid & Neighbor Query Engine.

Verifies:
- 25+ isolated boundary, geometry, antimeridian, and update tests.
- Core Correctness Invariant: ZERO false negatives for any track within <= 500m.
- Scaling & Candidate-Pair Reduction Benchmarks (100, 500, 1,000, 5,000 tracks).
"""

from datetime import UTC, datetime
import math
import time
import pytest

from ai.correlation.grouping import TrackObservation
from ai.correlation.spatial_grid import (
    DEFAULT_CELL_SIZE_METERS,
    SpatialGridConfig,
    SpatialHashGrid,
    normalize_latitude,
    normalize_longitude,
)
from ai.features.kinematics import haversine_distance


class TestSpatialHashGridUnit:
    """Isolated unit tests covering all edge cases, geometries, and lifecycle states."""

    def test_01_empty_grid(self) -> None:
        """Test 1: Empty grid initial state and queries."""
        grid = SpatialHashGrid()
        assert grid.track_count == 0
        assert grid.cell_count == 0
        assert grid.get_all_track_ids() == []
        assert grid.get_candidate_neighbors("TRK-NONE") == []
        assert grid.get_cell("TRK-NONE") is None

    def test_02_single_insertion(self) -> None:
        """Test 2: Single track insertion."""
        grid = SpatialHashGrid()
        cell = grid.insert("TRK-01", 37.7749, -122.4194)
        assert isinstance(cell, tuple)
        assert len(cell) == 2
        assert grid.track_count == 1
        assert grid.cell_count == 1
        assert grid.get_all_track_ids() == ["TRK-01"]
        assert grid.get_cell("TRK-01") == cell
        assert grid.get_candidate_neighbors("TRK-01") == []

    def test_03_multiple_tracks_in_same_cell(self) -> None:
        """Test 3: Multiple tracks occupying the same cell discover each other."""
        grid = SpatialHashGrid()
        grid.insert("T1", 37.7749, -122.4194)
        grid.insert("T2", 37.77491, -122.41941)
        grid.insert("T3", 37.77492, -122.41942)

        assert grid.track_count == 3
        assert grid.cell_count == 1

        assert grid.get_candidate_neighbors("T1") == ["T2", "T3"]
        assert grid.get_candidate_neighbors("T2") == ["T1", "T3"]
        assert grid.get_candidate_neighbors("T3") == ["T1", "T2"]

    def test_04_neighbor_cell_discovery_cardinal(self) -> None:
        """Test 4: Tracks in adjacent cardinal cells (North, South, East, West) are found."""
        grid = SpatialHashGrid(SpatialGridConfig(cell_size_meters=500.0))
        # Center track
        grid.insert("CENTER", 37.7749, -122.4194)

        # North offset ~ 400m (~0.0036 deg)
        grid.insert("NORTH", 37.7749 + 0.0036, -122.4194)
        # South offset ~ 400m
        grid.insert("SOUTH", 37.7749 - 0.0036, -122.4194)
        # East offset ~ 400m (~0.0045 deg at 37.7N)
        grid.insert("EAST", 37.7749, -122.4194 + 0.0045)
        # West offset ~ 400m
        grid.insert("WEST", 37.7749, -122.4194 - 0.0045)

        neighbors = grid.get_candidate_neighbors("CENTER")
        for expected in ["EAST", "NORTH", "SOUTH", "WEST"]:
            assert expected in neighbors

    def test_05_diagonal_neighbor_discovery(self) -> None:
        """Test 5: Tracks in diagonal neighbor cells (NE, NW, SE, SW) are found."""
        grid = SpatialHashGrid(SpatialGridConfig(cell_size_meters=500.0))
        grid.insert("CENTER", 37.7749, -122.4194)

        grid.insert("NE", 37.7749 + 0.0025, -122.4194 + 0.0025)
        grid.insert("NW", 37.7749 + 0.0025, -122.4194 - 0.0025)
        grid.insert("SE", 37.7749 - 0.0025, -122.4194 + 0.0025)
        grid.insert("SW", 37.7749 - 0.0025, -122.4194 - 0.0025)

        neighbors = grid.get_candidate_neighbors("CENTER")
        for expected in ["NE", "NW", "SE", "SW"]:
            assert expected in neighbors

    def test_06_track_update_within_same_cell(self) -> None:
        """Test 6: Updating track within the same cell preserves cell index and updates coords."""
        grid = SpatialHashGrid()
        c1 = grid.insert("T1", 37.77490, -122.41940)
        c2 = grid.update("T1", 37.77491, -122.41941)

        assert c1 == c2
        assert grid.track_count == 1
        assert grid.cell_count == 1
        assert grid.get_track_coords("T1") == (37.77491, -122.41941)

    def test_07_track_update_across_cell_boundary(self) -> None:
        """Test 7: Moving track to a distant cell cleanly vacates old cell and occupies new cell."""
        grid = SpatialHashGrid()
        c1 = grid.insert("T1", 37.7749, -122.4194)
        c2 = grid.update("T1", 38.5000, -121.5000)

        assert c1 != c2
        assert grid.track_count == 1
        assert grid.cell_count == 1  # Old cell deleted because empty
        assert grid.get_cell("T1") == c2
        assert grid.get_cell_tracks(c1[0], c1[1]) == []
        assert grid.get_cell_tracks(c2[0], c2[1]) == ["T1"]

    def test_08_track_removal(self) -> None:
        """Test 8: Removing track removes all references and deletes empty cell."""
        grid = SpatialHashGrid()
        c = grid.insert("T1", 37.7749, -122.4194)
        assert grid.remove("T1") is True

        assert grid.track_count == 0
        assert grid.cell_count == 0
        assert grid.get_cell("T1") is None
        assert grid.get_candidate_neighbors("T1") == []

    def test_09_unknown_track_removal(self) -> None:
        """Test 9: Removing unknown track safely returns False."""
        grid = SpatialHashGrid()
        assert grid.remove("NONEXISTENT") is False

    def test_10_duplicate_insertion_behavior(self) -> None:
        """Test 10: Re-inserting existing track updates it without duplicating entries."""
        grid = SpatialHashGrid()
        grid.insert("T1", 37.7749, -122.4194)
        grid.insert("T1", 37.7749, -122.4194)
        grid.insert("T1", 37.7750, -122.4195)

        assert grid.track_count == 1
        assert grid.get_all_track_ids() == ["T1"]

    def test_11_negative_latitude(self) -> None:
        """Test 11: Southern hemisphere indexing (Sydney, Australia)."""
        grid = SpatialHashGrid()
        c1 = grid.insert("SYD-1", -33.8688, 151.2093)
        c2 = grid.insert("SYD-2", -33.8690, 151.2095)

        assert grid.track_count == 2
        assert grid.get_candidate_neighbors("SYD-1") == ["SYD-2"]

    def test_12_negative_longitude(self) -> None:
        """Test 12: Western hemisphere indexing (San Francisco, USA)."""
        grid = SpatialHashGrid()
        grid.insert("SF-1", 37.7749, -122.4194)
        grid.insert("SF-2", 37.7750, -122.4195)

        assert grid.get_candidate_neighbors("SF-1") == ["SF-2"]

    def test_13_extreme_pm_180_longitude(self) -> None:
        """Test 13: Normalization and cell lookup for exact +/-180 longitude boundaries."""
        assert normalize_longitude(180.0) == -180.0
        assert normalize_longitude(-180.0) == -180.0
        assert normalize_longitude(180.5) == -179.5
        assert normalize_longitude(-180.5) == 179.5

        grid = SpatialHashGrid()
        c_pos = grid.insert("T-POS", 0.0, 180.0)
        c_neg = grid.insert("T-NEG", 0.0, -180.0)
        # Both represent the exact antimeridian line
        assert c_pos == c_neg

    def test_14_antimeridian_neighbors(self) -> None:
        """Test 14: Tracks on opposite sides of the +/-180° antimeridian correctly discover each other."""
        grid = SpatialHashGrid(SpatialGridConfig(cell_size_meters=500.0))
        # Track A is at +179.998° (East hemisphere edge)
        grid.insert("EAST-EDGE", 10.0, 179.998)
        # Track B is at -179.998° (West hemisphere edge, physical separation ~437m)
        grid.insert("WEST-EDGE", 10.0, -179.998)

        dist = haversine_distance(10.0, 179.998, 10.0, -179.998)
        assert dist < 500.0, f"Expected physical distance < 500m, got {dist:.1f}m"

        assert "WEST-EDGE" in grid.get_candidate_neighbors("EAST-EDGE")
        assert "EAST-EDGE" in grid.get_candidate_neighbors("WEST-EDGE")

    def test_15_equator_behavior(self) -> None:
        """Test 15: Exact equator (lat = 0.0) quantization."""
        grid = SpatialHashGrid()
        grid.insert("EQ-1", 0.0, 10.0)
        grid.insert("EQ-2", 0.001, 10.001)

        assert grid.get_candidate_neighbors("EQ-1") == ["EQ-2"]

    def test_16_latitude_30_behavior(self) -> None:
        """Test 16: 30° latitude quantization."""
        grid = SpatialHashGrid()
        grid.insert("L30-1", 30.0, 45.0)
        grid.insert("L30-2", 30.002, 45.002)

        assert grid.get_candidate_neighbors("L30-1") == ["L30-2"]

    def test_17_latitude_60_behavior(self) -> None:
        """Test 17: 60° latitude quantization (where cos(60) = 0.5 doubles longitudinal degrees/meter)."""
        grid = SpatialHashGrid()
        grid.insert("L60-1", 60.0, 10.0)
        grid.insert("L60-2", 60.002, 10.004)  # ~300m apart

        dist = haversine_distance(60.0, 10.0, 60.002, 10.004)
        assert dist < 500.0

        assert grid.get_candidate_neighbors("L60-1") == ["L60-2"]

    def test_18_latitude_80_behavior(self) -> None:
        """Test 18: High polar latitude (80°N)."""
        grid = SpatialHashGrid()
        grid.insert("L80-1", 80.0, 0.0)
        grid.insert("L80-2", 80.001, 0.005)  # ~140m apart

        dist = haversine_distance(80.0, 0.0, 80.001, 0.005)
        assert dist < 500.0

        assert grid.get_candidate_neighbors("L80-1") == ["L80-2"]

    def test_19_exact_cell_boundary_behavior(self) -> None:
        """Test 19: Coordinate precisely on cell boundary."""
        grid = SpatialHashGrid()
        row_delta = grid._delta_lat_adj
        # Position at exactly boundary line
        grid.insert("BND-1", -90.0 + row_delta, 0.0)
        grid.insert("BND-2", -90.0 + row_delta + 0.0001, 0.0)

        assert "BND-2" in grid.get_candidate_neighbors("BND-1")

    def test_20_deterministic_neighbor_ordering(self) -> None:
        """Test 20: Candidate neighbors are always returned in deterministic lexicographical order."""
        grid = SpatialHashGrid()
        grid.insert("CENTER", 37.7749, -122.4194)
        grid.insert("Z_TRACK", 37.7749, -122.4193)
        grid.insert("A_TRACK", 37.7749, -122.4195)
        grid.insert("M_TRACK", 37.7750, -122.4194)

        neighbors = grid.get_candidate_neighbors("CENTER")
        assert neighbors == ["A_TRACK", "M_TRACK", "Z_TRACK"]

    def test_21_no_stale_memberships_after_update(self) -> None:
        """Test 21: Track moving away from neighbor is no longer returned as neighbor."""
        grid = SpatialHashGrid()
        grid.insert("T1", 37.7749, -122.4194)
        grid.insert("T2", 37.7750, -122.4195)
        assert grid.get_candidate_neighbors("T1") == ["T2"]

        # Move T2 to London
        grid.update("T2", 51.5074, -0.1278)
        assert grid.get_candidate_neighbors("T1") == []
        assert grid.get_candidate_neighbors("T2") == []

    def test_22_no_stale_memberships_after_removal(self) -> None:
        """Test 22: Removed track is no longer returned as candidate for remaining tracks."""
        grid = SpatialHashGrid()
        grid.insert("T1", 37.7749, -122.4194)
        grid.insert("T2", 37.7750, -122.4195)
        grid.remove("T2")

        assert grid.get_candidate_neighbors("T1") == []

    def test_23_query_radius_candidates(self) -> None:
        """Test 23: query_radius_candidates by arbitrary coordinate."""
        grid = SpatialHashGrid()
        grid.insert("T1", 37.7749, -122.4194)
        grid.insert("T2", 37.7760, -122.4180)
        grid.insert("FAR", 38.5000, -121.5000)

        cands = grid.query_radius_candidates(37.7750, -122.4190, radius_meters=600.0)
        assert "T1" in cands
        assert "T2" in cands
        assert "FAR" not in cands

    def test_24_clear_resets_all_state(self) -> None:
        """Test 24: clear() empties all internal indices."""
        grid = SpatialHashGrid()
        grid.insert("T1", 37.7749, -122.4194)
        grid.insert("T2", 37.7750, -122.4195)
        grid.clear()

        assert grid.track_count == 0
        assert grid.cell_count == 0
        assert grid.get_all_track_ids() == []

    def test_25_observation_caching(self) -> None:
        """Test 25: Optional TrackObservation caching and retrieval."""
        grid = SpatialHashGrid()
        obs = TrackObservation(
            id="T-OBS",
            latitude=37.7749,
            longitude=-122.4194,
            altitude=120.0,
            velocity=25.0,
            heading=90.0,
            confidence=0.95,
            timestamp=datetime(2026, 8, 27, 0, 0, 0, tzinfo=UTC),
        )
        grid.insert(obs.id, obs.latitude, obs.longitude, observation=obs)
        cached = grid.get_track_observation("T-OBS")
        assert cached is not None
        assert cached.id == "T-OBS"
        assert cached.altitude == 120.0
        assert cached.velocity == 25.0


class TestSpatialGridCorrectnessInvariant:
    """Core correctness invariant: ZERO FALSE NEGATIVES for any pair with Haversine distance <= 500m."""

    @pytest.mark.parametrize("center_lat,center_lon", [
        (0.0, 0.0),          # Equator / Prime Meridian
        (0.0, 179.999),      # Equator / Antimeridian
        (37.7749, -122.4194),# Mid-latitude (San Francisco)
        (-33.8688, 151.2093),# Southern Hemisphere (Sydney)
        (60.0, 10.0),        # High Latitude (Oslo)
        (80.0, -179.998),    # High Polar / Antimeridian
        (-80.0, 45.0),       # South Polar
    ])
    def test_zero_false_negatives_invariant(self, center_lat: float, center_lon: float) -> None:
        """Generate a cluster of tracks at various distances (from 10m to 1200m).
        Verify: Every pair with distance <= 500.0m is in candidate neighbors.
        """
        cell_size = 500.0
        grid = SpatialHashGrid(SpatialGridConfig(cell_size_meters=cell_size))

        # Generate 40 synthetic tracks around center_lat, center_lon
        tracks: list[tuple[str, float, float]] = []
        for i in range(40):
            # Angular offset in bearing and distance (0 to 1200 meters)
            bearing_rad = (i * 9.0) * math.pi / 180.0
            dist_m = 25.0 * i  # 0m, 25m, 50m, ..., 975m

            # Approximate lat/lon offset
            d_lat = (dist_m * math.cos(bearing_rad)) / 111195.0
            cos_lat = max(0.0001, math.cos(math.radians(center_lat)))
            d_lon = (dist_m * math.sin(bearing_rad)) / (111195.0 * cos_lat)

            lat = normalize_latitude(center_lat + d_lat)
            lon = normalize_longitude(center_lon + d_lon)
            tid = f"TRK-{i:03d}"
            tracks.append((tid, lat, lon))
            grid.insert(tid, lat, lon)

        # Pairwise verification against ground-truth Haversine distance
        for i, (id_a, lat_a, lon_a) in enumerate(tracks):
            candidates = set(grid.get_candidate_neighbors(id_a))

            for j, (id_b, lat_b, lon_b) in enumerate(tracks):
                if i == j:
                    continue

                true_dist = haversine_distance(lat_a, lon_a, lat_b, lon_b)

                if true_dist <= cell_size:
                    # Invariant: Must NOT be missed (ZERO FALSE NEGATIVES)
                    assert id_b in candidates, (
                        f"FAILED INVARIANT at ({center_lat}, {center_lon}): "
                        f"Track {id_b} (dist={true_dist:.1f}m <= {cell_size}m) "
                        f"was missing from candidate neighbors of {id_a}!"
                    )


class TestSpatialGridPerformanceBenchmark:
    """Scale and candidate reduction benchmark across 100, 500, 1,000, and 5,000 synthetic tracks."""

    TRACK_SCALES = [100, 500, 1000, 5000]

    def test_benchmark_candidate_reduction_and_throughput(self) -> None:
        """Measure insertion time, query time, and candidate-pair reduction vs N(N-1)/2 all-pairs."""
        print("\n" + "=" * 76)
        print("  AEROGUARD AI3-A SPATIAL HASH GRID BENCHMARK & CANDIDATE REDUCTION")
        print("  Local Software Microbenchmark — Pure Python 3.12")
        print("=" * 76)

        for n in self.TRACK_SCALES:
            grid = SpatialHashGrid(SpatialGridConfig(cell_size_meters=500.0))

            # Sector distribution: tracks dispersed over a 20km x 20km sector (approx 40x40 grid cells)
            # with 4-track local clusters to simulate realistic airspace formations
            base_lat = 37.7749
            base_lon = -122.4194

            tracks: list[tuple[str, float, float]] = []
            for i in range(n):
                cluster_id = i // 4
                in_cluster = i % 4
                # Spread clusters across ~20km (0.18 degrees)
                grid_x = (cluster_id % 20) * 0.009
                grid_y = (cluster_id // 20) * 0.009
                cluster_lat = base_lat + grid_y + (in_cluster * 0.0002)
                cluster_lon = base_lon + grid_x + (in_cluster * 0.0002)
                tracks.append((f"T-{i:04d}", cluster_lat, cluster_lon))

            # 1. Insertion Benchmark
            t0 = time.perf_counter()
            for tid, lat, lon in tracks:
                grid.insert(tid, lat, lon)
            t_insert_ms = (time.perf_counter() - t0) * 1000.0

            # 2. Candidate Neighbor Query Benchmark
            t0 = time.perf_counter()
            total_candidate_pairs = 0
            for tid, _, _ in tracks:
                cands = grid.get_candidate_neighbors(tid)
                total_candidate_pairs += len(cands)
            t_query_ms = (time.perf_counter() - t0) * 1000.0

            # Total unique unordered candidate pairs = total_candidate_pairs / 2
            unique_candidate_pairs = total_candidate_pairs // 2
            all_pairs = (n * (n - 1)) // 2
            reduction_factor = all_pairs / max(1, unique_candidate_pairs)
            pct_saved = ((all_pairs - unique_candidate_pairs) / all_pairs) * 100.0

            print(
                f"  [N={n:5d}] Insert: {t_insert_ms:6.2f}ms ({t_insert_ms*1000/n:5.1f}µs/trk) | "
                f"Query: {t_query_ms:6.2f}ms ({t_query_ms*1000/n:5.1f}µs/trk) | "
                f"Pairs: {unique_candidate_pairs:7d} vs {all_pairs:10d} all-pairs | "
                f"Reduction: {reduction_factor:6.1f}x ({pct_saved:5.1f}% saved)"
            )

            # Assertions on complexity reduction
            assert unique_candidate_pairs < all_pairs
            if n >= 500:
                assert reduction_factor > 10.0, f"Expected >10x reduction for N={n}, got {reduction_factor:.1f}x"
