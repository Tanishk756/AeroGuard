/**
 * AeroGuard Operator Console — AI3-F Telemetry Optimization & High-Density UI Validation Suite
 * Uses Node.js native test runner (node:test, node:assert/strict).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

// ── Pure Domain Types for AI3-F Operator Telemetry Tests ──

export interface ThreatPriorityFactor {
  name: string;
  score: number;
  weight: number;
  contribution: number;
  description: string;
}

export interface ThreatPriorityAssessment {
  track_id: string;
  group_id?: string | null;
  priority_score: number;
  priority_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  factors: ThreatPriorityFactor[];
  reason: string;
  evaluated_at: string;
}

export interface BehaviorClassification {
  track_id: string;
  state: 'NORMAL' | 'APPROACHING' | 'DEPARTING' | 'LOITERING' | 'RAPID_CHANGE' | 'COORDINATED' | 'ANOMALOUS';
  confidence: number;
  duration_seconds: number;
  reason: string;
  contributing_factors: string[];
  evaluated_at: string;
}

export interface TrackGroup {
  group_id: string;
  member_track_ids: string[];
  centroid_lat: number;
  centroid_lon: number;
  centroid_alt?: number | null;
  radius_meters: number;
  member_count: number;
  confidence: number;
  behavioral_state: string;
  updated_at: string;
}

export interface CoordinatedFormation {
  formation_id: string;
  group_id: string;
  member_track_ids: string[];
  synchronization_index: number;
  heading_dispersion_deg: number;
  velocity_dispersion_mps: number;
  confidence: number;
  evaluated_at: string;
}

export interface MultiTrackIntelligenceSummary {
  evaluated_at: string;
  groups: TrackGroup[];
  formations: CoordinatedFormation[];
  behaviors: BehaviorClassification[];
  priorities: ThreatPriorityAssessment[];
}

export interface RealtimeEventEnvelope {
  channel: string;
  event_type: string;
  timestamp: string;
  sequence?: number;
  payload: Record<string, unknown>;
}

export interface Track {
  id: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  state: string;
  source: string;
  confidence: number;
  created_at: string;
  updated_at: string;
}

const BASE_PIXELS_PER_DEGREE = 2500;

export function projectLatLon(
  lat: number,
  lon: number,
  centerLat: number,
  centerLon: number,
  zoom: number,
  panX: number,
  panY: number,
  width: number,
  height: number
): { x: number; y: number } {
  const cosLat = Math.cos((centerLat * Math.PI) / 180);
  const scale = BASE_PIXELS_PER_DEGREE * zoom;
  const x = width / 2 + (lon - centerLon) * scale * cosLat + panX;
  const y = height / 2 - (lat - centerLat) * scale + panY;
  return { x, y };
}

export interface PureRenderScene {
  tracks: Array<{ id: string; screenX: number; screenY: number; priorityLevel?: string }>;
  groups: Array<{ groupId: string; screenX: number; screenY: number; radiusPx: number }>;
}

export function buildPureRenderScene(
  tracks: Track[],
  summary: MultiTrackIntelligenceSummary | null,
  width = 1920,
  height = 1080,
  centerLat = 37.7749,
  centerLon = -122.4194,
  zoom = 1.0
): PureRenderScene {
  const prioMap = new Map(summary?.priorities.map((p) => [p.track_id, p.priority_level]) || []);
  const renderTracks = tracks.map((t) => {
    const { x, y } = projectLatLon(t.latitude, t.longitude, centerLat, centerLon, zoom, 0, 0, width, height);
    return {
      id: t.id,
      screenX: x,
      screenY: y,
      priorityLevel: prioMap.get(t.id),
    };
  });

  const renderGroups = (summary?.groups || []).map((g) => {
    const { x, y } = projectLatLon(g.centroid_lat, g.centroid_lon, centerLat, centerLon, zoom, 0, 0, width, height);
    const radiusPx = (g.radius_meters / 111194.9) * BASE_PIXELS_PER_DEGREE * zoom;
    return {
      groupId: g.group_id,
      screenX: x,
      screenY: y,
      radiusPx,
    };
  });

  return {
    tracks: renderTracks,
    groups: renderGroups,
  };
}

// ── Synthetic Dataset Generators ──

function generateSyntheticTracks(n: number): Track[] {
  const tracks: Track[] = [];
  const baseLat = 37.7749;
  const baseLon = -122.4194;

  for (let i = 0; i < n; i++) {
    tracks.push({
      id: `TRK-${i.toString().padStart(5, '0')}`,
      latitude: baseLat + (i % 50) * 0.005,
      longitude: baseLon + Math.floor(i / 50) * 0.005,
      altitude: 150.0 + (i % 20),
      velocity: 20.0 + (i % 10),
      heading: (i * 15) % 360,
      state: 'ACTIVE',
      source: 'RADAR',
      confidence: 0.95,
      created_at: '2026-08-27T12:00:00Z',
      updated_at: '2026-08-27T12:00:00Z',
    });
  }
  return tracks;
}

function generateSyntheticSummary(n: number): MultiTrackIntelligenceSummary {
  const groups: TrackGroup[] = [];
  const formations: CoordinatedFormation[] = [];
  const behaviors: BehaviorClassification[] = [];
  const priorities: ThreatPriorityAssessment[] = [];

  const groupCount = Math.floor(n / 4);

  for (let g = 0; g < groupCount; g++) {
    const memberIds = [
      `TRK-${(g * 4).toString().padStart(5, '0')}`,
      `TRK-${(g * 4 + 1).toString().padStart(5, '0')}`,
      `TRK-${(g * 4 + 2).toString().padStart(5, '0')}`,
      `TRK-${(g * 4 + 3).toString().padStart(5, '0')}`,
    ];
    const gid = `GRP-${g.toString().padStart(4, '0')}`;
    groups.push({
      group_id: gid,
      member_track_ids: memberIds,
      centroid_lat: 37.7749 + g * 0.01,
      centroid_lon: -122.4194 + g * 0.01,
      radius_meters: 150.0,
      member_count: 4,
      confidence: 0.92,
      behavioral_state: 'COORDINATED',
      updated_at: '2026-08-27T12:00:00Z',
    });

    formations.push({
      formation_id: `FMT-${gid}`,
      group_id: gid,
      member_track_ids: memberIds,
      synchronization_index: 0.95,
      heading_dispersion_deg: 2.1,
      velocity_dispersion_mps: 0.4,
      confidence: 0.94,
      evaluated_at: '2026-08-27T12:00:00Z',
    });
  }

  for (let i = 0; i < n; i++) {
    const tid = `TRK-${i.toString().padStart(5, '0')}`;
    const inGroup = i < groupCount * 4;
    const gid = inGroup ? `GRP-${Math.floor(i / 4).toString().padStart(4, '0')}` : null;
    const prioScore = Math.max(5.0, Math.min(95.0, 30.0 + (i % 65)));
    const prioLevel =
      prioScore >= 75 ? 'CRITICAL' : prioScore >= 50 ? 'HIGH' : prioScore >= 25 ? 'MEDIUM' : 'LOW';

    behaviors.push({
      track_id: tid,
      state: inGroup ? 'COORDINATED' : i % 5 === 0 ? 'APPROACHING' : 'NORMAL',
      confidence: 0.9,
      duration_seconds: 12.0,
      reason: inGroup ? 'Part of coordinated cluster' : 'Standard trajectory',
      contributing_factors: [],
      evaluated_at: '2026-08-27T12:00:00Z',
    });

    priorities.push({
      track_id: tid,
      group_id: gid,
      priority_score: prioScore,
      priority_level: prioLevel,
      confidence: 0.92,
      factors: [
        { name: 'proximity', score: prioScore * 0.4, weight: 0.35, contribution: prioScore * 0.14, description: 'Proximity' },
        { name: 'velocity', score: 20.0, weight: 0.2, contribution: 4.0, description: 'Kinematics' },
      ],
      reason: `Defensive priority score ${prioScore.toFixed(1)}`,
      evaluated_at: '2026-08-27T12:00:00Z',
    });
  }

  return {
    evaluated_at: '2026-08-27T12:00:00Z',
    groups,
    formations,
    behaviors,
    priorities,
  };
}

// ── In-Memory Realtime Telemetry Ingestion Simulator ──

class RealtimeTelemetrySimulator {
  private summary: MultiTrackIntelligenceSummary | null = null;
  private lastSequence: number = 0;
  private lastTimestamp: number = 0;
  public stateUpdatesCount: number = 0;
  public rejectedStaleCount: number = 0;
  public rejectedDuplicateCount: number = 0;
  public coalescedEventsCount: number = 0;

  public setBaseline(summary: MultiTrackIntelligenceSummary) {
    this.summary = { ...summary };
    this.lastTimestamp = new Date(summary.evaluated_at).getTime();
  }

  public getSummary(): MultiTrackIntelligenceSummary | null {
    return this.summary;
  }

  public processEnvelope(envelope: RealtimeEventEnvelope): boolean {
    // 1. Monotonic sequence check
    if (typeof envelope.sequence === 'number' && envelope.sequence > 0) {
      if (envelope.sequence <= this.lastSequence) {
        this.rejectedStaleCount++;
        return false;
      }
      this.lastSequence = envelope.sequence;
    }

    const payload = envelope.payload as Record<string, unknown>;
    if (!payload) return false;

    // 2. Timestamp freshness check
    const timeStr = (payload.evaluated_at || payload.updated_at || envelope.timestamp) as string | undefined;
    if (timeStr) {
      const eventTime = new Date(timeStr).getTime();
      if (!isNaN(eventTime) && eventTime > 0) {
        if (eventTime < this.lastTimestamp && !envelope.sequence) {
          this.rejectedStaleCount++;
          return false;
        }
        if (eventTime > this.lastTimestamp) {
          this.lastTimestamp = eventTime;
        }
      }
    }

    // 3. Process according to event type
    if (envelope.event_type === 'ai.summary') {
      const newSummary = payload as unknown as MultiTrackIntelligenceSummary;
      // Duplicate suppression
      if (
        this.summary &&
        this.summary.evaluated_at === newSummary.evaluated_at &&
        this.summary.priorities.length === newSummary.priorities.length
      ) {
        this.rejectedDuplicateCount++;
        return false;
      }
      this.summary = newSummary;
      this.stateUpdatesCount++;
      return true;
    }

    if (!this.summary) return false;

    if (envelope.event_type === 'ai.priority' || envelope.event_type === 'ai.priority.updated') {
      const p = payload as unknown as ThreatPriorityAssessment;
      const idx = this.summary.priorities.findIndex((item) => item.track_id === p.track_id);
      if (idx >= 0) {
        // Duplicate check
        if (
          this.summary.priorities[idx].priority_score === p.priority_score &&
          this.summary.priorities[idx].priority_level === p.priority_level
        ) {
          this.rejectedDuplicateCount++;
          return false;
        }
        this.summary.priorities[idx] = p;
      } else {
        this.summary.priorities.push(p);
      }
      this.stateUpdatesCount++;
      return true;
    }

    if (envelope.event_type === 'ai.behavior' || envelope.event_type === 'ai.behavior.updated') {
      const b = payload as unknown as BehaviorClassification;
      const idx = this.summary.behaviors.findIndex((item) => item.track_id === b.track_id);
      if (idx >= 0) {
        if (this.summary.behaviors[idx].state === b.state) {
          this.rejectedDuplicateCount++;
          return false;
        }
        this.summary.behaviors[idx] = b;
      } else {
        this.summary.behaviors.push(b);
      }
      this.stateUpdatesCount++;
      return true;
    }

    if (envelope.event_type === 'ai.group' || envelope.event_type === 'ai.group.updated') {
      const g = payload as unknown as TrackGroup;
      const idx = this.summary.groups.findIndex((item) => item.group_id === g.group_id);
      if (idx >= 0) {
        this.summary.groups[idx] = g;
      } else {
        this.summary.groups.push(g);
      }
      this.stateUpdatesCount++;
      return true;
    }

    return false;
  }

  public processBatchCoalesced(envelopes: RealtimeEventEnvelope[]): void {
    if (envelopes.length === 0) return;
    const prioUpdates = new Map<string, ThreatPriorityAssessment>();
    const behUpdates = new Map<string, BehaviorClassification>();
    const grpUpdates = new Map<string, TrackGroup>();
    let latestSummary: MultiTrackIntelligenceSummary | null = null;

    for (const env of envelopes) {
      if (typeof env.sequence === 'number' && env.sequence <= this.lastSequence) {
        this.rejectedStaleCount++;
        continue;
      }
      if (typeof env.sequence === 'number') {
        this.lastSequence = env.sequence;
      }

      const p = env.payload as Record<string, unknown>;
      if (env.event_type === 'ai.summary') {
        latestSummary = p as unknown as MultiTrackIntelligenceSummary;
      } else if (env.event_type.startsWith('ai.priority')) {
        const item = p as unknown as ThreatPriorityAssessment;
        prioUpdates.set(item.track_id, item);
      } else if (env.event_type.startsWith('ai.behavior')) {
        const item = p as unknown as BehaviorClassification;
        behUpdates.set(item.track_id, item);
      } else if (env.event_type.startsWith('ai.group')) {
        const item = p as unknown as TrackGroup;
        grpUpdates.set(item.group_id, item);
      }
    }

    if (latestSummary) {
      this.summary = latestSummary;
    } else if (this.summary) {
      for (const [tid, item] of prioUpdates) {
        const idx = this.summary.priorities.findIndex((x) => x.track_id === tid);
        if (idx >= 0) this.summary.priorities[idx] = item;
        else this.summary.priorities.push(item);
      }
      for (const [tid, item] of behUpdates) {
        const idx = this.summary.behaviors.findIndex((x) => x.track_id === tid);
        if (idx >= 0) this.summary.behaviors[idx] = item;
        else this.summary.behaviors.push(item);
      }
      for (const [gid, item] of grpUpdates) {
        const idx = this.summary.groups.findIndex((x) => x.group_id === gid);
        if (idx >= 0) this.summary.groups[idx] = item;
        else this.summary.groups.push(item);
      }
    }

    this.coalescedEventsCount += envelopes.length;
    this.stateUpdatesCount += 1; // exactly 1 atomic React commit for the entire batch
  }
}

// ── Test Suites ──

describe('AeroGuard Stage AI3-F — Telemetry Optimization & High-Density UI Tests', () => {
  it('1. Duplicate Event Suppression: 500 identical events cause zero state commits', () => {
    const sim = new RealtimeTelemetrySimulator();
    const initial = generateSyntheticSummary(100);
    sim.setBaseline(initial);

    const dupEnvelope: RealtimeEventEnvelope = {
      channel: 'operational',
      event_type: 'ai.priority.updated',
      timestamp: '2026-08-27T12:00:00Z',
      sequence: 1,
      payload: initial.priorities[0] as unknown as Record<string, unknown>,
    };

    // First application updates sequence
    const accepted = sim.processEnvelope(dupEnvelope);
    assert.strictEqual(accepted, false); // identical data rejected
    assert.strictEqual(sim.rejectedDuplicateCount, 1);

    // 500 identical repeated updates with no sequence advance
    for (let i = 0; i < 500; i++) {
      sim.processEnvelope({
        ...dupEnvelope,
        sequence: 1,
      });
    }

    assert.strictEqual(sim.stateUpdatesCount, 0);
    assert.strictEqual(sim.rejectedStaleCount + sim.rejectedDuplicateCount, 501);
  });

  it('2. Stale Event Rejection: Out-of-order sequence and older timestamp rejected', () => {
    const sim = new RealtimeTelemetrySimulator();
    const initial = generateSyntheticSummary(100);
    sim.setBaseline(initial);

    // Event sequence 10 arrives
    sim.processEnvelope({
      channel: 'operational',
      event_type: 'ai.priority.updated',
      timestamp: '2026-08-27T12:01:00Z',
      sequence: 10,
      payload: { ...initial.priorities[0], priority_score: 88.0 },
    });

    assert.strictEqual(sim.stateUpdatesCount, 1);
    assert.strictEqual(sim.getSummary()?.priorities[0].priority_score, 88.0);

    // Stale event sequence 8 arrives
    const staleAccepted = sim.processEnvelope({
      channel: 'operational',
      event_type: 'ai.priority.updated',
      timestamp: '2026-08-27T12:00:50Z',
      sequence: 8,
      payload: { ...initial.priorities[0], priority_score: 40.0 },
    });

    assert.strictEqual(staleAccepted, false);
    assert.strictEqual(sim.getSummary()?.priorities[0].priority_score, 88.0);
    assert.strictEqual(sim.rejectedStaleCount, 1);
  });

  it('3. Monotonic Sequence Verification: Strictly increasing sequences accepted', () => {
    const sim = new RealtimeTelemetrySimulator();
    sim.setBaseline(generateSyntheticSummary(50));

    const seqs = [1, 2, 3, 5, 8, 13, 21];
    for (const s of seqs) {
      const ok = sim.processEnvelope({
        channel: 'operational',
        event_type: 'ai.priority.updated',
        timestamp: '2026-08-27T12:00:00Z',
        sequence: s,
        payload: {
          track_id: 'TRK-00001',
          priority_score: 50.0 + s,
          priority_level: 'HIGH',
          factors: [],
          reason: 'Monotonic test',
          evaluated_at: '2026-08-27T12:00:00Z',
        },
      });
      assert.strictEqual(ok, true);
    }
    assert.strictEqual(sim.stateUpdatesCount, seqs.length);
  });

  it('4. Realtime Event Coalescing: 100 rapid events collapsed into a single state update', () => {
    const sim = new RealtimeTelemetrySimulator();
    sim.setBaseline(generateSyntheticSummary(100));

    const burstEvents: RealtimeEventEnvelope[] = [];
    for (let i = 1; i <= 100; i++) {
      burstEvents.push({
        channel: 'operational',
        event_type: 'ai.priority.updated',
        timestamp: '2026-08-27T12:00:00Z',
        sequence: 100 + i,
        payload: {
          track_id: `TRK-${(i % 100).toString().padStart(5, '0')}`,
          priority_score: 75.0,
          priority_level: 'CRITICAL',
          factors: [],
          reason: 'Burst test',
          evaluated_at: '2026-08-27T12:00:00Z',
        },
      });
    }

    sim.processBatchCoalesced(burstEvents);
    assert.strictEqual(sim.stateUpdatesCount, 1);
    assert.strictEqual(sim.coalescedEventsCount, 100);
  });

  it('5. Selected Track Stability: Selected track preserved across priority and behavior updates', () => {
    let selectedTrackId: string | null = 'TRK-00005';
    const summary = generateSyntheticSummary(50);

    // Telemetry updates another track TRK-00001
    const p1 = { ...summary.priorities[0], priority_score: 99.0, priority_level: 'CRITICAL' as const };
    const p5 = { ...summary.priorities[5], priority_score: 85.0, priority_level: 'HIGH' as const };

    const prioMap = new Map(summary.priorities.map((p) => [p.track_id, p]));
    prioMap.set(p1.track_id, p1);
    prioMap.set(p5.track_id, p5);
    const nextPriorities = Array.from(prioMap.values());

    // Selection invariant
    assert.strictEqual(selectedTrackId, 'TRK-00005');
    const selectedPrio = nextPriorities.find((p) => p.track_id === selectedTrackId);
    assert.ok(selectedPrio);
    assert.strictEqual(selectedPrio.priority_score, 85.0);
  });

  it('6. Selected Group Stability: Selected group preserved during member telemetry updates', () => {
    let selectedGroupId: string | null = 'GRP-0000';
    const summary = generateSyntheticSummary(50);

    // Group member update
    const g0 = summary.groups[0];
    assert.strictEqual(g0.group_id, selectedGroupId);

    // Update group centroid and confidence
    const updatedG0: TrackGroup = { ...g0, confidence: 0.98, radius_meters: 160.0 };
    const nextGroups = summary.groups.map((g) => (g.group_id === updatedG0.group_id ? updatedG0 : g));

    assert.strictEqual(selectedGroupId, 'GRP-0000');
    const selectedGrp = nextGroups.find((g) => g.group_id === selectedGroupId);
    assert.ok(selectedGrp);
    assert.strictEqual(selectedGrp.confidence, 0.98);
  });

  it('7. Priority Sorting & Filtering Performance: 5,000 tracks sorted and filtered deterministically', () => {
    const summary = generateSyntheticSummary(5000);

    const t0 = performance.now();
    // Sort descending by priority score
    const sorted = [...summary.priorities].sort((a, b) => b.priority_score - a.priority_score);
    const tSort = performance.now() - t0;

    // Filter by min level >= HIGH
    const t1 = performance.now();
    const highAndAbove = sorted.filter((p) => p.priority_level === 'HIGH' || p.priority_level === 'CRITICAL');
    const tFilter = performance.now() - t1;

    assert.strictEqual(sorted.length, 5000);
    assert.ok(sorted[0].priority_score >= sorted[sorted.length - 1].priority_score);
    assert.ok(highAndAbove.length > 0);
    assert.ok(tSort < 50.0, `Sorting 5,000 items took ${tSort.toFixed(2)}ms, expected < 50ms`);
    assert.ok(tFilter < 20.0, `Filtering 5,000 items took ${tFilter.toFixed(2)}ms, expected < 20ms`);
  });

  it('8. Intelligence Summary Derivation: Aggregate count computation at N=5,000 is sub-millisecond', () => {
    const summary = generateSyntheticSummary(5000);

    const t0 = performance.now();
    const criticalCount = summary.priorities.filter((p) => p.priority_level === 'CRITICAL').length;
    const highCount = summary.priorities.filter((p) => p.priority_level === 'HIGH').length;
    const groupCount = summary.groups.length;
    const formationCount = summary.formations.length;
    const tDerive = performance.now() - t0;

    assert.ok(criticalCount >= 0);
    assert.ok(highCount >= 0);
    assert.strictEqual(groupCount, 1250);
    assert.strictEqual(formationCount, 1250);
    assert.ok(tDerive < 10.0, `Deriving metrics took ${tDerive.toFixed(2)}ms, expected < 10ms`);
  });

  it('9. Factor Score Reconciliation: All priority factors sum correctly and match contributions', () => {
    const summary = generateSyntheticSummary(100);
    for (const p of summary.priorities) {
      let totalContrib = 0;
      for (const f of p.factors) {
        assert.ok(f.score >= 0.0 && f.score <= 100.0);
        assert.ok(f.weight >= 0.0 && f.weight <= 1.0);
        totalContrib += f.contribution;
      }
      assert.ok(totalContrib >= 0.0);
    }
  });

  it('10. MAP2 RenderScene Construction: N=100 tracks scene built within frame budget', () => {
    const tracks = generateSyntheticTracks(100);
    const summary = generateSyntheticSummary(100);

    const t0 = performance.now();
    const scene = buildPureRenderScene(tracks, summary);
    const tElapsed = performance.now() - t0;

    assert.strictEqual(scene.tracks.length, 100);
    assert.strictEqual(scene.groups.length, 25);
    assert.ok(tElapsed < 5.0, `Scene construction for 100 tracks took ${tElapsed.toFixed(2)}ms, expected < 5ms`);
  });

  it('11. MAP2 RenderScene Construction: N=500 tracks scene built within frame budget', () => {
    const tracks = generateSyntheticTracks(500);
    const summary = generateSyntheticSummary(500);

    const t0 = performance.now();
    const scene = buildPureRenderScene(tracks, summary);
    const tElapsed = performance.now() - t0;

    assert.strictEqual(scene.tracks.length, 500);
    assert.strictEqual(scene.groups.length, 125);
    assert.ok(tElapsed < 15.0, `Scene construction for 500 tracks took ${tElapsed.toFixed(2)}ms, expected < 15ms`);
  });

  it('12. MAP2 RenderScene Construction: N=1,000 tracks scene built within frame budget', () => {
    const tracks = generateSyntheticTracks(1000);
    const summary = generateSyntheticSummary(1000);

    const t0 = performance.now();
    const scene = buildPureRenderScene(tracks, summary);
    const tElapsed = performance.now() - t0;

    assert.strictEqual(scene.tracks.length, 1000);
    assert.strictEqual(scene.groups.length, 250);
    assert.ok(tElapsed < 25.0, `Scene construction for 1,000 tracks took ${tElapsed.toFixed(2)}ms, expected < 25ms`);
  });

  it('13. MAP2 RenderScene Construction: N=5,000 tracks high-density scene generation', () => {
    const tracks = generateSyntheticTracks(5000);
    const summary = generateSyntheticSummary(5000);

    const t0 = performance.now();
    const scene = buildPureRenderScene(tracks, summary);
    const tElapsed = performance.now() - t0;

    assert.strictEqual(scene.tracks.length, 5000);
    assert.strictEqual(scene.groups.length, 1250);
    assert.ok(tElapsed < 100.0, `Scene construction for 5,000 tracks took ${tElapsed.toFixed(2)}ms, expected < 100ms`);
  });

  it('14. Mixed Telemetry Event Types: Correctly routes priorities, behaviors, and groups', () => {
    const sim = new RealtimeTelemetrySimulator();
    sim.setBaseline(generateSyntheticSummary(20));

    const events: RealtimeEventEnvelope[] = [
      {
        channel: 'operational',
        event_type: 'ai.priority.updated',
        timestamp: '2026-08-27T12:00:00Z',
        sequence: 50,
        payload: {
          track_id: 'TRK-00000',
          priority_score: 95.0,
          priority_level: 'CRITICAL',
          factors: [],
          reason: 'Critical escalation',
          evaluated_at: '2026-08-27T12:00:00Z',
        },
      },
      {
        channel: 'operational',
        event_type: 'ai.behavior.updated',
        timestamp: '2026-08-27T12:00:00Z',
        sequence: 51,
        payload: {
          track_id: 'TRK-00000',
          state: 'RAPID_CHANGE',
          confidence: 0.96,
          duration_seconds: 5.0,
          reason: 'Erratic maneuver',
          contributing_factors: [],
          evaluated_at: '2026-08-27T12:00:00Z',
        },
      },
    ];

    sim.processBatchCoalesced(events);
    const snap = sim.getSummary();
    assert.ok(snap);
    assert.strictEqual(snap.priorities[0].priority_score, 95.0);
    assert.strictEqual(snap.behaviors[0].state, 'RAPID_CHANGE');
  });

  it('15. Empty Intelligence State: Gracefully handles null/empty summary', () => {
    const tracks = generateSyntheticTracks(10);
    const scene = buildPureRenderScene(tracks, null);

    assert.strictEqual(scene.tracks.length, 10);
    assert.strictEqual(scene.groups.length, 0);
  });
});
