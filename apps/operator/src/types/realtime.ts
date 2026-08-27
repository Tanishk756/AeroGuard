/**
 * Realtime WebSocket event contract types for AeroGuard defensive streaming.
 */

export type RealtimeChannel = 'operational' | 'simulation' | 'system';

export type RealtimeEventType =
  | 'track.created'
  | 'track.updated'
  | 'track.dropped'
  | 'alert.created'
  | 'alert.updated'
  | 'threat.updated'
  | 'geofence.breach'
  | 'simulation.state'
  | 'simulation.step'
  | 'simulation.clock'
  | 'simulation.reset'
  | 'system.heartbeat';

export interface RealtimeEventEnvelope<T = Record<string, unknown>> {
  event_id: string;
  event_type: RealtimeEventType | string;
  channel: RealtimeChannel | string;
  sequence: number;
  timestamp: string;
  resource_type?: string | null;
  resource_id?: string | null;
  correlation_id?: string | null;
  payload: T;
}

export type StreamStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'FAILED';

export type OperationalConnectionMode = 'STREAMING' | 'POLLING' | 'CONNECTING' | 'RECONNECTING' | 'DISCONNECTED';
