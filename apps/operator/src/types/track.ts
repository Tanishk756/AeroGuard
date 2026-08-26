export type TrackState = 'NEW' | 'ACTIVE' | 'STALE' | 'LOST' | 'ARCHIVED';

export interface Track {
  id: string;
  state: TrackState;
  first_seen_at: string;
  last_seen_at: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  confidence: number;
  classification: string;
  source_count: number;
  metadata?: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

export interface TrackHistoryPoint {
  id: string;
  track_id: string;
  sequence: number;
  timestamp: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  confidence: number;
  state: TrackState;
  provenance: string;
  source_detection_ids: string[];
}

export interface TrackListResponse {
  items: Track[];
  total: number;
  limit: number;
  offset: number;
}

export interface TrackDetailResponse extends Track {
  recent_history?: TrackHistoryPoint[];
}

export interface TrackHistoryListResponse {
  items: TrackHistoryPoint[];
  total: number;
}
