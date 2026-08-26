import { SystemHealthResponse, SystemInfoResponse } from '../types';
import { request } from './client';

export async function getHealth(): Promise<SystemHealthResponse> {
  return request<SystemHealthResponse>('/health');
}

export async function getSystemInfo(): Promise<SystemInfoResponse> {
  return request<SystemInfoResponse>('/system/info');
}
