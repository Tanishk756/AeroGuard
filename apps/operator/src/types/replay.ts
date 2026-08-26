import { HistoricalAlertItem, HistoricalDetectionItem, HistoricalThreatItem } from './history';
import { TrackState } from './track';

export interface ReplayFilter {
  track_ids?: string[];
  sensor_ids?: string[];
  classifications?: string[];
}

export interface ReplayRequest {
  start_time: string;
  end_time: string;
  step_interval_seconds?: number;
  filters?: ReplayFilter;
}

export interface ReplayStepRequest {
  request: ReplayRequest;
  current_step?: number;
  steps_to_advance?: number;
}

export interface ReplayTrackState {
  track_id: string;
  state: TrackState;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  confidence: number;
  classification: string;
  source_count: number;
}

export interface ReplaySnapshot {
  replay_timestamp: string;
  step_index: number;
  is_complete: boolean;
  active_tracks: ReplayTrackState[];
  recent_detections: HistoricalDetectionItem[];
  active_alerts: HistoricalAlertItem[];
  active_threats: HistoricalThreatItem[];
}

export interface ReplayDifference {
  field: string;
  value_1: unknown;
  value_2: unknown;
  delta?: number | null;
}

export interface ReplayComparisonReport {
  identical: boolean;
  total_detections_match: boolean;
  total_tracks_match: boolean;
  total_alerts_match: boolean;
  total_threats_match: boolean;
  detections_count_1: number;
  detections_count_2: number;
  tracks_count_1: number;
  tracks_count_2: number;
  alerts_count_1: number;
  alerts_count_2: number;
  threats_count_1: number;
  threats_count_2: number;
  differences: ReplayDifference[];
}

export interface ReplayComparisonRequest {
  request_1: ReplayRequest;
  request_2: ReplayRequest;
}
