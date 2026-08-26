import { TrackDetailResponse, TrackHistoryListResponse, TrackListResponse } from '../types';
import { request } from './client';

export interface GetTracksParams {
  state?: string;
  classification?: string;
  last_seen_from?: string;
  last_seen_to?: string;
  limit?: number;
  offset?: number;
}

export async function getTracks(params?: GetTracksParams): Promise<TrackListResponse> {
  return request<TrackListResponse>('/tracks', { params: params as Record<string, string | number | undefined> });
}

export async function getTrackDetail(trackId: string): Promise<TrackDetailResponse> {
  return request<TrackDetailResponse>(`/tracks/${encodeURIComponent(trackId)}`);
}

export async function getTrackHistory(trackId: string, limit = 50, offset = 0): Promise<TrackHistoryListResponse> {
  return request<TrackHistoryListResponse>(`/tracks/${encodeURIComponent(trackId)}/history`, {
    params: { limit, offset },
  });
}
