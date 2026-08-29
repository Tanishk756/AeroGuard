/**
 * AeroGuard Operator Console — Stage IM1-F Tactical Map Incident Integration Tests
 * Uses Node.js native test runner (node:test, node:assert/strict).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

// ── Pure Domain Models & Scene Types for Testing ──

export type IncidentStatus =
  | 'NEW'
  | 'ACKNOWLEDGED'
  | 'TRIAGED'
  | 'ESCALATED'
  | 'RESOLVED'
  | 'CLOSED';

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface MockIncident {
  id: string;
  incident_number: string;
  title: string;
  status: IncidentStatus;
  severity: IncidentSeverity;
  source: string;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
  originating_alert_id?: string | null;
  originating_intelligence_event_id?: string | null;
  assigned_to?: string | null;
  created_at: string;
  updated_at: string;
}

export interface MockTrack {
  id: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  state: string;
}

export interface MockTrackGroup {
  group_id: string;
  centroid_lat: number;
  centroid_lon: number;
  member_track_ids: string[];
  member_count: number;
  confidence: number;
  behavioral_state: string;
}

export interface RenderIncidentItem {
  incidentId: string;
  incidentNumber: string;
  title: string;
  severity: IncidentSeverity;
  status: IncidentStatus;
  screenX: number;
  screenY: number;
  associatedTrackId?: string | null;
  associatedGroupId?: string | null;
  isSelected: boolean;
  isHighlighted: boolean;
}

export interface HitTestResult {
  type: 'track' | 'sensor' | 'geofence' | 'group' | 'incident';
  id: string;
  screenX: number;
  screenY: number;
  distancePixels: number;
}

const BASE_PIXELS_PER_DEGREE = 2500;
const CULL_PADDING = 80;

function projectLatLon(
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

function buildTestRenderScene(options: {
  width: number;
  height: number;
  centerLat: number;
  centerLon: number;
  zoom: number;
  panOffsetX?: number;
  panOffsetY?: number;
  tracks: MockTrack[];
  groups?: MockTrackGroup[];
  incidents?: MockIncident[];
  selectedTrackId?: string | null;
  selectedGroupId?: string | null;
  selectedIncidentId?: string | null;
  layers?: { incidents?: boolean; tracks?: boolean };
}) {
  const {
    width,
    height,
    centerLat,
    centerLon,
    zoom,
    panOffsetX = 0,
    panOffsetY = 0,
    tracks,
    groups = [],
    incidents = [],
    selectedTrackId = null,
    selectedGroupId = null,
    selectedIncidentId = null,
    layers = {},
  } = options;

  // 1. Project Tracks
  const trackCoordMap = new Map<string, { x: number; y: number }>();
  const renderTracks: Array<{ id: string; screenX: number; screenY: number }> = [];

  for (const t of tracks) {
    const pos = projectLatLon(
      t.latitude,
      t.longitude,
      centerLat,
      centerLon,
      zoom,
      panOffsetX,
      panOffsetY,
      width,
      height
    );
    trackCoordMap.set(t.id, pos);
    renderTracks.push({ id: t.id, screenX: pos.x, screenY: pos.y });
  }

  // 2. Project Groups
  const groupCoordMap = new Map<string, { x: number; y: number }>();
  for (const g of groups) {
    const pos = projectLatLon(
      g.centroid_lat,
      g.centroid_lon,
      centerLat,
      centerLon,
      zoom,
      panOffsetX,
      panOffsetY,
      width,
      height
    );
    groupCoordMap.set(g.group_id, pos);
  }

  // 3. Project Incidents (IM1-F)
  const renderIncidents: RenderIncidentItem[] = [];
  if (layers.incidents !== false && incidents.length > 0) {
    const entityIncidentCounts = new Map<string, number>();

    for (const inc of incidents) {
      let screenPos: { x: number; y: number } | null = null;
      let targetEntityKey: string | null = null;

      if (inc.primary_track_id && trackCoordMap.has(inc.primary_track_id)) {
        screenPos = trackCoordMap.get(inc.primary_track_id)!;
        targetEntityKey = `trk_${inc.primary_track_id}`;
      } else if (inc.primary_group_id && groupCoordMap.has(inc.primary_group_id)) {
        screenPos = groupCoordMap.get(inc.primary_group_id)!;
        targetEntityKey = `grp_${inc.primary_group_id}`;
      }

      if (screenPos && targetEntityKey) {
        const count = entityIncidentCounts.get(targetEntityKey) || 0;
        entityIncidentCounts.set(targetEntityKey, count + 1);

        const offsetX = 16 + (count % 3) * 14;
        const offsetY = -16 - Math.floor(count / 3) * 14;

        const posX = screenPos.x + offsetX;
        const posY = screenPos.y + offsetY;

        const isSelected = inc.id === selectedIncidentId;
        const isHighlighted =
          isSelected ||
          (selectedTrackId != null && inc.primary_track_id === selectedTrackId) ||
          (selectedGroupId != null && inc.primary_group_id === selectedGroupId);

        const isVisible =
          posX >= -CULL_PADDING &&
          posX <= width + CULL_PADDING &&
          posY >= -CULL_PADDING &&
          posY <= height + CULL_PADDING;

        if (isVisible || isSelected) {
          renderIncidents.push({
            incidentId: inc.id,
            incidentNumber: inc.incident_number,
            title: inc.title,
            severity: inc.severity,
            status: inc.status,
            screenX: posX,
            screenY: posY,
            associatedTrackId: inc.primary_track_id,
            associatedGroupId: inc.primary_group_id,
            isSelected,
            isHighlighted,
          });
        }
      }
    }
  }

  return {
    tracks: renderTracks,
    incidents: renderIncidents,
    selectedIncidentId,
  };
}

function hitTestScene(
  screenX: number,
  screenY: number,
  incidents: RenderIncidentItem[],
  tracks: Array<{ id: string; screenX: number; screenY: number }>
): HitTestResult | null {
  const INCIDENT_HIT_RADIUS = 14;
  const TRACK_HIT_RADIUS = 16;
  let closestHit: HitTestResult | null = null;
  let minDistance = Infinity;

  // 1. Test Incident Markers (highest priority)
  for (const inc of incidents) {
    const dist = Math.hypot(screenX - inc.screenX, screenY - inc.screenY);
    if (dist <= INCIDENT_HIT_RADIUS && dist < minDistance) {
      minDistance = dist;
      closestHit = {
        type: 'incident',
        id: inc.incidentId,
        screenX: inc.screenX,
        screenY: inc.screenY,
        distancePixels: dist,
      };
    }
  }

  if (closestHit) return closestHit;

  // 2. Test Track Markers
  for (const t of tracks) {
    const dist = Math.hypot(screenX - t.screenX, screenY - t.screenY);
    if (dist <= TRACK_HIT_RADIUS && dist < minDistance) {
      minDistance = dist;
      closestHit = {
        type: 'track',
        id: t.id,
        screenX: t.screenX,
        screenY: t.screenY,
        distancePixels: dist,
      };
    }
  }

  return closestHit;
}

// ── Test Suites ──

describe('AeroGuard Stage IM1-F Tactical Map Incident Integration Tests', () => {
  const centerLat = 37.7749;
  const centerLon = -122.4194;
  const viewportWidth = 800;
  const viewportHeight = 600;

  const mockTrack1: MockTrack = {
    id: 'trk-alpha-01',
    latitude: 37.7749,
    longitude: -122.4194,
    altitude: 120,
    velocity: 25,
    heading: 90,
    state: 'ACTIVE',
  };

  const mockTrack2: MockTrack = {
    id: 'trk-bravo-02',
    latitude: 37.7849,
    longitude: -122.4094,
    altitude: 150,
    velocity: 30,
    heading: 180,
    state: 'ACTIVE',
  };

  const mockGroup1: MockTrackGroup = {
    group_id: 'grp-swarm-01',
    centroid_lat: 37.7750,
    centroid_lon: -122.4190,
    member_track_ids: ['trk-alpha-01', 'trk-bravo-02'],
    member_count: 2,
    confidence: 0.95,
    behavioral_state: 'SWARM_CONVERGENCE',
  };

  // 1. Incident -> Primary Track Projection
  it('projects incident marker near primary track position', () => {
    const inc: MockIncident = {
      id: 'inc-001',
      incident_number: 'INC-2026-0001',
      title: 'Airspace Incursion Alpha',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:05:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    assert.equal(scene.incidents.length, 1);
    const item = scene.incidents[0];
    assert.equal(item.incidentId, 'inc-001');
    assert.equal(item.incidentNumber, 'INC-2026-0001');
    assert.equal(item.associatedTrackId, 'trk-alpha-01');
    assert.equal(item.severity, 'HIGH');
    assert.equal(item.status, 'TRIAGED');

    // Expected screen position: track is at (400, 300), first incident offset is (16, -16)
    assert.equal(item.screenX, 400 + 16);
    assert.equal(item.screenY, 300 - 16);
  });

  // 2. Incident -> Primary Group Centroid Projection
  it('projects incident marker near primary group centroid when no primary track', () => {
    const inc: MockIncident = {
      id: 'inc-002',
      incident_number: 'INC-2026-0002',
      title: 'Coordinated Swarm Incursion',
      status: 'ESCALATED',
      severity: 'CRITICAL',
      source: 'AI_SWARM',
      primary_group_id: 'grp-swarm-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:05:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1, mockTrack2],
      groups: [mockGroup1],
      incidents: [inc],
    });

    assert.equal(scene.incidents.length, 1);
    const item = scene.incidents[0];
    assert.equal(item.incidentId, 'inc-002');
    assert.equal(item.associatedGroupId, 'grp-swarm-01');
    assert.equal(item.associatedTrackId, undefined);
  });

  // 3. Uncorrelated Incident Has No Map Position
  it('does not project uncorrelated incidents with neither primary track nor group', () => {
    const inc: MockIncident = {
      id: 'inc-003',
      incident_number: 'INC-2026-0003',
      title: 'System Security Audit Warning',
      status: 'NEW',
      severity: 'LOW',
      source: 'SYSTEM',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    assert.equal(scene.incidents.length, 0);
  });

  // 4. Deterministic Scene Construction
  it('constructs identical scene projections deterministically', () => {
    const inc: MockIncident = {
      id: 'inc-004',
      incident_number: 'INC-2026-0004',
      title: 'Deterministic Incursion',
      status: 'ACKNOWLEDGED',
      severity: 'MEDIUM',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const sceneA = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    const sceneB = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    assert.deepEqual(sceneA.incidents, sceneB.incidents);
  });

  // 5. Incident Selection
  it('marks isSelected true when incident ID matches selectedIncidentId', () => {
    const inc: MockIncident = {
      id: 'inc-005',
      incident_number: 'INC-2026-0005',
      title: 'Selected Incident',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
      selectedIncidentId: 'inc-005',
    });

    assert.equal(scene.incidents[0].isSelected, true);
    assert.equal(scene.incidents[0].isHighlighted, true);
  });

  // 6. Selected Incident Highlight
  it('sets isHighlighted true when selectedIncidentId matches', () => {
    const inc: MockIncident = {
      id: 'inc-006',
      incident_number: 'INC-2026-0006',
      title: 'Highlighted Incident',
      status: 'NEW',
      severity: 'MEDIUM',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
      selectedIncidentId: 'inc-006',
    });

    assert.equal(scene.incidents[0].isHighlighted, true);
  });

  // 7. Track Correlation Highlight
  it('sets isHighlighted true when correlated track is selected', () => {
    const inc: MockIncident = {
      id: 'inc-007',
      incident_number: 'INC-2026-0007',
      title: 'Track Correlated Incident',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
      selectedTrackId: 'trk-alpha-01',
    });

    assert.equal(scene.incidents[0].isSelected, false);
    assert.equal(scene.incidents[0].isHighlighted, true);
  });

  // 8. Group Correlation Highlight
  it('sets isHighlighted true when correlated group is selected', () => {
    const inc: MockIncident = {
      id: 'inc-008',
      incident_number: 'INC-2026-0008',
      title: 'Group Correlated Incident',
      status: 'ESCALATED',
      severity: 'CRITICAL',
      source: 'AI_SWARM',
      primary_group_id: 'grp-swarm-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      groups: [mockGroup1],
      incidents: [inc],
      selectedGroupId: 'grp-swarm-01',
    });

    assert.equal(scene.incidents[0].isSelected, false);
    assert.equal(scene.incidents[0].isHighlighted, true);
  });

  // 9. Multiple Incidents on Same Track
  it('staggers multiple incidents on the same track with deterministic offsets', () => {
    const inc1: MockIncident = {
      id: 'inc-009a',
      incident_number: 'INC-2026-0009A',
      title: 'Incursion Alpha',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };
    const inc2: MockIncident = {
      id: 'inc-009b',
      incident_number: 'INC-2026-0009B',
      title: 'Velocity Anomaly Alpha',
      status: 'NEW',
      severity: 'MEDIUM',
      source: 'AI_ANOMALY',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:01:00Z',
      updated_at: '2026-08-29T10:01:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc1, inc2],
    });

    assert.equal(scene.incidents.length, 2);
    const item1 = scene.incidents[0];
    const item2 = scene.incidents[1];

    // Assert distinct coordinates
    assert.notEqual(item1.screenX, item2.screenX);
    assert.equal(item1.screenX, 400 + 16);
    assert.equal(item2.screenX, 400 + 16 + 14);
  });

  // 10. Multiple Incidents on Same Group
  it('staggers multiple incidents on the same group with deterministic offsets', () => {
    const inc1: MockIncident = {
      id: 'inc-010a',
      incident_number: 'INC-2026-010A',
      title: 'Swarm Warning 1',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'AI_SWARM',
      primary_group_id: 'grp-swarm-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };
    const inc2: MockIncident = {
      id: 'inc-010b',
      incident_number: 'INC-2026-010B',
      title: 'Swarm Warning 2',
      status: 'ESCALATED',
      severity: 'CRITICAL',
      source: 'AI_SWARM',
      primary_group_id: 'grp-swarm-01',
      created_at: '2026-08-29T10:01:00Z',
      updated_at: '2026-08-29T10:01:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      groups: [mockGroup1],
      incidents: [inc1, inc2],
    });

    assert.equal(scene.incidents.length, 2);
    assert.notEqual(scene.incidents[0].screenX, scene.incidents[1].screenX);
  });

  // 11. Closed Incident Rendering
  it('preserves CLOSED status on rendered item', () => {
    const inc: MockIncident = {
      id: 'inc-011',
      incident_number: 'INC-2026-0011',
      title: 'Resolved Incursion',
      status: 'CLOSED',
      severity: 'LOW',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T08:00:00Z',
      updated_at: '2026-08-29T09:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    assert.equal(scene.incidents[0].status, 'CLOSED');
  });

  // 12. Severity Mapping
  it('maps all 4 standard severity levels onto render items', () => {
    const severities: IncidentSeverity[] = ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL'];
    for (let i = 0; i < severities.length; i++) {
      const inc: MockIncident = {
        id: `inc-sev-${i}`,
        incident_number: `INC-SEV-${i}`,
        title: `Severity Test ${severities[i]}`,
        status: 'NEW',
        severity: severities[i],
        source: 'ALERT',
        primary_track_id: 'trk-alpha-01',
        created_at: '2026-08-29T10:00:00Z',
        updated_at: '2026-08-29T10:00:00Z',
      };

      const scene = buildTestRenderScene({
        width: viewportWidth,
        height: viewportHeight,
        centerLat,
        centerLon,
        zoom: 1,
        tracks: [mockTrack1],
        incidents: [inc],
      });

      assert.equal(scene.incidents[0].severity, severities[i]);
    }
  });

  // 13. Status Mapping
  it('maps all 6 standard lifecycle statuses onto render items', () => {
    const statuses: IncidentStatus[] = ['NEW', 'ACKNOWLEDGED', 'TRIAGED', 'ESCALATED', 'RESOLVED', 'CLOSED'];
    for (let i = 0; i < statuses.length; i++) {
      const inc: MockIncident = {
        id: `inc-stat-${i}`,
        incident_number: `INC-STAT-${i}`,
        title: `Status Test ${statuses[i]}`,
        status: statuses[i],
        severity: 'MEDIUM',
        source: 'ALERT',
        primary_track_id: 'trk-alpha-01',
        created_at: '2026-08-29T10:00:00Z',
        updated_at: '2026-08-29T10:00:00Z',
      };

      const scene = buildTestRenderScene({
        width: viewportWidth,
        height: viewportHeight,
        centerLat,
        centerLon,
        zoom: 1,
        tracks: [mockTrack1],
        incidents: [inc],
      });

      assert.equal(scene.incidents[0].status, statuses[i]);
    }
  });

  // 14. Incident Hit Testing
  it('detects hit test click within 14px of incident marker', () => {
    const inc: MockIncident = {
      id: 'inc-hit-01',
      incident_number: 'INC-2026-HIT1',
      title: 'Hit Target',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    const incItem = scene.incidents[0];
    const hit = hitTestScene(incItem.screenX + 3, incItem.screenY - 2, scene.incidents, scene.tracks);

    assert.ok(hit);
    assert.equal(hit.type, 'incident');
    assert.equal(hit.id, 'inc-hit-01');
  });

  // 15. Incident Hit Testing Priority Over Track
  it('prioritizes incident hit test when clicking directly on incident badge', () => {
    const inc: MockIncident = {
      id: 'inc-prio-01',
      incident_number: 'INC-2026-PRIO',
      title: 'Priority Target',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    const incItem = scene.incidents[0];
    const hit = hitTestScene(incItem.screenX, incItem.screenY, scene.incidents, scene.tracks);

    assert.ok(hit);
    assert.equal(hit.type, 'incident');
    assert.equal(hit.id, 'inc-prio-01');
  });

  // 16. Incident Layer Visibility Toggle
  it('omits incidents from render scene when incidents layer is false', () => {
    const inc: MockIncident = {
      id: 'inc-layer-01',
      incident_number: 'INC-2026-LAYER',
      title: 'Layer Hidden Target',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
      layers: { incidents: false },
    });

    assert.equal(scene.incidents.length, 0);
  });

  // 17. Offscreen Culling
  it('culls unselected incidents that are far outside the viewport', () => {
    const farTrack: MockTrack = {
      id: 'trk-far-01',
      latitude: 50.0, // Far from 37.7749
      longitude: 0.0,
      state: 'ACTIVE',
    };

    const inc: MockIncident = {
      id: 'inc-far-01',
      incident_number: 'INC-2026-FAR',
      title: 'Far Target',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-far-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [farTrack],
      incidents: [inc],
      selectedIncidentId: null,
    });

    assert.equal(scene.incidents.length, 0);
  });

  // 18. Selected Offscreen Incident Preservation
  it('preserves offscreen incidents when explicitly selected', () => {
    const farTrack: MockTrack = {
      id: 'trk-far-02',
      latitude: 50.0,
      longitude: 0.0,
      state: 'ACTIVE',
    };

    const inc: MockIncident = {
      id: 'inc-far-02',
      incident_number: 'INC-2026-FAR2',
      title: 'Far Selected Target',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-far-02',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [farTrack],
      incidents: [inc],
      selectedIncidentId: 'inc-far-02',
    });

    assert.equal(scene.incidents.length, 1);
    assert.equal(scene.incidents[0].isSelected, true);
  });

  // 19. Realtime Dynamic Scene Insertion
  it('dynamically inserts new incident into scene upon realtime incident.created', () => {
    const list: MockIncident[] = [];
    const sceneBefore = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: list,
    });
    assert.equal(sceneBefore.incidents.length, 0);

    // Simulate incident.created event
    list.push({
      id: 'inc-rt-01',
      incident_number: 'INC-RT-01',
      title: 'Realtime Incident',
      status: 'NEW',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    });

    const sceneAfter = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: list,
    });
    assert.equal(sceneAfter.incidents.length, 1);
    assert.equal(sceneAfter.incidents[0].incidentId, 'inc-rt-01');
  });

  // 20. Realtime Lifecycle Update
  it('updates incident status in scene upon status escalation event', () => {
    const list: MockIncident[] = [
      {
        id: 'inc-rt-02',
        incident_number: 'INC-RT-02',
        title: 'Escalating Incident',
        status: 'NEW',
        severity: 'MEDIUM',
        source: 'ALERT',
        primary_track_id: 'trk-alpha-01',
        created_at: '2026-08-29T10:00:00Z',
        updated_at: '2026-08-29T10:00:00Z',
      },
    ];

    const scene1 = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: list,
    });
    assert.equal(scene1.incidents[0].status, 'NEW');

    // Mutate status to ESCALATED
    list[0].status = 'ESCALATED';
    list[0].severity = 'CRITICAL';

    const scene2 = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: list,
    });
    assert.equal(scene2.incidents[0].status, 'ESCALATED');
    assert.equal(scene2.incidents[0].severity, 'CRITICAL');
  });

  // 21. Defensive Non-Kinetic Safety Invariant
  it('validates strictly defensive situational-awareness invariants (no targeting/kinetic fields)', () => {
    const inc: MockIncident = {
      id: 'inc-safe-01',
      incident_number: 'INC-SAFE-01',
      title: 'Defensive Observation',
      status: 'TRIAGED',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'trk-alpha-01',
      created_at: '2026-08-29T10:00:00Z',
      updated_at: '2026-08-29T10:00:00Z',
    };

    const scene = buildTestRenderScene({
      width: viewportWidth,
      height: viewportHeight,
      centerLat,
      centerLon,
      zoom: 1,
      tracks: [mockTrack1],
      incidents: [inc],
    });

    const item = scene.incidents[0] as any;
    // Verify prohibited offensive / kinetic fields DO NOT exist
    assert.equal(item.weaponSolution, undefined);
    assert.equal(item.engagementGeometry, undefined);
    assert.equal(item.fireControl, undefined);
    assert.equal(item.jammingCommand, undefined);
    assert.equal(item.killProbability, undefined);
    assert.equal(item.targetDesignation, undefined);
  });

  // 22. High-Density Scene Construction Benchmarks
  describe('High-Density Incident Performance Benchmarks', () => {
    function generateHighDensityTracks(count: number): MockTrack[] {
      const tracks: MockTrack[] = [];
      for (let i = 0; i < count; i++) {
        const row = Math.floor(i / 10);
        const col = i % 10;
        tracks.push({
          id: `trk-hd-${i}`,
          latitude: centerLat + (row - 5) * 0.01,
          longitude: centerLon + (col - 5) * 0.01,
          altitude: 100 + (i % 20) * 10,
          velocity: 20 + (i % 15),
          heading: (i * 36) % 360,
          state: 'ACTIVE',
        });
      }
      return tracks;
    }

    function generateHighDensityIncidents(count: number, trackCount: number): MockIncident[] {
      const items: MockIncident[] = [];
      for (let i = 0; i < count; i++) {
        const targetTrackId = `trk-hd-${i % trackCount}`;
        items.push({
          id: `inc-hd-${i}`,
          incident_number: `INC-2026-${String(i).padStart(4, '0')}`,
          title: `Automated Test Incursion ${i}`,
          status: i % 6 === 0 ? 'CLOSED' : i % 5 === 0 ? 'RESOLVED' : i % 3 === 0 ? 'ESCALATED' : 'TRIAGED',
          severity: i % 4 === 0 ? 'CRITICAL' : i % 3 === 0 ? 'HIGH' : i % 2 === 0 ? 'MEDIUM' : 'LOW',
          source: 'ALERT',
          primary_track_id: targetTrackId,
          created_at: '2026-08-29T10:00:00Z',
          updated_at: '2026-08-29T10:00:00Z',
        });
      }
      return items;
    }

    const testTracks = generateHighDensityTracks(100);

    it('processes 100 correlated incidents within 5ms', () => {
      const items = generateHighDensityIncidents(100, testTracks.length);
      const start = performance.now();
      const scene = buildTestRenderScene({
        width: viewportWidth,
        height: viewportHeight,
        centerLat,
        centerLon,
        zoom: 1,
        tracks: testTracks,
        incidents: items,
      });
      const elapsed = performance.now() - start;

      assert.equal(scene.incidents.length, 100);
      assert.ok(elapsed < 5, `100 incidents took ${elapsed.toFixed(3)}ms (expected < 5ms)`);
    });

    it('processes 500 correlated incidents within 15ms', () => {
      const items = generateHighDensityIncidents(500, testTracks.length);
      const start = performance.now();
      const scene = buildTestRenderScene({
        width: viewportWidth,
        height: viewportHeight,
        centerLat,
        centerLon,
        zoom: 1,
        tracks: testTracks,
        incidents: items,
      });
      const elapsed = performance.now() - start;

      assert.equal(scene.incidents.length, 500);
      assert.ok(elapsed < 15, `500 incidents took ${elapsed.toFixed(3)}ms (expected < 15ms)`);
    });

    it('processes 1,000 correlated incidents within 30ms', () => {
      const items = generateHighDensityIncidents(1000, testTracks.length);
      const start = performance.now();
      const scene = buildTestRenderScene({
        width: viewportWidth,
        height: viewportHeight,
        centerLat,
        centerLon,
        zoom: 1,
        tracks: testTracks,
        incidents: items,
      });
      const elapsed = performance.now() - start;

      assert.equal(scene.incidents.length, 1000);
      assert.ok(elapsed < 30, `1,000 incidents took ${elapsed.toFixed(3)}ms (expected < 30ms)`);
    });

    it('processes 5,000 correlated incidents within 100ms', () => {
      const items = generateHighDensityIncidents(5000, testTracks.length);
      const start = performance.now();
      const scene = buildTestRenderScene({
        width: viewportWidth,
        height: viewportHeight,
        centerLat,
        centerLon,
        zoom: 1,
        tracks: testTracks,
        incidents: items,
      });
      const elapsed = performance.now() - start;

      assert.equal(scene.incidents.length, 5000);
      assert.ok(elapsed < 100, `5,000 incidents took ${elapsed.toFixed(3)}ms (expected < 100ms)`);
    });
  });
});
