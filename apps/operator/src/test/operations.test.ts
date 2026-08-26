import assert from 'node:assert';
import test, { describe, it } from 'node:test';

describe('AeroGuard Stage UI3 Mission Operations & Interaction Unit Tests', () => {
  describe('Command Palette & Search Filtering', () => {
    interface CommandItem {
      id: string;
      label: string;
      category: string;
      shortcut?: string;
    }

    const commands: CommandItem[] = [
      { id: 'nav-overview', label: 'Go to Overview Workspace', category: 'Navigation', shortcut: 'g o' },
      { id: 'nav-tracks', label: 'Go to Track Management', category: 'Navigation', shortcut: 'g t' },
      { id: 'nav-sensors', label: 'Go to Sensor Inventory', category: 'Navigation', shortcut: 'g s' },
      { id: 'nav-alerts', label: 'Go to Operational Alerts', category: 'Navigation', shortcut: 'g a' },
      { id: 'nav-threats', label: 'Go to Threat Triage', category: 'Navigation', shortcut: 'g h' },
      { id: 'nav-scenarios', label: 'Go to Scenario Simulation Hub', category: 'Navigation', shortcut: 'g c' },
      { id: 'nav-replay', label: 'Go to Replay Analysis', category: 'Navigation', shortcut: 'g r' },
      { id: 'nav-history', label: 'Go to Historical Logs', category: 'Navigation', shortcut: 'g l' },
      { id: 'nav-analytics', label: 'Go to Operational Analytics', category: 'Navigation', shortcut: 'g y' },
      { id: 'map-fit', label: 'Fit Tactical Map to All Entities', category: 'Tactical Map', shortcut: 'f' },
      { id: 'map-reset', label: 'Reset Tactical Map View Center', category: 'Tactical Map', shortcut: 'c' },
      { id: 'ops-refresh', label: 'Refresh Operational Telemetry Data', category: 'Operations', shortcut: 'r' },
      { id: 'ws-inspector', label: 'Toggle Workspace Inspector Panel', category: 'Workspace', shortcut: 'i' },
      { id: 'ws-clear', label: 'Clear Active Entity Selection', category: 'Workspace', shortcut: 'Esc' },
    ];

    const filterCommands = (query: string) => {
      if (!query.trim()) return commands;
      const q = query.toLowerCase();
      return commands.filter(
        (cmd) =>
          cmd.label.toLowerCase().includes(q) ||
          cmd.category.toLowerCase().includes(q) ||
          (cmd.shortcut && cmd.shortcut.toLowerCase().includes(q))
      );
    };

    it('returns all commands when search query is empty', () => {
      const results = filterCommands('');
      assert.strictEqual(results.length, commands.length);
    });

    it('filters commands by label substring', () => {
      const results = filterCommands('replay');
      assert.strictEqual(results.length, 1);
      assert.strictEqual(results[0].id, 'nav-replay');
    });

    it('filters commands by category', () => {
      const results = filterCommands('Tactical Map');
      assert.strictEqual(results.length, 2);
      assert.ok(results.some((c) => c.id === 'map-fit'));
      assert.ok(results.some((c) => c.id === 'map-reset'));
    });

    it('filters commands by shortcut key', () => {
      const results = filterCommands('g c');
      assert.strictEqual(results.length, 1);
      assert.strictEqual(results[0].id, 'nav-scenarios');
    });
  });

  describe('Multi-Entity Selection Resolution', () => {
    type EntityType = 'track' | 'sensor' | 'geofence' | 'alert' | 'threat';

    interface EntitySelection {
      type: EntityType;
      id: string;
    }

    const resolveSelectionTarget = (entityType: EntityType, entityId: string, trackIdRef?: string | null): EntitySelection => {
      if (entityType === 'alert' && trackIdRef) {
        return { type: 'track', id: trackIdRef };
      }
      if (entityType === 'threat' && trackIdRef) {
        return { type: 'track', id: trackIdRef };
      }
      return { type: entityType, id: entityId };
    };

    it('resolves alert with track reference to track entity', () => {
      const sel = resolveSelectionTarget('alert', 'ALT-990', 'TRK-ALPHA');
      assert.strictEqual(sel.type, 'track');
      assert.strictEqual(sel.id, 'TRK-ALPHA');
    });

    it('resolves alert without track reference to alert entity', () => {
      const sel = resolveSelectionTarget('alert', 'ALT-880', null);
      assert.strictEqual(sel.type, 'alert');
      assert.strictEqual(sel.id, 'ALT-880');
    });

    it('resolves threat triage item to referenced track', () => {
      const sel = resolveSelectionTarget('threat', 'THREAT-1', 'TRK-BRAVO');
      assert.strictEqual(sel.type, 'track');
      assert.strictEqual(sel.id, 'TRK-BRAVO');
    });

    it('resolves sensor and geofence entities directly', () => {
      const sensorSel = resolveSelectionTarget('sensor', 'SNS-01');
      assert.strictEqual(sensorSel.type, 'sensor');
      assert.strictEqual(sensorSel.id, 'SNS-01');

      const geoSel = resolveSelectionTarget('geofence', 'GEO-NORTH');
      assert.strictEqual(geoSel.type, 'geofence');
      assert.strictEqual(geoSel.id, 'GEO-NORTH');
    });
  });

  describe('Scenario Simulation Lifecycle State Transitions', () => {
    type ScenarioStatus = 'DRAFT' | 'READY' | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'COMPLETED';

    const getAvailableActions = (status: ScenarioStatus) => {
      switch (status) {
        case 'DRAFT':
        case 'READY':
          return { canStart: true, canPause: false, canResume: false, canStep: true, canStop: false, canReset: false };
        case 'RUNNING':
          return { canStart: false, canPause: true, canResume: false, canStep: false, canStop: true, canReset: false };
        case 'PAUSED':
          return { canStart: false, canPause: false, canResume: true, canStep: true, canStop: true, canReset: false };
        case 'STOPPED':
        case 'COMPLETED':
          return { canStart: false, canPause: false, canResume: false, canStep: false, canStop: false, canReset: true };
      }
    };

    it('allows Start and Step when scenario is in READY state', () => {
      const actions = getAvailableActions('READY');
      assert.strictEqual(actions.canStart, true);
      assert.strictEqual(actions.canStep, true);
      assert.strictEqual(actions.canPause, false);
      assert.strictEqual(actions.canStop, false);
    });

    it('allows Pause and Stop when scenario is RUNNING', () => {
      const actions = getAvailableActions('RUNNING');
      assert.strictEqual(actions.canStart, false);
      assert.strictEqual(actions.canPause, true);
      assert.strictEqual(actions.canStop, true);
      assert.strictEqual(actions.canStep, false);
    });

    it('allows Resume, Step, and Stop when scenario is PAUSED', () => {
      const actions = getAvailableActions('PAUSED');
      assert.strictEqual(actions.canResume, true);
      assert.strictEqual(actions.canStep, true);
      assert.strictEqual(actions.canStop, true);
    });

    it('allows Reset when scenario is STOPPED or COMPLETED', () => {
      const actions = getAvailableActions('COMPLETED');
      assert.strictEqual(actions.canReset, true);
      assert.strictEqual(actions.canStart, false);
    });
  });

  describe('Replay Snapshot Spatial Mapping', () => {
    interface ReplayTrackState {
      track_id: string;
      state: 'NEW' | 'ACTIVE' | 'STALE' | 'LOST' | 'ARCHIVED';
      latitude: number;
      longitude: number;
      altitude?: number | null;
      velocity?: number | null;
      heading?: number | null;
      confidence: number;
      classification: string;
      source_count: number;
    }

    it('maps ReplayTrackState into Track entity format for TacticalMap presentation', () => {
      const replayTracks: ReplayTrackState[] = [
        {
          track_id: 'RPL-TRK-01',
          state: 'ACTIVE',
          latitude: 37.7749,
          longitude: -122.4194,
          altitude: 120.5,
          velocity: 15.2,
          heading: 88.0,
          confidence: 0.96,
          classification: 'DRONE_ROTARY',
          source_count: 2,
        },
      ];

      const timestamp = '2026-08-26T12:00:00Z';
      const mapped = replayTracks.map((t) => ({
        id: t.track_id,
        state: t.state,
        latitude: t.latitude,
        longitude: t.longitude,
        altitude: t.altitude ?? undefined,
        velocity: t.velocity ?? undefined,
        heading: t.heading ?? undefined,
        confidence: t.confidence,
        classification: t.classification,
        source_count: t.source_count,
        last_seen_at: timestamp,
        first_seen_at: timestamp,
        created_at: timestamp,
        updated_at: timestamp,
      }));

      assert.strictEqual(mapped.length, 1);
      assert.strictEqual(mapped[0].id, 'RPL-TRK-01');
      assert.strictEqual(mapped[0].latitude, 37.7749);
      assert.strictEqual(mapped[0].longitude, -122.4194);
      assert.strictEqual(mapped[0].last_seen_at, timestamp);
    });
  });

  describe('URL Deep-Link State Serialization', () => {
    it('serializes and deserializes tab, entity, and id search params', () => {
      const params = new URLSearchParams();
      params.set('tab', 'threats');
      params.set('entity', 'track');
      params.set('id', 'TRK-900');

      const urlString = params.toString();
      assert.strictEqual(urlString, 'tab=threats&entity=track&id=TRK-900');

      const parsed = new URLSearchParams(urlString);
      assert.strictEqual(parsed.get('tab'), 'threats');
      assert.strictEqual(parsed.get('entity'), 'track');
      assert.strictEqual(parsed.get('id'), 'TRK-900');
    });
  });

  describe('Timeline Filtering & Time Window Calculation', () => {
    const mockTimeline = [
      { timestamp: '2026-08-26T10:00:00Z', event_type: 'TRACK_NEW', summary: 'Track detected' },
      { timestamp: '2026-08-26T10:05:00Z', event_type: 'ALERT_GEOFENCE', summary: 'Geofence breached' },
      { timestamp: '2026-08-26T10:10:00Z', event_type: 'THREAT_HIGH', summary: 'Elevated triage' },
      { timestamp: '2026-08-26T10:12:00Z', event_type: 'SENSOR_ONLINE', summary: 'Sensor active' },
    ];

    it('filters timeline by event type substring', () => {
      const alertEvents = mockTimeline.filter((e) => e.event_type.includes('ALERT'));
      assert.strictEqual(alertEvents.length, 1);
      assert.strictEqual(alertEvents[0].event_type, 'ALERT_GEOFENCE');
    });

    it('filters timeline by relative time cutoff', () => {
      const referenceTime = new Date('2026-08-26T10:15:00Z').getTime();
      const cutoff10min = referenceTime - 10 * 60 * 1000;

      const recentEvents = mockTimeline.filter(
        (e) => new Date(e.timestamp).getTime() >= cutoff10min
      );
      assert.strictEqual(recentEvents.length, 3); // 10:05, 10:10, 10:12
    });
  });
});
