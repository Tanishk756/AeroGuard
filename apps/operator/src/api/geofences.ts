import { Geofence, GeofencePage } from '../types';
import { request } from './client';

export interface GetGeofencesParams {
  enabled?: boolean;
  cursor?: string;
  limit?: number;
}

export async function getGeofences(params?: GetGeofencesParams): Promise<GeofencePage> {
  return request<GeofencePage>('/geofences', {
    params: params as Record<string, string | number | boolean | undefined>,
  });
}

export async function getGeofenceDetail(geofenceId: string): Promise<Geofence> {
  return request<Geofence>(`/geofences/${encodeURIComponent(geofenceId)}`);
}
