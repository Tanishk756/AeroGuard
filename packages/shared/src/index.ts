export type AppEnvironment = 'development' | 'staging' | 'production';

export type StatusLevel = 'NORMAL' | 'INFO' | 'WARNING' | 'HIGH' | 'CRITICAL' | 'OFFLINE' | 'DEGRADED';

export interface AppConfig {
  application_name: string;
  environment: AppEnvironment;
  timezone: string;
  session_duration: number;
  audit_retention: number;
  ui_theme: 'dark-tactical';
  realtime_configuration: {
    enabled: boolean;
    reconnect_delay_ms: number;
  };
}

export interface UserSummary {
  id: string;
  username: string;
  display_name: string;
  email: string;
  status: 'ACTIVE' | 'DISABLED';
  created_at: string;
  updated_at: string;
  last_login_at?: string | null;
}

export interface EventEnvelope<TPayload = Record<string, unknown>> {
  event_id: string;
  event_type: string;
  timestamp: string;
  correlation_id: string;
  source: string;
  payload: TPayload;
}
