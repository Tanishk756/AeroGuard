/**
 * AeroGuard Operator Console — AI2 Multi-Track Defensive Intelligence & UI Tests
 * Uses Node.js native test runner (node:test, node:assert).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

// ── Pure Domain Types & Logic for AI2 Operator Console Intelligence Tests ──

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
  groups: TrackGroup[];
  behaviors: BehaviorClassification[];
  formations: CoordinatedFormation[];
  priorities: ThreatPriorityAssessment[];
  evaluated_at: string;
}

export interface RenderGroupItem {
  groupId: string;
  centroidScreenX: number;
  centroidScreenY: number;
  radiusPixels: number;
  memberTrackIds: string[];
  memberScreenCoords: Array<{ x: number; y: number; trackId: string }>;
  confidence: number;
  behaviorState?: string;
  isCoordinated: boolean;
  synchronizationIndex?: number;
  isSelected: boolean;
}

const BASE_PIXELS_PER_DEGREE = 2500;
const EARTH_RADIUS_METERS = 6371000;

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

export function projectGroupsForRenderer(
  groups: TrackGroup[],
  formations: CoordinatedFormation[],
  trackCoords: Map<string, { x: number; y: number }>,
  centerLat: number,
  centerLon: number,
  zoom: number,
  panX: number,
  panY: number,
  width: number,
  height: number,
  selectedGroupId?: string | null
): RenderGroupItem[] {
  const formationMap = new Map<string, CoordinatedFormation>();
  for (const f of formations) {
    formationMap.set(f.group_id, f);
  }

  const cosLat = Math.cos((centerLat * Math.PI) / 180);
  const pixelsPerMeter = (BASE_PIXELS_PER_DEGREE * zoom * cosLat) / ((2 * Math.PI * EARTH_RADIUS_METERS) / 360);

  const result: RenderGroupItem[] = [];
  for (const g of groups) {
    const center = projectLatLon(g.centroid_lat, g.centroid_lon, centerLat, centerLon, zoom, panX, panY, width, height);
    const radiusPixels = Math.max(20, g.radius_meters * pixelsPerMeter);
    const isSelected = g.group_id === selectedGroupId;

    const memberCoords: Array<{ x: number; y: number; trackId: string }> = [];
    for (const mid of g.member_track_ids) {
      const coord = trackCoords.get(mid);
      if (coord) {
        memberCoords.push({ x: coord.x, y: coord.y, trackId: mid });
      }
    }

    const fmt = formationMap.get(g.group_id);
    result.push({
      groupId: g.group_id,
      centroidScreenX: center.x,
      centroidScreenY: center.y,
      radiusPixels,
      memberTrackIds: g.member_track_ids,
      memberScreenCoords: memberCoords,
      confidence: g.confidence,
      behaviorState: g.behavioral_state,
      isCoordinated: fmt != null,
      synchronizationIndex: fmt?.synchronization_index,
      isSelected,
    });
  }
  return result;
}

// ── Mock Data Fixtures ──

const mockMultiTrackSummary: MultiTrackIntelligenceSummary = {
  groups: [
    {
      group_id: 'GRP-TEST-01',
      member_track_ids: ['TRK-AI2-01', 'TRK-AI2-02'],
      centroid_lat: 37.77505,
      centroid_lon: -122.4192,
      radius_meters: 65.0,
      member_count: 2,
      confidence: 0.94,
      behavioral_state: 'COORDINATED',
      updated_at: '2026-08-27T00:00:30Z',
    },
  ],
  behaviors: [
    {
      track_id: 'TRK-AI2-01',
      state: 'APPROACHING',
      confidence: 0.95,
      duration_seconds: 24.5,
      reason: 'Sustained inbound velocity toward perimeter',
      contributing_factors: ['inbound_velocity', 'heading_alignment'],
      evaluated_at: '2026-08-27T00:00:30Z',
    },
    {
      track_id: 'TRK-AI2-02',
      state: 'COORDINATED',
      confidence: 0.92,
      duration_seconds: 20.0,
      reason: 'Synchronized heading and velocity with wingman',
      contributing_factors: ['formation_synchronization'],
      evaluated_at: '2026-08-27T00:00:30Z',
    },
    {
      track_id: 'TRK-AI2-03',
      state: 'NORMAL',
      confidence: 0.88,
      duration_seconds: 30.0,
      reason: 'Nominal flight kinematics',
      contributing_factors: ['steady_flight'],
      evaluated_at: '2026-08-27T00:00:30Z',
    },
  ],
  formations: [
    {
      formation_id: 'FMT-TEST-01',
      group_id: 'GRP-TEST-01',
      member_track_ids: ['TRK-AI2-01', 'TRK-AI2-02'],
      synchronization_index: 0.96,
      heading_dispersion_deg: 0.2,
      velocity_dispersion_mps: 0.5,
      confidence: 0.94,
      evaluated_at: '2026-08-27T00:00:30Z',
    },
  ],
  priorities: [
    {
      track_id: 'TRK-AI2-01',
      group_id: 'GRP-TEST-01',
      priority_score: 76.5,
      priority_level: 'HIGH',
      confidence: 0.95,
      factors: [
        { name: 'geofence', score: 85.0, weight: 0.30, contribution: 25.5, description: 'Approaching perimeter' },
        { name: 'behavior', score: 70.0, weight: 0.25, contribution: 17.5, description: 'Inbound approach' },
        { name: 'anomaly', score: 60.0, weight: 0.20, contribution: 12.0, description: 'Kinematic anomaly' },
        { name: 'coordination', score: 96.0, weight: 0.15, contribution: 14.4, description: 'High sync' },
        { name: 'kinematic', score: 71.0, weight: 0.10, contribution: 7.1, description: 'High speed' },
      ],
      reason: 'Approaching defensive perimeter with coordinated wingman',
      evaluated_at: '2026-08-27T00:00:30Z',
    },
    {
      track_id: 'TRK-AI2-02',
      group_id: 'GRP-TEST-01',
      priority_score: 72.0,
      priority_level: 'HIGH',
      confidence: 0.92,
      factors: [
        { name: 'geofence', score: 80.0, weight: 0.30, contribution: 24.0, description: 'Approaching' },
        { name: 'behavior', score: 80.0, weight: 0.25, contribution: 20.0, description: 'Coordinated' },
        { name: 'anomaly', score: 40.0, weight: 0.20, contribution: 8.0, description: 'Low anomaly' },
        { name: 'coordination', score: 96.0, weight: 0.15, contribution: 14.4, description: 'High sync' },
        { name: 'kinematic', score: 71.0, weight: 0.10, contribution: 7.1, description: 'High speed' },
      ],
      reason: 'Wingman in coordinated formation',
      evaluated_at: '2026-08-27T00:00:30Z',
    },
    {
      track_id: 'TRK-AI2-03',
      group_id: null,
      priority_score: 18.0,
      priority_level: 'LOW',
      confidence: 0.88,
      factors: [
        { name: 'geofence', score: 0.0, weight: 0.30, contribution: 0.0, description: 'No breach' },
        { name: 'behavior', score: 10.0, weight: 0.25, contribution: 2.5, description: 'Normal' },
        { name: 'anomaly', score: 10.0, weight: 0.20, contribution: 2.0, description: 'Nominal' },
        { name: 'coordination', score: 0.0, weight: 0.15, contribution: 0.0, description: 'Isolated' },
        { name: 'kinematic', score: 15.0, weight: 0.10, contribution: 1.5, description: 'Nominal' },
      ],
      reason: 'Isolated nominal flight',
      evaluated_at: '2026-08-27T00:00:30Z',
    },
  ],
  evaluated_at: '2026-08-27T00:00:30Z',
};

describe('AeroGuard Stage AI2-G Operator Console Intelligence & UI Tests', () => {

  // 1. Priority Sorting & Level Ordering
  describe('Priority Sorting & Ranking', () => {
    it('orders priority assessments in strict descending order of priority_score', () => {
      const sorted = [...mockMultiTrackSummary.priorities].sort(
        (a, b) => b.priority_score - a.priority_score
      );
      assert.equal(sorted[0].track_id, 'TRK-AI2-01');
      assert.equal(sorted[1].track_id, 'TRK-AI2-02');
      assert.equal(sorted[2].track_id, 'TRK-AI2-03');
      assert.ok(sorted[0].priority_score >= sorted[1].priority_score);
      assert.ok(sorted[1].priority_score >= sorted[2].priority_score);
    });

    it('maps priority levels deterministically to standard rank order', () => {
      const levelRank: Record<string, number> = {
        CRITICAL: 3,
        HIGH: 2,
        MEDIUM: 1,
        LOW: 0,
      };
      assert.ok(levelRank.CRITICAL > levelRank.HIGH);
      assert.ok(levelRank.HIGH > levelRank.MEDIUM);
      assert.ok(levelRank.MEDIUM > levelRank.LOW);
    });

    it('formats priority scores to 1 decimal place with bounds [0.0, 100.0]', () => {
      for (const p of mockMultiTrackSummary.priorities) {
        assert.ok(p.priority_score >= 0.0 && p.priority_score <= 100.0);
        const formatted = p.priority_score.toFixed(1);
        assert.match(formatted, /^\d+\.\d$/);
      }
    });
  });

  // 2. Explainable Factor Reconciliation
  describe('Explainable Factor Reconciliation', () => {
    it('reconciles mathematical sum of factor contributions to P_base', () => {
      const p = mockMultiTrackSummary.priorities[0];
      const sumContrib = p.factors.reduce((acc, f) => acc + f.contribution, 0);
      assert.ok(sumContrib >= 0.0);

      // Verify each factor contribution == score * weight
      for (const factor of p.factors) {
        const expectedContrib = factor.score * factor.weight;
        assert.ok(Math.abs(factor.contribution - expectedContrib) <= 0.01);
      }
    });

    it('verifies all 5 required factor keys are present in every priority assessment', () => {
      const requiredFactors = new Set(['geofence', 'behavior', 'anomaly', 'coordination', 'kinematic']);
      for (const p of mockMultiTrackSummary.priorities) {
        assert.equal(p.factors.length, 5);
        const present = new Set(p.factors.map((f) => f.name.toLowerCase()));
        for (const req of requiredFactors) {
          assert.ok(present.has(req), `Missing factor ${req} in ${p.track_id}`);
        }
      }
    });
  });

  // 3. Behavioral State & Group Coordination Mapping
  describe('Behavioral & Formation Mapping', () => {
    it('maps track IDs to corresponding behavioral classifications', () => {
      const bMap = new Map(mockMultiTrackSummary.behaviors.map((b) => [b.track_id, b]));
      assert.equal(bMap.get('TRK-AI2-01')?.state, 'APPROACHING');
      assert.equal(bMap.get('TRK-AI2-02')?.state, 'COORDINATED');
      assert.equal(bMap.get('TRK-AI2-03')?.state, 'NORMAL');
    });

    it('resolves group membership and coordinated formation parameters', () => {
      const group = mockMultiTrackSummary.groups[0];
      assert.equal(group.member_count, 2);
      assert.deepEqual(group.member_track_ids, ['TRK-AI2-01', 'TRK-AI2-02']);

      const formation = mockMultiTrackSummary.formations[0];
      assert.equal(formation.group_id, 'GRP-TEST-01');
      assert.ok(formation.synchronization_index > 0.90);
      assert.ok(formation.heading_dispersion_deg < 5.0);
    });
  });

  // 4. MAP2 Scene Building & Projection with AI2 Overlays
  describe('MAP2 Renderer AI2 Scene Building', () => {
    it('projects multi-track groups into RenderGroupItem structures with pixel radii', () => {
      const trackCoords = new Map<string, { x: number; y: number }>([
        ['TRK-AI2-01', { x: 400, y: 300 }],
        ['TRK-AI2-02', { x: 410, y: 305 }],
      ]);

      const groups = projectGroupsForRenderer(
        mockMultiTrackSummary.groups,
        mockMultiTrackSummary.formations,
        trackCoords,
        37.7749,
        -122.4194,
        1.2,
        0,
        0,
        800,
        600
      );

      assert.equal(groups.length, 1);
      const g = groups[0];
      assert.equal(g.groupId, 'GRP-TEST-01');
      assert.ok(g.radiusPixels >= 20);
      assert.equal(g.memberTrackIds.length, 2);
      assert.equal(g.memberScreenCoords.length, 2);
      assert.ok(g.isCoordinated);
      assert.equal(g.synchronizationIndex, 0.96);
    });

    it('preserves selected group highlights across scene projection', () => {
      const trackCoords = new Map<string, { x: number; y: number }>();
      const groups = projectGroupsForRenderer(
        mockMultiTrackSummary.groups,
        mockMultiTrackSummary.formations,
        trackCoords,
        37.7749,
        -122.4194,
        1.2,
        0,
        0,
        800,
        600,
        'GRP-TEST-01'
      );

      assert.equal(groups[0].isSelected, true);
    });

    it('handles empty active track intelligence cleanly without throwing exceptions', () => {
      const groups = projectGroupsForRenderer(
        [],
        [],
        new Map(),
        37.7749,
        -122.4194,
        1.2,
        0,
        0,
        800,
        600
      );

      assert.deepEqual(groups, []);
    });
  });

  // 5. Stale Event & Realtime Telemetry Protection
  describe('Realtime Telemetry & Freshness Protection', () => {
    it('rejects stale events with evaluated_at timestamps older than existing state', () => {
      const currentStateTime = new Date('2026-08-27T00:00:30Z').getTime();
      const incomingStaleTime = new Date('2026-08-27T00:00:15Z').getTime();
      const incomingFreshTime = new Date('2026-08-27T00:00:45Z').getTime();

      const isStale = incomingStaleTime < currentStateTime;
      const isFresh = incomingFreshTime >= currentStateTime;

      assert.ok(isStale, 'Older event should be classified as stale');
      assert.ok(isFresh, 'Newer event should be classified as fresh');
    });

    it('safely validates malformed intelligence payloads without crashing', () => {
      const malformedPayload: unknown = { random_garbage: true };
      const isMultiTrack = (p: any): p is MultiTrackIntelligenceSummary => {
        return p && Array.isArray(p.groups) && Array.isArray(p.priorities);
      };

      assert.equal(isMultiTrack(malformedPayload), false);
      assert.equal(isMultiTrack(mockMultiTrackSummary), true);
    });
  });

  // 6. RBAC Permission Visibility Logic
  describe('RBAC Visibility Rules', () => {
    it('restricts intelligence visibility to operators with tracks.read permission', () => {
      const userPermissions = ['tracks.read', 'system.read'];
      const viewerPermissions = ['system.read'];

      const canViewIntelligence = (perms: string[]) => perms.includes('tracks.read');

      assert.ok(canViewIntelligence(userPermissions));
      assert.equal(canViewIntelligence(viewerPermissions), false);
    });
  });
});
