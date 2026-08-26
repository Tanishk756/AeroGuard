import { Sensor, SensorListResponse } from '../types';
import { request } from './client';

export interface GetSensorsParams {
  status?: string;
  source_type?: string;
  source_class?: string;
  limit?: number;
  offset?: number;
}

export async function getSensors(params?: GetSensorsParams): Promise<SensorListResponse> {
  return request<SensorListResponse>('/sensors', { params: params as Record<string, string | number | undefined> });
}

export async function getSensorDetail(sensorId: string): Promise<Sensor> {
  return request<Sensor>(`/sensors/${encodeURIComponent(sensorId)}`);
}
