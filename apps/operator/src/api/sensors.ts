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
  const result = await request<Sensor[] | SensorListResponse>('/sensors', {
    params: params as Record<string, string | number | undefined>,
  });

  // Handle both direct list of sensors (FastAPI response_model=list[SensorResponse]) and paginated response
  if (Array.isArray(result)) {
    return {
      items: result,
      total: result.length,
      limit: result.length,
      offset: 0,
    };
  }

  return result;
}

export async function getSensorDetail(sensorId: string): Promise<Sensor> {
  return request<Sensor>(`/sensors/${encodeURIComponent(sensorId)}`);
}
