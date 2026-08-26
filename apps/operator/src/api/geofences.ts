import { Geofence, GeofenceCreate, GeofencePage, GeofenceUpdate } from '../types';
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

export async function createGeofence(data: GeofenceCreate): Promise<Geofence> {
  return request<Geofence>('/geofences', {
    method: 'POST',
    body: JSON.stringify(data),
  });
}

export async function updateGeofence(geofenceId: string, data: GeofenceUpdate): Promise<Geofence> {
  return request<Geofence>(`/geofences/${encodeURIComponent(geofenceId)}`, {
    method: 'PUT',
    body: JSON.stringify(data),
  });
}

export async function deleteGeofence(geofenceId: string): Promise<void> {
  return request<void>(`/geofences/${encodeURIComponent(geofenceId)}`, {
    method: 'DELETE',
  });
}
