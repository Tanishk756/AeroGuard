export type FormationType = 'LINE' | 'COLUMN' | 'V_FORMATION' | 'GRID' | 'CIRCLE';

export type SwarmRole = 'LEADER' | 'FOLLOWER';

export type SwarmHealth = 'HEALTHY' | 'DEGRADED' | 'CRITICAL' | 'DISCONNECTED';

export type SafetyEventType =
  | 'FORMATION_DEVIATION'
  | 'MINIMUM_SEPARATION_BREACH'
  | 'VEHICLE_DISCONNECTED'
  | 'LEADER_LOST'
  | 'SLOT_CONFLICT';

export interface SwarmMember {
  id: string;
  swarm_id: string;
  vehicle_id: string;
  role: SwarmRole;
  slot_index: number;
  offset_x: number;
  offset_y: number;
  offset_z: number;
}

export interface Swarm {
  id: string;
  name: string;
  description?: string;
  leader_vehicle_id?: string;
  formation_type: FormationType;
  formation_spacing_m: number;
  min_separation_m: number;
  status: string;
  members: SwarmMember[];
  created_at: string;
  updated_at: string;
}

export interface SafetyEvent {
  event_type: SafetyEventType;
  severity: 'INFO' | 'WARNING' | 'CRITICAL';
  vehicle_id: string;
  target_vehicle_id?: string;
  distance_m?: number;
  threshold_m?: number;
  timestamp: string;
  message: string;
}

export interface SwarmVehicleState {
  vehicle_id: string;
  autopilot_type: string;
  role: SwarmRole;
  slot_index: number;
  current_position_enu: [number, number, number];
  current_velocity_enu: [number, number, number];
  current_heading_deg: number;
  desired_position_enu: [number, number, number];
  desired_velocity_enu: [number, number, number];
  position_error_m: number;
  health_status: string;
  last_telemetry_timestamp: number;
}

export interface SwarmState {
  swarm_id: string;
  leader_vehicle_id?: string;
  formation_type: FormationType;
  health: SwarmHealth;
  vehicle_states: Record<string, SwarmVehicleState>;
  safety_events: SafetyEvent[];
  timestamp: string;
}
