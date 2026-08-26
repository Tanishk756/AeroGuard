import { AlertSeverity, AlertStatus, AlertType } from './alert';
import { ThreatLevel } from './threat';
import { TrackState } from './track';

export interface HistoricalDetectionItem {
  id: string;
  sensor_id: string;
  source_detection_id: string;
  timestamp: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  confidence: number;
  source_class: string;
  source_type: string;
  classification?: string | null;
  track_id?: string | null;
}

export interface HistoricalDetectionsPage {
  items: HistoricalDetectionItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface HistoricalTrackStateResponse {
  track_id: string;
  as_of_time: string;
  state?: TrackState | null;
  sequence?: number | null;
  latitude?: number | null;
  longitude?: number | null;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  confidence?: number | null;
  provenance?: string | null;
  source_detection_ids?: string[] | null;
  observed_at?: string | null;
}

export interface HistoricalAlertItem {
  id: string;
  type: AlertType;
  severity: AlertSeverity;
  status: AlertStatus;
  track_id?: string | null;
  sensor_id?: string | null;
  reason: string;
  created_at: string;
  resolved_at?: string | null;
}

export interface HistoricalAlertsPage {
  items: HistoricalAlertItem[];
  total: number;
  limit: number;
  offset: number;
}

export interface HistoricalThreatItem {
  id: string;
  track_id: string;
  score: number;
  level: ThreatLevel;
  factors: Record<string, unknown>;
  created_at: string;
}

export interface HistoricalThreatsPage {
  items: HistoricalThreatItem[];
  total: number;
  limit: number;
  offset: number;
}

export type TimelineEventType =
  | 'DETECTION_OBSERVED'
  | 'TRACK_STATE_CHANGED'
  | 'THREAT_ASSESSED'
  | 'GEOFENCE_BREACHED'
  | 'ALERT_RAISED'
  | 'ALERT_RESOLVED';

export interface TimelineItem {
  timestamp: string;
  event_type: TimelineEventType;
  entity_id: string;
  track_id?: string | null;
  sensor_id?: string | null;
  summary: string;
  details: Record<string, unknown>;
}

export interface TimelinePage {
  items: TimelineItem[];
  total: number;
  limit: number;
  offset: number;
}
