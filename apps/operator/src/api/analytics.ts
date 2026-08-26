import {
  AlertMetrics,
  AnalyticsSummaryResponse,
  DetectionMetrics,
  ThreatMetrics,
  TrackMetrics,
} from '../types';
import { request } from './client';

export async function getAnalyticsSummary(params?: {
  window_start?: string;
  window_end?: string;
}): Promise<AnalyticsSummaryResponse> {
  return request<AnalyticsSummaryResponse>('/analytics/summary', {
    params: params as Record<string, string | undefined>,
  });
}

export async function getDetectionMetrics(params?: {
  window_start?: string;
  window_end?: string;
}): Promise<DetectionMetrics> {
  return request<DetectionMetrics>('/analytics/detections', {
    params: params as Record<string, string | undefined>,
  });
}

export async function getTrackMetrics(params?: {
  window_start?: string;
  window_end?: string;
}): Promise<TrackMetrics> {
  return request<TrackMetrics>('/analytics/tracks', {
    params: params as Record<string, string | undefined>,
  });
}

export async function getAlertMetrics(params?: {
  window_start?: string;
  window_end?: string;
}): Promise<AlertMetrics> {
  return request<AlertMetrics>('/analytics/alerts', {
    params: params as Record<string, string | undefined>,
  });
}

export async function getThreatMetrics(params?: {
  window_start?: string;
  window_end?: string;
}): Promise<ThreatMetrics> {
  return request<ThreatMetrics>('/analytics/threats', {
    params: params as Record<string, string | undefined>,
  });
}
