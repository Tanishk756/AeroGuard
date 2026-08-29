/**
 * AeroGuard Incident Management Types & Realtime Contracts
 * Stage IM1-E: Operator Incident Workspace
 */

export type IncidentStatus =
  | 'NEW'
  | 'ACKNOWLEDGED'
  | 'TRIAGED'
  | 'ESCALATED'
  | 'RESOLVED'
  | 'CLOSED';

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type IncidentSource =
  | 'OPERATOR'
  | 'ALERT'
  | 'AI_ANOMALY'
  | 'AI_SWARM'
  | 'SYSTEM'
  | 'EXTERNAL';

export type IncidentEventType =
  | 'CREATED'
  | 'STATUS_CHANGED'
  | 'ASSIGNED'
  | 'TRIAGED'
  | 'ESCALATED'
  | 'DE_ESCALATED'
  | 'NOTE_ADDED'
  | 'ACTION_LOGGED'
  | 'RESOLVED'
  | 'CLOSED';

export type DefensiveActionCategory =
  | 'SENSOR_REVIEW'
  | 'TRACK_CORRELATION_REVIEW'
  | 'OPERATOR_CONTACT'
  | 'SUPERVISOR_ESCALATION'
  | 'PROCEDURE_REVIEW'
  | 'SCENARIO_REVIEW'
  | 'OTHER';

export interface Incident {
  id: string;
  incident_number: string;
  title: string;
  description?: string | null;
  status: IncidentStatus;
  severity: IncidentSeverity;
  source: IncidentSource;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
  originating_alert_id?: string | null;
  originating_intelligence_event_id?: string | null;
  created_by?: string | null;
  acknowledged_by?: string | null;
  assigned_to?: string | null;
  resolved_by?: string | null;
  closed_by?: string | null;
  created_at: string;
  updated_at: string;
  acknowledged_at?: string | null;
  assigned_at?: string | null;
  resolved_at?: string | null;
  closed_at?: string | null;
  metadata?: Record<string, unknown>;
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  sequence: number;
  timestamp: string;
  event_type: IncidentEventType;
  actor_user_id?: string | null;
  previous_status?: IncidentStatus | null;
  new_status?: IncidentStatus | null;
  message?: string | null;
  category?: DefensiveActionCategory | null;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface IncidentListResponse {
  items: Incident[];
  total: number;
  limit: number;
  offset: number;
}

export interface IncidentRealtimePayload {
  incident_id: string;
  incident_number: string;
  title: string;
  status: string;
  previous_status?: string | null;
  severity: string;
  previous_severity?: string | null;
  source: string;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
  originating_alert_id?: string | null;
  originating_intelligence_event_id?: string | null;
  assigned_to?: string | null;
  previous_assignee?: string | null;
  actor_user_id?: string | null;
  incident_event_id: string;
  incident_event_sequence: number;
  incident_event_type: string;
  category?: string | null;
  message?: string | null;
  timestamp: string;
}

export interface CreateIncidentRequest {
  title: string;
  description?: string | null;
  severity?: IncidentSeverity;
  source?: IncidentSource;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
  originating_alert_id?: string | null;
  originating_intelligence_event_id?: string | null;
  metadata?: Record<string, unknown>;
}

export interface AcknowledgeIncidentRequest {
  message?: string;
}

export interface AssignIncidentRequest {
  assigned_to: string;
  reason?: string;
}

export interface TriageIncidentRequest {
  severity?: IncidentSeverity;
  notes?: string;
}

export interface EscalateIncidentRequest {
  reason: string;
}

export interface DeEscalateIncidentRequest {
  target_status?: IncidentStatus;
  reason: string;
}

export interface ResolveIncidentRequest {
  resolution_summary: string;
}

export interface CloseIncidentRequest {
  closure_notes?: string;
}

export interface AddIncidentNoteRequest {
  message: string;
  metadata?: Record<string, unknown>;
}

export interface LogDefensiveActionRequest {
  category: DefensiveActionCategory;
  message?: string;
  metadata?: Record<string, unknown>;
}

export interface IncidentFilterParams {
  status?: string;
  severity?: string;
  source?: string;
  assigned_to?: string;
  primary_track_id?: string;
  primary_group_id?: string;
  originating_alert_id?: string;
  search?: string;
  limit?: number;
  offset?: number;
}
