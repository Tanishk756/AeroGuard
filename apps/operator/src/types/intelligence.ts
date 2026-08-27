/**
 * AeroGuard Defensive AI & Kinematic Intelligence Types
 */

export type AnomalyCategory =
  | 'NORMAL'
  | 'UNUSUAL_KINEMATICS'
  | 'RAPID_ALTITUDE_CHANGE'
  | 'ERRATIC_HEADING'
  | 'EXCESSIVE_ACCELERATION'
  | 'LOITERING_PATTERN'
  | 'TRAJECTORY_DEVIATION';

export type AnomalySeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface KinematicFeatures {
  speed_mps: number;
  acceleration_mps2: number;
  vertical_speed_mps: number;
  heading_deg?: number | null;
  turn_rate_dps: number;
  speed_variance: number;
  altitude_variance: number;
  acceleration_variance: number;
  trajectory_curvature: number;
  loiter_radius_meters?: number | null;
  directional_consistency: number;
  sample_count: number;
  timespan_seconds: number;
}

export interface AnomalyFactor {
  name: string;
  score: number;
  weight: number;
  contribution: number;
  severity: AnomalySeverity;
  description: string;
}

export interface AnomalyAssessment {
  track_id: string;
  anomaly_score: number;
  anomaly_level: AnomalySeverity;
  primary_category: AnomalyCategory;
  sensor_confidence: number;
  factors: AnomalyFactor[];
  summary: string;
  evaluated_at: string;
}

export interface TrajectoryWayPoint {
  timestamp: string;
  time_offset_seconds: number;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  uncertainty_radius_meters: number;
}

export interface TrajectoryPrediction {
  track_id: string;
  prediction_horizon_seconds: number;
  model_type: string;
  waypoints: TrajectoryWayPoint[];
  generated_at: string;
}

export interface GeofenceIngressEstimate {
  track_id: string;
  geofence_id: string;
  geofence_name: string;
  estimated_time_to_breach_seconds?: number | null;
  intersection_latitude?: number | null;
  intersection_longitude?: number | null;
  status: 'INSIDE' | 'APPROACHING' | 'DIVERGING' | 'NO_INTERSECTION';
  evaluated_at: string;
}

export interface DefensiveIntelligenceSummary {
  track_id: string;
  features: KinematicFeatures;
  anomaly: AnomalyAssessment;
  trajectory: TrajectoryPrediction;
  ingress_estimates: GeofenceIngressEstimate[];
  evaluated_at: string;
}
