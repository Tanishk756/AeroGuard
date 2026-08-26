export type AlertType =
  | 'TRACK_DETECTED'
  | 'TRACK_LOST'
  | 'UNKNOWN_TRACK'
  | 'GEOFENCE_BREACH'
  | 'SENSOR_OFFLINE'
  | 'SENSOR_DEGRADED'
  | 'DATA_QUALITY_LOW';

export type AlertSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
export type AlertStatus = 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';

export interface Alert {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  track_id?: string | null;
  sensor_id?: string | null;
  reason: string;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
  acknowledged_at?: string | null;
  resolved_at?: string | null;
}

export interface AlertListResponse {
  items: Alert[];
  total: number;
  limit: number;
  offset: number;
}
