import { ThreatAssessment, ThreatAssessmentListResponse } from '../types';
import { request } from './client';

export interface GetThreatsParams {
  level?: string;
  min_score?: number;
  limit?: number;
  offset?: number;
}

export async function getThreats(params?: GetThreatsParams): Promise<ThreatAssessmentListResponse> {
  return request<ThreatAssessmentListResponse>('/threats', { params: params as Record<string, string | number | undefined> });
}

export async function getThreatDetail(trackId: string): Promise<ThreatAssessment> {
  return request<ThreatAssessment>(`/threats/${encodeURIComponent(trackId)}`);
}
