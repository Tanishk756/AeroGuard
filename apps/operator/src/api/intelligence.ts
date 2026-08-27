/**
 * AeroGuard Defensive Intelligence API Client
 */

import { DefensiveIntelligenceSummary } from '../types/intelligence';
import { request } from './client';

export async function getTrackIntelligence(
  trackId: string
): Promise<DefensiveIntelligenceSummary> {
  return request<DefensiveIntelligenceSummary>(`/tracks/${encodeURIComponent(trackId)}/intelligence`);
}
