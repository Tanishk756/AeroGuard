export type AuditResult = 'SUCCESS' | 'FAILURE';

export interface AuditEvent {
  id: string;
  event_type: string;
  event_version: number;
  timestamp: string;
  action: string;
  result: AuditResult | string;
  correlation_id: string;
  actor_user_id?: string | null;
  actor_session_id?: string | null;
  target_type?: string | null;
  target_id?: string | null;
  reason?: string | null;
  permission?: string | null;
  source_ip?: string | null;
  user_agent?: string | null;
  metadata?: Record<string, unknown>;
  created_at: string;
}

export interface AuditEventPage {
  items: AuditEvent[];
  next_cursor?: string | null;
}

export interface AuditFilterParams {
  event_type?: string;
  result?: string;
  actor_id?: string;
  target_type?: string;
  target_id?: string;
  permission?: string;
  date_from?: string;
  date_to?: string;
  cursor?: string;
  limit?: number;
}
