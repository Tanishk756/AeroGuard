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

export interface IncidentSummaryMetrics {
  total_incidents: number;
  active_incidents: number;
  acknowledged_incidents: number;
  assigned_incidents: number;
  triaged_incidents: number;
  escalated_incidents: number;
  resolved_incidents: number;
  closed_incidents: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export interface IncidentDistributionItem {
  count: number;
  percentage: number;
}

export interface IncidentTimeSeriesBucket {
  bucket_start: string;
  created_count: number;
  resolved_count: number;
  closed_count: number;
  escalated_count: number;
}

export interface IncidentLifecycleTimingMetrics {
  median_acknowledgement_seconds?: number | null;
  p95_acknowledgement_seconds?: number | null;
  median_assignment_seconds?: number | null;
  p95_assignment_seconds?: number | null;
  median_resolution_seconds?: number | null;
  p95_resolution_seconds?: number | null;
  median_closure_seconds?: number | null;
  p95_closure_seconds?: number | null;
  median_duration_seconds?: number | null;
  p95_duration_seconds?: number | null;
  sample_counts: Record<string, number>;
}

export interface IncidentProceduralActionMetrics {
  by_category: Record<string, number>;
  total_actions: number;
}

export interface IncidentCorrelationMetrics {
  with_primary_track: number;
  with_primary_group: number;
  uncorrelated: number;
  top_tracks: Array<{ track_id: string; incident_count: number }>;
  top_groups: Array<{ group_id: string; incident_count: number }>;
}

export interface IncidentWorkflowEventMetrics {
  by_event_type: Record<string, number>;
  total_events: number;
  total_notes: number;
  total_actions: number;
}

export interface IncidentAnalyticsResponse {
  window_start?: string | null;
  window_end?: string | null;
  bucket_size: string;
  summary: IncidentSummaryMetrics;
  timing: IncidentLifecycleTimingMetrics;
  severity_distribution: Record<IncidentSeverity, IncidentDistributionItem>;
  status_distribution: Record<IncidentStatus, IncidentDistributionItem>;
  time_series: IncidentTimeSeriesBucket[];
  procedural_actions: IncidentProceduralActionMetrics;
  correlations: IncidentCorrelationMetrics;
  workflow: IncidentWorkflowEventMetrics;
}

export interface IncidentAnalyticsFilterParams {
  start?: string;
  end?: string;
  severity?: IncidentSeverity;
  status?: IncidentStatus;
  assigned_to?: string;
  primary_track_id?: string;
  primary_group_id?: string;
  bucket_size?: 'hour' | 'day' | 'week';
}

// ---------------------------------------------------------------------------
// Incident Export Contracts (IM2-A / IM2-B)
// ---------------------------------------------------------------------------

export type IncidentExportFormat = 'JSON' | 'CSV' | 'PDF';

export type IncidentExportStatus = 'PENDING' | 'COMPLETED' | 'FAILED';

export interface CreateIncidentExportRequest {
  format?: IncidentExportFormat;
  start?: string | null;
  end?: string | null;
  severity?: IncidentSeverity | null;
  status?: IncidentStatus | null;
  assigned_to?: string | null;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
}

export interface IncidentExportMetadata {
  id: string;
  export_number: string;
  requested_by: string;
  format: IncidentExportFormat;
  status: IncidentExportStatus;
  record_count: number;
  file_size_bytes: number;
  sha256_checksum: string;
  created_at: string;
  completed_at?: string | null;
  filter_params_json?: Record<string, unknown>;
}

export interface IncidentExportResponse {
  metadata: IncidentExportMetadata;
  payload?: string | null;
}

export interface IncidentExportFilterParams {
  limit?: number;
  offset?: number;
}

// ---------------------------------------------------------------------------
// Incident Retention & Archival Governance Contracts (IM2-D)
// ---------------------------------------------------------------------------

export type IncidentArchivalState =
  | 'ACTIVE'
  | 'ARCHIVE_ELIGIBLE'
  | 'ARCHIVE_PENDING'
  | 'ARCHIVED'
  | 'ARCHIVE_FAILED'
  | 'PURGE_ELIGIBLE'
  | 'PURGE_APPROVED'
  | 'PURGED';

export interface RetentionPolicyResponse {
  id: string;
  policy_name: string;
  description?: string | null;
  enabled: boolean;
  incident_retention_days: number;
  export_retention_days: number;
  minimum_archive_age_days: number;
  minimum_purge_age_days: number;
  require_archive_before_purge: boolean;
  require_supervisor_approval: boolean;
  dry_run_by_default: boolean;
  created_by?: string | null;
  updated_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface RetentionPolicyUpdateRequest {
  incident_retention_days?: number;
  export_retention_days?: number;
  minimum_archive_age_days?: number;
  minimum_purge_age_days?: number;
  require_archive_before_purge?: boolean;
  require_supervisor_approval?: boolean;
  dry_run_by_default?: boolean;
}

export interface RetentionHoldCreateRequest {
  incident_id: string;
  reason: string;
}

export interface RetentionHoldResponse {
  id: string;
  incident_id: string;
  reason: string;
  active: boolean;
  placed_by: string;
  placed_at: string;
  released_by?: string | null;
  released_at?: string | null;
}

export interface RetentionEvaluationRecord {
  incident_id: string;
  incident_number: string;
  status: string;
  archival_state: string;
  age_days: number;
  is_terminal: boolean;
  has_active_hold: boolean;
  eligible_for_archive: boolean;
  eligible_for_purge: boolean;
  blocking_reasons: string[];
}

export interface RetentionEvaluationResponse {
  policy: RetentionPolicyResponse;
  evaluated_at: string;
  dry_run: boolean;
  total_evaluated: number;
  eligible_for_archive: number;
  already_archived: number;
  eligible_for_purge: number;
  blocked_by_hold: number;
  blocked_by_active_status: number;
  blocked_by_minimum_age: number;
  blocked_by_missing_archive: number;
  sample_records: RetentionEvaluationRecord[];
}

export interface ArchiveIncidentsRequest {
  incident_ids?: string[];
  batch_all_eligible?: boolean;
  archive_format?: 'JSON' | 'PDF';
}

export interface ArchiveRecordMetadata {
  id: string;
  archive_number: string;
  incident_id: string;
  sha256_checksum: string;
  file_size_bytes: number;
  archive_format: string;
  archived_at: string;
  archived_by: string;
  verified_at?: string | null;
}

export interface ArchiveIncidentsResponse {
  message: string;
  archived_count: number;
  archives: ArchiveRecordMetadata[];
}

export interface PurgeIncidentsRequest {
  incident_ids?: string[];
  batch_all_eligible?: boolean;
  confirm?: boolean;
}

export interface PurgePreviewRecord {
  incident_id: string;
  incident_number: string;
  will_be_purged: boolean;
  blocking_reasons: string[];
}

export interface PurgePreviewResponse {
  dry_run: boolean;
  policy_name: string;
  eligible_for_purge_count: number;
  blocked_count: number;
  records: PurgePreviewRecord[];
}

export interface PurgeIncidentsResponse {
  message: string;
  dry_run: boolean;
  purged_count: number;
  purged_incident_ids: string[];
  audit_event_id?: string | null;
}
