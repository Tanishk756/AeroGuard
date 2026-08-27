/**
 * AeroGuard Defensive AI & Kinematic Intelligence Types
 * Includes AI1 Single-Track and AI2 Multi-Track Behavioral & Priority Contracts
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

// =====================================================================
// STAGE AI2 MULTI-TRACK INTELLIGENCE & BEHAVIORAL CONTRACTS
// =====================================================================

export type BehavioralState =
  | 'NORMAL'
  | 'APPROACHING'
  | 'DEPARTING'
  | 'LOITERING'
  | 'RAPID_CHANGE'
  | 'COORDINATED'
  | 'ANOMALOUS';

export interface BehaviorClassification {
  track_id: string;
  state: BehavioralState;
  confidence: number;
  duration_seconds: number;
  reason: string;
  contributing_factors: string[];
  evaluated_at: string;
}

export interface TrackGroup {
  group_id: string;
  member_track_ids: string[];
  centroid_lat: number;
  centroid_lon: number;
  centroid_alt?: number | null;
  radius_meters: number;
  member_count: number;
  confidence: number;
  behavioral_state: BehavioralState;
  updated_at: string;
}

export interface CoordinatedFormation {
  formation_id: string;
  group_id: string;
  member_track_ids: string[];
  synchronization_index: number;
  heading_dispersion_deg: number;
  velocity_dispersion_mps: number;
  confidence: number;
  evaluated_at: string;
}

export interface ThreatPriorityFactor {
  name: string;
  score: number;
  weight: number;
  contribution: number;
  description: string;
}

export interface ThreatPriorityAssessment {
  track_id: string;
  group_id?: string | null;
  priority_score: number;
  priority_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  factors: ThreatPriorityFactor[];
  reason: string;
  evaluated_at: string;
}

export interface MultiTrackIntelligenceSummary {
  groups: TrackGroup[];
  behaviors: BehaviorClassification[];
  formations: CoordinatedFormation[];
  priorities: ThreatPriorityAssessment[];
  evaluated_at: string;
}
