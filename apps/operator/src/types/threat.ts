export type ThreatLevel = 'NONE' | 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface ThreatAssessment {
  id: string;
  track_id: string;
  score: number;
  level: ThreatLevel;
  factors?: {
    speed_mps?: number;
    altitude_m?: number;
    heading_deg?: number;
    geofence_breached?: boolean;
    source_diversity?: number;
    classification?: string;
    [key: string]: unknown;
  };
  created_at: string;
  updated_at: string;
}

export interface ThreatAssessmentListResponse {
  items: ThreatAssessment[];
  total: number;
  limit: number;
  offset: number;
}
