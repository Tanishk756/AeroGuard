export type SensorStatus = 'ACTIVE' | 'INACTIVE' | 'MAINTENANCE' | 'DEGRADED';
export type SensorSourceClass = 'REAL' | 'SIMULATION' | 'REPLAY';

export interface Sensor {
  id: string;
  name: string;
  source_type: string;
  source_class: SensorSourceClass;
  status: SensorStatus;
  configuration_version: number;
  configuration_metadata?: {
    latitude?: number;
    longitude?: number;
    altitude?: number;
    range_meters?: number;
    detection_probability?: number;
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
}

export interface SensorListResponse {
  items: Sensor[];
  total: number;
  limit: number;
  offset: number;
}
