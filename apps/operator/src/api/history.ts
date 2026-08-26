import {
  HistoricalAlertsPage,
  HistoricalDetectionsPage,
  HistoricalThreatsPage,
  HistoricalTrackStateResponse,
  TimelinePage,
  TrackHistoryListResponse,
} from '../types';
import { request } from './client';

export async function getHistoricalDetections(params?: {
  start_time?: string;
  end_time?: string;
  sensor_id?: string;
  source_type?: string;
  classification?: string;
  track_id?: string;
  limit?: number;
  offset?: number;
}): Promise<HistoricalDetectionsPage> {
  return request<HistoricalDetectionsPage>('/history/detections', {
    params: params as Record<string, string | number | undefined>,
  });
}

export async function getHistoricalTrackPoints(
  trackId: string,
  params?: { start_time?: string; end_time?: string; limit?: number; offset?: number }
): Promise<TrackHistoryListResponse> {
  return request<TrackHistoryListResponse>(`/history/tracks/${encodeURIComponent(trackId)}`, {
    params: params as Record<string, string | number | undefined>,
  });
}

export async function getHistoricalTrackStateAt(trackId: string, asOfTime: string): Promise<HistoricalTrackStateResponse> {
  return request<HistoricalTrackStateResponse>(`/history/tracks/${encodeURIComponent(trackId)}/state`, {
    params: { as_of_time: asOfTime },
  });
}

export async function getHistoricalAlerts(params?: {
  start_time?: string;
  end_time?: string;
  severity?: string;
  status?: string;
  alert_type?: string;
  track_id?: string;
  sensor_id?: string;
  limit?: number;
  offset?: number;
}): Promise<HistoricalAlertsPage> {
  return request<HistoricalAlertsPage>('/history/alerts', {
    params: params as Record<string, string | number | undefined>,
  });
}

export async function getHistoricalThreats(params?: {
  start_time?: string;
  end_time?: string;
  level?: string;
  track_id?: string;
  min_score?: number;
  limit?: number;
  offset?: number;
}): Promise<HistoricalThreatsPage> {
  return request<HistoricalThreatsPage>('/history/threats', {
    params: params as Record<string, string | number | undefined>,
  });
}

export async function getTimeline(params?: {
  start_time?: string;
  end_time?: string;
  track_id?: string;
  event_types?: string;
  limit?: number;
  offset?: number;
}): Promise<TimelinePage> {
  return request<TimelinePage>('/history/timeline', {
    params: params as Record<string, string | number | undefined>,
  });
}
