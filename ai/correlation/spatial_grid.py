"""Deterministic Pure-Python Spatial Hash Grid for Multi-Track Neighborhood Indexing.

AeroGuard Stage AI3-A — Spatial Hash Grid & Neighbor Query Engine.

PURPOSE
-------
Provides an O(1) average insertion, update, removal, and local 3x3 neighborhood
candidate query index. Replaces O(N^2) pairwise all-pairs distance loops in multi-track
grouping with localized candidate retrieval.

MATHEMATICAL QUANTIZATION & PROJECTION MODEL
--------------------------------------------
1. Earth Model:
   Spherical WGS-84 radius: R = 6,371,000.0 meters (matching Haversine in kinematics.py).
   Meters per degree latitude: M_lat = (pi * R) / 180.0 ≈ 111,194.9266 m/deg.

2. Latitude Quantization:
   Row height in degrees: delta_lat = cell_size_meters / M_lat.
   Row index: row = floor((lat + 90.0) / delta_lat), bounded in [0, N_rows - 1].

3. Longitude Quantization with Latitude Scaling:
   Physical distance per degree longitude shrinks with cos(lat).
   To guarantee that a 3x3 cell neighborhood query covers at least cell_size_meters
   in all directions without false negatives, each latitude row `r` scales its column count:
     cos_max(r) = maximum cos(lat) within row `r`
     delta_lon(r) = delta_lat / max(0.0001, cos_max(r))
     N_cols(r) = max(1, ceil(360.0 / delta_lon(r)))
     delta_lon_adj(r) = 360.0 / N_cols(r)  (<= delta_lon(r))
     col(r, lon) = floor((lon + 180.0) / delta_lon_adj(r)) mod N_cols(r)

4. Antimeridian Handling:
   Longitudes wrap continuously around ±180.0° via modular arithmetic on N_cols(r).
   A track at +179.999° and a track at -179.999° share adjacent column indices.

5. Candidate Guarantee (Zero False Negatives Invariant):
   Any two tracks separated by horizontal Haversine distance <= cell_size_meters are
   guaranteed to be located in the same cell or in adjacent cells within the 3x3 neighborhood.
   SpatialHashGrid performs candidate reduction; exact distance/heading/velocity tests
   remain the responsibility of the domain grouping engine.

THREAD SAFETY
-------------
SpatialHashGrid is single-threaded / synchronous. It does not employ internal locking.
Thread-safe concurrent access should be managed by the calling service or wrapper.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
import math
from typing import Any

from ai.correlation.grouping import TrackObservation, to_track_observation
from ai.features.kinematics import EARTH_RADIUS_METERS

DEFAULT_CELL_SIZE_METERS: float = 500.0
METERS_PER_DEGREE_LAT: float = (math.pi * EARTH_RADIUS_METERS) / 180.0  # ≈ 111194.9266 m/deg


def normalize_longitude(lon: float) -> float:
    """Normalize longitude into standard [-180.0, 180.0) degrees."""
    lon_mod = (lon + 180.0) % 360.0
    if lon_mod < 0.0:
        lon_mod += 360.0
    return lon_mod - 180.0


def normalize_latitude(lat: float) -> float:
    """Clamp latitude into valid [-90.0, 90.0] degrees."""
    return max(-90.0, min(90.0, float(lat)))


@dataclass(frozen=True)
class SpatialGridConfig:
    """Configuration for spatial hash grid indexing."""

    cell_size_meters: float = DEFAULT_CELL_SIZE_METERS


class SpatialHashGrid:
    """Deterministic, pure-Python 2D spatial hash grid with latitude-scaled column quantization."""

    def __init__(self, config: SpatialGridConfig | None = None) -> None:
        self._config = config or SpatialGridConfig()
        self._cell_size_meters = max(10.0, float(self._config.cell_size_meters))

        # Latitude row parameters
        self._delta_lat: float = self._cell_size_meters / METERS_PER_DEGREE_LAT
        self._num_rows: int = max(1, math.ceil(180.0 / self._delta_lat))
        # Re-adjust delta_lat so exactly num_rows span 180 degrees
        self._delta_lat_adj: float = 180.0 / self._num_rows

        # Precompute per-row longitude column counts and widths
        self._row_cols: list[int] = [0] * self._num_rows
        self._row_delta_lon: list[float] = [0.0] * self._num_rows
        self._precompute_row_quantization()

        # Primary spatial index: (row, col) -> set of track_ids
        self._grid: dict[tuple[int, int], set[str]] = {}

        # Reverse indices for O(1) track lookup, update, and removal
        self._track_cell: dict[str, tuple[int, int]] = {}
        self._track_coords: dict[str, tuple[float, float]] = {}
        self._track_obs: dict[str, TrackObservation] = {}

    def _precompute_row_quantization(self) -> None:
        """Precompute longitude quantization parameters for all latitude rows."""
        for r in range(self._num_rows):
            lat_south = (r * self._delta_lat_adj) - 90.0
            lat_north = ((r + 1) * self._delta_lat_adj) - 90.0

            # Find maximum cos(lat) in this latitude row
            if lat_south <= 0.0 <= lat_north:
                cos_max = 1.0
            else:
                cos_south = math.cos(math.radians(lat_south))
                cos_north = math.cos(math.radians(lat_north))
                cos_max = max(cos_south, cos_north)

            # Clamp cos_max to avoid division by zero near poles
            cos_max_clamped = max(0.0001, cos_max)
            delta_lon_target = self._delta_lat_adj / cos_max_clamped
            n_cols = max(1, math.ceil(360.0 / delta_lon_target))

            self._row_cols[r] = n_cols
            self._row_delta_lon[r] = 360.0 / n_cols

    # ── Coordinate & Cell Conversion ──────────────────────────────────────────

    def get_cell_coords(self, latitude: float, longitude: float) -> tuple[int, int]:
        """Convert latitude and longitude into deterministic integer (row, col) cell coordinates."""
        lat = normalize_latitude(latitude)
        lon = normalize_longitude(longitude)

        # Row index in [0, num_rows - 1]
        row = int((lat + 90.0) / self._delta_lat_adj)
        row = max(0, min(self._num_rows - 1, row))

        # Column index in [0, row_cols[row] - 1]
        n_cols = self._row_cols[row]
        delta_lon = self._row_delta_lon[row]
        lon_360 = (lon + 180.0) % 360.0
        col = int(lon_360 / delta_lon) % n_cols

        return (row, col)

    def _get_col_in_row_for_lon(self, row: int, longitude: float) -> int:
        """Compute the column index in row `row` corresponding to a given longitude."""
        lon = normalize_longitude(longitude)
        n_cols = self._row_cols[row]
        delta_lon = self._row_delta_lon[row]
        lon_360 = (lon + 180.0) % 360.0
        return int(lon_360 / delta_lon) % n_cols

    # ── State Mutation API ───────────────────────────────────────────────────

    def insert(
        self,
        track_id: str,
        latitude: float,
        longitude: float,
        observation: Any = None,
    ) -> tuple[int, int]:
        """Insert a track into the spatial hash grid.
        
        If the track already exists, it is automatically updated to the new position.
        """
        tid = str(track_id)
        # If track exists, remove from previous cell first to prevent stale references
        if tid in self._track_cell:
            old_cell = self._track_cell[tid]
            if old_cell in self._grid:
                self._grid[old_cell].discard(tid)
                if not self._grid[old_cell]:
                    del self._grid[old_cell]

        lat = normalize_latitude(latitude)
        lon = normalize_longitude(longitude)
        cell = self.get_cell_coords(lat, lon)

        if cell not in self._grid:
            self._grid[cell] = set()
        self._grid[cell].add(tid)

        self._track_cell[tid] = cell
        self._track_coords[tid] = (lat, lon)

        if observation is not None:
            self._track_obs[tid] = to_track_observation(observation)

        return cell

    def update(
        self,
        track_id: str,
        latitude: float,
        longitude: float,
        observation: Any = None,
    ) -> tuple[int, int]:
        """Update an existing track's position (or insert if not present)."""
        return self.insert(track_id, latitude, longitude, observation)

    def remove(self, track_id: str) -> bool:
        """Remove a track from the spatial grid. Returns True if removed, False if not found."""
        tid = str(track_id)
        if tid not in self._track_cell:
            return False

        cell = self._track_cell.pop(tid)
        self._track_coords.pop(tid, None)
        self._track_obs.pop(tid, None)

        if cell in self._grid:
            self._grid[cell].discard(tid)
            if not self._grid[cell]:
                del self._grid[cell]

        return True

    def clear(self) -> None:
        """Clear all tracks and grid cells."""
        self._grid.clear()
        self._track_cell.clear()
        self._track_coords.clear()
        self._track_obs.clear()

    # ── Candidate Neighbor Queries ───────────────────────────────────────────

    def get_candidate_neighbors(self, track_id: str) -> list[str]:
        """Return deterministic sorted list of candidate neighbor track IDs in the 3x3 cell neighborhood.
        
        Excludes `track_id` itself. Returns empty list if `track_id` is not indexed.
        """
        tid = str(track_id)
        if tid not in self._track_cell:
            return []

        cell = self._track_cell[tid]
        lat, lon = self._track_coords[tid]
        center_row, _ = cell

        candidates: set[str] = set()

        # Inspect 3 rows: center_row - 1, center_row, center_row + 1
        for dr in (-1, 0, 1):
            r = center_row + dr
            if 0 <= r < self._num_rows:
                n_cols = self._row_cols[r]
                col_center = self._get_col_in_row_for_lon(r, lon)
                # Inspect 3 columns: col_center - 1, col_center, col_center + 1 (with antimeridian wrap)
                for dc in (-1, 0, 1):
                    c = (col_center + dc) % n_cols
                    cell_key = (r, c)
                    if cell_key in self._grid:
                        candidates.update(self._grid[cell_key])

        # Exclude self and return sorted list for determinism
        candidates.discard(tid)
        return sorted(candidates)

    def query_radius_candidates(
        self,
        latitude: float,
        longitude: float,
        radius_meters: float | None = None,
    ) -> list[str]:
        """Return deterministic sorted list of candidate track IDs within `radius_meters` of (lat, lon).
        
        If radius_meters is None, defaults to cell_size_meters (inspecting 3x3 neighborhood).
        """
        rad_m = max(1.0, float(radius_meters if radius_meters is not None else self._cell_size_meters))
        lat = normalize_latitude(latitude)
        lon = normalize_longitude(longitude)

        # Number of rows to inspect in each direction
        row_radius = max(1, math.ceil((rad_m / METERS_PER_DEGREE_LAT) / self._delta_lat_adj))
        center_row = int((lat + 90.0) / self._delta_lat_adj)
        center_row = max(0, min(self._num_rows - 1, center_row))

        candidates: set[str] = set()

        for dr in range(-row_radius, row_radius + 1):
            r = center_row + dr
            if 0 <= r < self._num_rows:
                n_cols = self._row_cols[r]
                delta_lon = self._row_delta_lon[r]
                col_center = self._get_col_in_row_for_lon(r, lon)

                # Column radius based on physical width of row
                col_radius = max(1, math.ceil(rad_m / (self._cell_size_meters)))
                for dc in range(-col_radius, col_radius + 1):
                    c = (col_center + dc) % n_cols
                    cell_key = (r, c)
                    if cell_key in self._grid:
                        candidates.update(self._grid[cell_key])

        return sorted(candidates)

    # ── Diagnostic & Inspection API ──────────────────────────────────────────

    @property
    def cell_size_meters(self) -> float:
        """Configured cell size in meters."""
        return self._cell_size_meters

    @property
    def track_count(self) -> int:
        """Total number of tracks currently indexed."""
        return len(self._track_cell)

    @property
    def cell_count(self) -> int:
        """Total number of non-empty grid cells."""
        return len(self._grid)

    def get_cell(self, track_id: str) -> tuple[int, int] | None:
        """Return the (row, col) cell coordinates of a track, or None if not found."""
        return self._track_cell.get(str(track_id))

    def get_track_coords(self, track_id: str) -> tuple[float, float] | None:
        """Return the (lat, lon) coordinates of a track, or None if not found."""
        return self._track_coords.get(str(track_id))

    def get_track_observation(self, track_id: str) -> TrackObservation | None:
        """Return the cached TrackObservation of a track, or None if not available."""
        return self._track_obs.get(str(track_id))

    def get_all_track_ids(self) -> list[str]:
        """Return deterministic sorted list of all indexed track IDs."""
        return sorted(self._track_cell.keys())

    def get_cell_tracks(self, row: int, col: int) -> list[str]:
        """Return deterministic sorted list of track IDs in cell (row, col)."""
        return sorted(self._grid.get((row, col), set()))

    def to_dict(self) -> dict[str, Any]:
        """Diagnostic summary of grid state."""
        return {
            "cell_size_meters": self._cell_size_meters,
            "track_count": self.track_count,
            "cell_count": self.cell_count,
            "num_rows": self._num_rows,
            "delta_lat_deg": round(self._delta_lat_adj, 6),
        }
