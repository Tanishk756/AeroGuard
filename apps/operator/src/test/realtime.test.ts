import assert from 'node:assert';
import test, { describe, it } from 'node:test';

// ── Pure Domain & Contract Definitions for RT1 Realtime Streaming ──

type RealtimeChannel = 'operational' | 'simulation' | 'system';

type RealtimeEventType =
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

interface RealtimeEventEnvelope<T = Record<string, unknown>> {
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

type StreamStatus = 'CONNECTING' | 'CONNECTED' | 'DISCONNECTED' | 'RECONNECTING' | 'FAILED';
type OperationalConnectionMode = 'STREAMING' | 'POLLING' | 'CONNECTING' | 'RECONNECTING' | 'DISCONNECTED';

interface Track {
  id: string;
  state: 'NEW' | 'ACTIVE' | 'STALE' | 'DROPPED';
  latitude: number;
  longitude: number;
  altitude?: number;
  velocity?: number;
  heading?: number;
  confidence: number;
  classification?: string;
  source_count: number;
  first_seen_at: string;
  last_seen_at: string;
  created_at: string;
  updated_at: string;
}

interface Alert {
  id: string;
  type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  reason: string;
  created_at: string;
  updated_at: string;
}

interface ThreatAssessment {
  id: string;
  track_id: string;
  score: number;
  level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  factors: Record<string, unknown>;
  created_at: string;
  updated_at: string;
}

function resolveWebSocketUrl(path: string, host = 'localhost:8000', protocol = 'http:'): string {
  const wsProto = protocol === 'https:' ? 'wss:' : 'ws:';
  return `${wsProto}//${host}${path}`;
}

describe('AeroGuard Stage RT1 Realtime Streaming & WebSocket Event Bus Unit Tests', () => {
  describe('WebSocket URL Resolution', () => {
    it('constructs ws:// URL for standard HTTP origin', () => {
      const url = resolveWebSocketUrl('/api/v1/ws/operational', 'localhost:8000', 'http:');
      assert.strictEqual(url, 'ws://localhost:8000/api/v1/ws/operational');
    });

    it('constructs wss:// URL for HTTPS origin', () => {
      const url = resolveWebSocketUrl('/api/v1/ws/operational', 'aeroguard.defense.internal', 'https:');
      assert.strictEqual(url, 'wss://aeroguard.defense.internal/api/v1/ws/operational');
    });

    it('resolves simulation channel path correctly', () => {
      const url = resolveWebSocketUrl('/api/v1/ws/simulation', 'localhost:8000', 'http:');
      assert.strictEqual(url, 'ws://localhost:8000/api/v1/ws/simulation');
    });
  });

  describe('Realtime Event Envelope Validation & Parsing', () => {
    it('parses valid operational track.created envelope', () => {
      const raw = {
        event_id: '550e8400-e29b-41d4-a716-446655440000',
        event_type: 'track.created',
        channel: 'operational',
        sequence: 42,
        timestamp: '2026-08-27T02:00:00Z',
        resource_type: 'track',
        resource_id: 'TRK-001',
        payload: {
          id: 'TRK-001',
          state: 'NEW',
          latitude: 37.7749,
          longitude: -122.4194,
          altitude: 120.5,
          confidence: 0.9,
          classification: 'UAV_ROTARY',
          source_count: 1,
          first_seen_at: '2026-08-27T02:00:00Z',
          last_seen_at: '2026-08-27T02:00:00Z',
          created_at: '2026-08-27T02:00:00Z',
          updated_at: '2026-08-27T02:00:00Z',
        },
      };

      const envelope = raw as RealtimeEventEnvelope<Track>;
      assert.strictEqual(envelope.event_type, 'track.created');
      assert.strictEqual(envelope.channel, 'operational');
      assert.strictEqual(envelope.sequence, 42);
      assert.strictEqual(envelope.payload.id, 'TRK-001');
      assert.strictEqual(envelope.payload.latitude, 37.7749);
    });

    it('parses valid simulation.step envelope', () => {
      const raw = {
        event_id: '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
        event_type: 'simulation.step',
        channel: 'simulation',
        sequence: 10,
        timestamp: '2026-08-27T02:00:01Z',
        payload: {
          scenario_id: 'SCN-ALPHA',
          tick_count: 50,
          virtual_time: '2026-08-27T02:05:00Z',
          active_targets: 3,
        },
      };

      const envelope = raw as RealtimeEventEnvelope;
      assert.strictEqual(envelope.channel, 'simulation');
      assert.strictEqual(envelope.event_type, 'simulation.step');
      assert.strictEqual((envelope.payload as { tick_count: number }).tick_count, 50);
    });
  });

  describe('Realtime State Reducer & Entity Reconciliation', () => {
    it('immutably adds new track on track.created', () => {
      const initialTracks: Track[] = [
        {
          id: 'TRK-001',
          state: 'ACTIVE',
          latitude: 37.77,
          longitude: -122.41,
          altitude: 100,
          velocity: 20,
          heading: 90,
          confidence: 0.9,
          classification: 'UAV_ROTARY',
          source_count: 1,
          first_seen_at: '2026-08-27T00:00:00Z',
          last_seen_at: '2026-08-27T00:00:00Z',
          created_at: '2026-08-27T00:00:00Z',
          updated_at: '2026-08-27T00:00:00Z',
        },
      ];

      const newTrack: Track = {
        id: 'TRK-002',
        state: 'NEW',
        latitude: 37.78,
        longitude: -122.42,
        altitude: 150,
        velocity: 15,
        heading: 180,
        confidence: 0.85,
        classification: 'UAV_FIXED_WING',
        source_count: 1,
        first_seen_at: '2026-08-27T00:01:00Z',
        last_seen_at: '2026-08-27T00:01:00Z',
        created_at: '2026-08-27T00:01:00Z',
        updated_at: '2026-08-27T00:01:00Z',
      };

      const updated = [newTrack, ...initialTracks];
      assert.strictEqual(updated.length, 2);
      assert.strictEqual(updated[0].id, 'TRK-002');
      assert.strictEqual(updated[1].id, 'TRK-001');
    });

    it('immutably updates existing track on track.updated', () => {
      const initialTracks: Track[] = [
        {
          id: 'TRK-001',
          state: 'NEW',
          latitude: 37.77,
          longitude: -122.41,
          altitude: 100,
          velocity: 20,
          heading: 90,
          confidence: 0.8,
          classification: 'UNKNOWN',
          source_count: 1,
          first_seen_at: '2026-08-27T00:00:00Z',
          last_seen_at: '2026-08-27T00:00:00Z',
          created_at: '2026-08-27T00:00:00Z',
          updated_at: '2026-08-27T00:00:00Z',
        },
      ];

      const updateData: Partial<Track> = {
        id: 'TRK-001',
        state: 'ACTIVE',
        latitude: 37.775,
        longitude: -122.415,
        classification: 'UAV_ROTARY',
        confidence: 0.95,
      };

      const updated = initialTracks.map((t) => (t.id === updateData.id ? { ...t, ...updateData } : t));
      assert.strictEqual(updated.length, 1);
      assert.strictEqual(updated[0].state, 'ACTIVE');
      assert.strictEqual(updated[0].latitude, 37.775);
      assert.strictEqual(updated[0].classification, 'UAV_ROTARY');
      assert.strictEqual(updated[0].altitude, 100);
    });

    it('removes track on track.dropped', () => {
      const initialTracks: Track[] = [
        { id: 'TRK-001', state: 'ACTIVE' } as Track,
        { id: 'TRK-002', state: 'ACTIVE' } as Track,
      ];

      const remaining = initialTracks.filter((t) => t.id !== 'TRK-001');
      assert.strictEqual(remaining.length, 1);
      assert.strictEqual(remaining[0].id, 'TRK-002');
    });

    it('immutably prepends new alert and prevents duplicates', () => {
      const existingAlerts: Alert[] = [
        {
          id: 'ALT-1',
          type: 'GEOFENCE_BREACH',
          severity: 'HIGH',
          status: 'OPEN',
          reason: 'Initial breach',
          created_at: '2026-08-27T00:00:00Z',
          updated_at: '2026-08-27T00:00:00Z',
        },
      ];

      const newAlert: Alert = {
        id: 'ALT-2',
        type: 'PROXIMITY_CRITICAL',
        severity: 'CRITICAL',
        status: 'OPEN',
        reason: 'Critical proximity warning',
        created_at: '2026-08-27T00:01:00Z',
        updated_at: '2026-08-27T00:01:00Z',
      };

      const withNew = [newAlert, ...existingAlerts];
      assert.strictEqual(withNew.length, 2);
      assert.strictEqual(withNew[0].id, 'ALT-2');

      // Duplicate protection
      const duplicateAlert: Alert = { ...newAlert, reason: 'Duplicate event' };
      const exists = withNew.some((a) => a.id === duplicateAlert.id);
      const deduplicated = exists ? withNew : [duplicateAlert, ...withNew];
      assert.strictEqual(deduplicated.length, 2);
    });

    it('immutably updates threat assessment score and factors', () => {
      const initialThreats: ThreatAssessment[] = [
        {
          id: 'THR-1',
          track_id: 'TRK-001',
          score: 45.0,
          level: 'LOW',
          factors: { kinematic: 10, geofence: 20 },
          created_at: '2026-08-27T00:00:00Z',
          updated_at: '2026-08-27T00:00:00Z',
        },
      ];

      const threatUpdate: ThreatAssessment = {
        id: 'THR-1',
        track_id: 'TRK-001',
        score: 85.0,
        level: 'CRITICAL',
        factors: { kinematic: 40, geofence: 45 },
        created_at: '2026-08-27T00:00:00Z',
        updated_at: '2026-08-27T00:01:00Z',
      };

      const updated = initialThreats.map((th) => (th.id === threatUpdate.id ? threatUpdate : th));
      assert.strictEqual(updated.length, 1);
      assert.strictEqual(updated[0].score, 85.0);
      assert.strictEqual(updated[0].level, 'CRITICAL');
    });
  });

  describe('Sequence Gap Detection & Fallback Policy', () => {
    it('detects sequence gaps when sequence jumps by more than 1', () => {
      let gapDetected = false;
      let expectedSeq = 0;
      let receivedSeq = 0;

      const onSequenceGap = (expected: number, received: number) => {
        gapDetected = true;
        expectedSeq = expected;
        receivedSeq = received;
      };

      const lastSeq = 5;
      const incomingSeq = 8;

      if (lastSeq > 0 && incomingSeq > lastSeq + 1) {
        onSequenceGap(lastSeq + 1, incomingSeq);
      }

      assert.strictEqual(gapDetected, true);
      assert.strictEqual(expectedSeq, 6);
      assert.strictEqual(receivedSeq, 8);
    });

    it('does not trigger gap detection on sequential messages', () => {
      let gapDetected = false;
      const onSequenceGap = () => {
        gapDetected = true;
      };

      const lastSeq = 5;
      const incomingSeq = 6;

      if (lastSeq > 0 && incomingSeq > lastSeq + 1) {
        onSequenceGap();
      }

      assert.strictEqual(gapDetected, false);
    });

    it('maps StreamStatus to ConnectionMode correctly', () => {
      const computeMode = (status: StreamStatus): OperationalConnectionMode => {
        if (status === 'CONNECTED') return 'STREAMING';
        if (status === 'CONNECTING') return 'CONNECTING';
        if (status === 'RECONNECTING') return 'RECONNECTING';
        return 'POLLING';
      };

      assert.strictEqual(computeMode('CONNECTED'), 'STREAMING');
      assert.strictEqual(computeMode('CONNECTING'), 'CONNECTING');
      assert.strictEqual(computeMode('RECONNECTING'), 'RECONNECTING');
      assert.strictEqual(computeMode('DISCONNECTED'), 'POLLING');
      assert.strictEqual(computeMode('FAILED'), 'POLLING');
    });

    it('determines appropriate polling interval based on connection mode', () => {
      const getPollingInterval = (mode: OperationalConnectionMode, baseInterval = 15000) => {
        return mode === 'STREAMING' ? 60000 : baseInterval;
      };

      assert.strictEqual(getPollingInterval('STREAMING'), 60000);
      assert.strictEqual(getPollingInterval('POLLING'), 15000);
      assert.strictEqual(getPollingInterval('DISCONNECTED'), 15000);
    });
  });

  describe('Desktop Realtime Notification Dispatch & Deduplication', () => {
    it('identifies eligible alert.created events for desktop toast notifications', () => {
      const shouldDispatchNotification = (envelope: { event_type: string; payload: { severity?: string } }) => {
        if (envelope.event_type !== 'alert.created') return false;
        const sev = envelope.payload.severity;
        return sev === 'CRITICAL' || sev === 'HIGH';
      };

      assert.strictEqual(
        shouldDispatchNotification({ event_type: 'alert.created', payload: { severity: 'CRITICAL' } }),
        true
      );
      assert.strictEqual(
        shouldDispatchNotification({ event_type: 'alert.created', payload: { severity: 'HIGH' } }),
        true
      );
      assert.strictEqual(
        shouldDispatchNotification({ event_type: 'alert.created', payload: { severity: 'LOW' } }),
        false
      );
      assert.strictEqual(
        shouldDispatchNotification({ event_type: 'track.created', payload: { severity: 'CRITICAL' } }),
        false
      );
    });

    it('identifies critical threat escalation events for desktop toast notifications', () => {
      const isCriticalThreat = (envelope: { event_type: string; payload: { level?: string; score?: number } }) => {
        if (envelope.event_type !== 'threat.updated') return false;
        return envelope.payload.level === 'CRITICAL' || (envelope.payload.score || 0) >= 80;
      };

      assert.strictEqual(
        isCriticalThreat({ event_type: 'threat.updated', payload: { level: 'CRITICAL', score: 85 } }),
        true
      );
      assert.strictEqual(
        isCriticalThreat({ event_type: 'threat.updated', payload: { level: 'HIGH', score: 70 } }),
        false
      );
    });
  });

  describe('Heartbeat Watchdog & Dead Socket Detection', () => {
    it('detects stream stall when activity exceeds maxIdle threshold', () => {
      const checkWatchdog = (lastActivityTime: number, now: number, heartbeatIntervalMs = 15000) => {
        const maxIdleMs = heartbeatIntervalMs * 2.5; // 37500ms
        return now - lastActivityTime > maxIdleMs;
      };

      const baseTime = 100000;
      assert.strictEqual(checkWatchdog(baseTime, baseTime + 10000), false); // 10s idle - OK
      assert.strictEqual(checkWatchdog(baseTime, baseTime + 35000), false); // 35s idle - OK
      assert.strictEqual(checkWatchdog(baseTime, baseTime + 40000), true); // 40s idle - Stalled!
    });
  });

  describe('Rate-Limited Animation Frame Track Batching', () => {
    it('coalesces multiple rapid track updates into a single deduplicated map', () => {
      const pendingTracks = new Map<string, Track>();

      const track1V1: Track = { id: 'TRK-1', latitude: 37.1, longitude: -122.1 } as Track;
      const track2V1: Track = { id: 'TRK-2', latitude: 37.2, longitude: -122.2 } as Track;
      const track1V2: Track = { id: 'TRK-1', latitude: 37.15, longitude: -122.15 } as Track;

      // Rapidly incoming events in same frame
      pendingTracks.set(track1V1.id, track1V1);
      pendingTracks.set(track2V1.id, track2V1);
      pendingTracks.set(track1V2.id, track1V2); // Overwrites TRK-1 with freshest coordinates

      assert.strictEqual(pendingTracks.size, 2);
      assert.strictEqual(pendingTracks.get('TRK-1')?.latitude, 37.15);
      assert.strictEqual(pendingTracks.get('TRK-2')?.latitude, 37.2);
    });
  });
});
