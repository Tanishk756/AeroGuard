export type GeofenceGeometry =
  | {
      type: 'bbox';
      min_lat: number;
      min_lon: number;
      max_lat: number;
      max_lon: number;
    }
  | {
      type: 'polygon';
      coordinates: [number, number][];
    };

export interface Geofence {
  id: string;
  name: string;
  enabled: boolean;
  geometry: GeofenceGeometry;
  min_altitude?: number | null;
  max_altitude?: number | null;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface GeofencePage {
  items: Geofence[];
  next_cursor?: string | null;
}
