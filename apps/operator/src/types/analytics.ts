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
  total_assessments: number;
  threats_by_level: Record<string, number>;
  average_score: number;
  max_score: number;
}

export interface AnalyticsSummaryResponse {
  window_start?: string | null;
  window_end?: string | null;
  generated_at: string;
  detections: DetectionMetrics;
  tracks: TrackMetrics;
  alerts: AlertMetrics;
  threats: ThreatMetrics;
}
