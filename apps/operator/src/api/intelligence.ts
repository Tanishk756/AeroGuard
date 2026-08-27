import {
  DefensiveIntelligenceSummary,
  MultiTrackIntelligenceSummary,
} from '../types/intelligence';
import { request } from './client';

export async function getTrackIntelligence(
  trackId: string
): Promise<DefensiveIntelligenceSummary> {
  return request<DefensiveIntelligenceSummary>(`/tracks/${encodeURIComponent(trackId)}/intelligence`);
}

export async function getMultiTrackIntelligenceSummary(params?: {
  track_id?: string;
  group_id?: string;
  min_priority_level?: string;
  min_priority_score?: number;
}): Promise<MultiTrackIntelligenceSummary> {
  return request<MultiTrackIntelligenceSummary>('/intelligence/summary', { params });
}
