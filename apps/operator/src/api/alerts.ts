import { Alert, AlertListResponse } from '../types';
import { request } from './client';

export interface GetAlertsParams {
  status?: string;
  severity?: string;
  type?: string;
  track_id?: string;
  sensor_id?: string;
  created_from?: string;
  created_to?: string;
  limit?: number;
  offset?: number;
}

export async function getAlerts(params?: GetAlertsParams): Promise<AlertListResponse> {
  return request<AlertListResponse>('/alerts', { params: params as Record<string, string | number | undefined> });
}

export async function getAlertDetail(alertId: string): Promise<Alert> {
  return request<Alert>(`/alerts/${encodeURIComponent(alertId)}`);
}
