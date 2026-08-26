export type ScenarioStatus = 'DRAFT' | 'READY' | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'COMPLETED';

export interface ScenarioWaypoint {
  latitude: number;
  longitude: number;
  altitude?: number | null;
  speed?: number | null;
}

export interface ScenarioTargetDefinition {
  target_id: string;
  initial_latitude: number;
  initial_longitude: number;
  initial_altitude?: number | null;
  velocity: number;
  heading: number;
  waypoints: ScenarioWaypoint[];
  classification?: string | null;
}

export interface ScenarioSensorDefinition {
  sensor_id: string;
  modality: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  range_meters: number;
  detection_probability: number;
  position_uncertainty_meters: number;
  altitude_uncertainty_meters?: number | null;
  velocity_uncertainty_mps?: number | null;
  fov_azimuth_start_deg?: number | null;
  fov_azimuth_span_deg?: number | null;
}

export interface ScenarioConfiguration {
  seed: number;
  duration_seconds: number;
  tick_rate_hz: number;
  start_time: string;
  targets: ScenarioTargetDefinition[];
  sensors: ScenarioSensorDefinition[];
  geofence_ids: string[];
}

export interface Scenario {
  id: string;
  name: string;
  description: string;
  status: ScenarioStatus;
  source_class: string;
  created_by_user_id: string;
  configuration_metadata: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface ScenarioCreate {
  name: string;
  description?: string;
  configuration: ScenarioConfiguration;
}

export interface ScenarioUpdate {
  name?: string;
  description?: string;
  configuration?: ScenarioConfiguration;
  status?: ScenarioStatus;
}

export interface ScenarioExecutionStatus {
  scenario_id: string;
  status: ScenarioStatus;
  is_paused: boolean;
  virtual_time: string;
  tick_count: number;
  active_targets: number;
  generated_detections_count: number;
  processed_detections_count: number;
  seed: number;
  error?: string | null;
}

export interface ScenarioPage {
  items: Scenario[];
  next_cursor?: string | null;
}
