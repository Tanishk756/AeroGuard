"""Association gating criteria and validation."""

from dataclasses import dataclass

from app.models.detection import Detection
from app.models.track import Track, TrackState
from app.tracking.association import angular_difference, haversine_distance


@dataclass(frozen=True)
class GatingConfig:
    maximum_time_delta: float = 10.0
    maximum_horizontal_distance: float = 500.0
    maximum_vertical_distance: float = 150.0
    stale_spatial_multiplier: float = 1.5
    maximum_velocity_delta: float = 50.0
    maximum_heading_delta: float = 90.0


@dataclass(frozen=True)
class GateResult:
    passed: bool
    reason: str
    horizontal_distance: float
    vertical_distance: float | None
    time_delta: float


class AssociationGate:
    def __init__(self, config: GatingConfig | None = None):
        self.config = config or GatingConfig()

    def evaluate(self, detection: Detection, track: Track) -> GateResult:
        time_delta = (detection.timestamp - track.last_seen_at).total_seconds()
        abs_time_delta = abs(time_delta)

        h_dist = haversine_distance(
            detection.latitude,
            detection.longitude,
            track.latitude,
            track.longitude,
        )

        v_dist: float | None = None
        if detection.altitude is not None and track.altitude is not None:
            v_dist = abs(detection.altitude - track.altitude)

        if abs_time_delta > self.config.maximum_time_delta:
            return GateResult(
                passed=False,
                reason=f"Time delta {abs_time_delta:.2f}s exceeds gate {self.config.maximum_time_delta:.2f}s",
                horizontal_distance=h_dist,
                vertical_distance=v_dist,
                time_delta=time_delta,
            )

        multiplier = (
            self.config.stale_spatial_multiplier
            if track.state == TrackState.STALE
            else 1.0
        )
        max_h = self.config.maximum_horizontal_distance * multiplier
        max_v = self.config.maximum_vertical_distance * multiplier

        if h_dist > max_h:
            return GateResult(
                passed=False,
                reason=f"Horizontal distance {h_dist:.2f}m exceeds gate {max_h:.2f}m",
                horizontal_distance=h_dist,
                vertical_distance=v_dist,
                time_delta=time_delta,
            )

        if v_dist is not None and v_dist > max_v:
            return GateResult(
                passed=False,
                reason=f"Vertical distance {v_dist:.2f}m exceeds gate {max_v:.2f}m",
                horizontal_distance=h_dist,
                vertical_distance=v_dist,
                time_delta=time_delta,
            )

        if detection.velocity is not None and track.velocity is not None:
            v_diff = abs(detection.velocity - track.velocity)
            if v_diff > self.config.maximum_velocity_delta:
                return GateResult(
                    passed=False,
                    reason=f"Velocity delta {v_diff:.2f}m/s exceeds gate {self.config.maximum_velocity_delta:.2f}m/s",
                    horizontal_distance=h_dist,
                    vertical_distance=v_dist,
                    time_delta=time_delta,
                )

        if detection.heading is not None and track.heading is not None:
            h_diff = angular_difference(detection.heading, track.heading)
            if h_diff > self.config.maximum_heading_delta:
                return GateResult(
                    passed=False,
                    reason=f"Heading delta {h_diff:.2f}deg exceeds gate {self.config.maximum_heading_delta:.2f}deg",
                    horizontal_distance=h_dist,
                    vertical_distance=v_dist,
                    time_delta=time_delta,
                )

        return GateResult(
            passed=True,
            reason="PASSED",
            horizontal_distance=h_dist,
            vertical_distance=v_dist,
            time_delta=time_delta,
        )
