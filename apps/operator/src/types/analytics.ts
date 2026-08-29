export interface DetectionMetrics {
  total_detections: number;
  detections_by_sensor: Record<string, number>;
  detections_by_source_type: Record<string, number>;
  detections_by_classification: Record<string, number>;
}

export interface TrackMetrics {
  total_tracks: number;
  tracks_by_state: Record<string, number>;
  tracks_by_classification: Record<string, number>;
  average_confidence: number;
  average_duration_seconds: number;
}

export interface AlertMetrics {
  total_alerts: number;
  alerts_by_type: Record<string, number>;
  alerts_by_severity: Record<string, number>;
  alerts_by_status: Record<string, number>;
  average_resolution_seconds: number;
}

export interface ThreatMetrics {
  total_assessed?: number;
  total_assessments?: number;
  threats_by_level?: Record<string, number>;
  by_level?: Record<string, number>;
  average_score?: number;
  avg_score?: number;
  max_score: number;
}

export interface ThreatTimeSeriesPoint {
  timestamp: string;
  peak_threat_score: number;
  group_count: number;
  formation_count: number;
  active_track_count: number;
}

export interface CoordinationPeakPoint {
  timestamp: string;
  group_id: string;
  member_count: number;
  coordination_index: number;
  formation_type: string;
}

export interface IntelligenceAnalyticsReport {
  window_start?: string | null;
  window_end?: string | null;
  total_snapshots: number;
  total_group_events: number;
  total_behavior_transitions: number;
  behavior_distribution: Record<string, number>;
  group_state_distribution: Record<string, number>;
  avg_group_size: number;
  max_group_size: number;
  avg_coordination_index: number;
  peak_threat_score: number;
  threat_score_time_series: ThreatTimeSeriesPoint[];
  coordination_peaks: CoordinationPeakPoint[];
}

export interface AnalyticsSummaryResponse {
  window_start?: string | null;
  window_end?: string | null;
  generated_at?: string;
  detections: DetectionMetrics;
  tracks: TrackMetrics;
  alerts: AlertMetrics;
  threats: ThreatMetrics;
  intelligence?: IntelligenceAnalyticsReport | null;
  geofence_breach_count?: number;
}
