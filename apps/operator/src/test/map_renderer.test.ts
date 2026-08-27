import assert from 'node:assert';
import test, { describe, it } from 'node:test';

// ── Pure Domain Types & Logic for MAP2 Tactical Renderer Tests ──

interface RenderViewport {
  centerLat: number;
  centerLon: number;
  zoom: number;
  panOffsetX: number;
  panOffsetY: number;
  width: number;
  height: number;
  devicePixelRatio: number;
}

interface RenderTrackItem {
  id: string;
  latitude: number;
  longitude: number;
  screenX: number;
  screenY: number;
  altitude?: number | null;
  velocity?: number | null;
  heading?: number | null;
  state: string;
  classification?: string;
  confidence: number;
  anomalyScore?: number | null;
  anomalyLevel?: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' | null;
  isSelected: boolean;
  isThreatElevated: boolean;
}

interface RenderTrackTrail {
  trackId: string;
  points: Array<{ screenX: number; screenY: number; alpha: number }>;
  isSelected: boolean;
}

interface RenderGeofenceItem {
  id: string;
  name: string;
  geometryType: 'BBOX' | 'POLYGON' | 'CIRCLE';
  screenCoordinates: Array<{ x: number; y: number }>;
  radiusPixels?: number;
  status: 'ENABLED' | 'DISABLED' | 'SELECTED' | 'WARNING';
  isSelected: boolean;
}

interface RenderSensorItem {
  id: string;
  name: string;
  screenX: number;
  screenY: number;
  rangeRadiusPixels?: number | null;
  status: string;
  isSelected: boolean;
}

interface HitTestResult {
  type: 'track' | 'sensor' | 'geofence';
  id: string;
  screenX: number;
  screenY: number;
  distancePixels: number;
}

const BASE_PIXELS_PER_DEGREE = 2500;
const EARTH_RADIUS_METERS = 6371000;

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

function isPointInPolygon(
  x: number,
  y: number,
  polygon: Array<{ x: number; y: number }>
): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;

    const intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}

function hitTestScene(
  screenX: number,
  screenY: number,
  tracks: RenderTrackItem[],
  sensors: RenderSensorItem[],
  geofences: RenderGeofenceItem[]
): HitTestResult | null {
  const TRACK_HIT_RADIUS = 16;
  const SENSOR_HIT_RADIUS = 14;
  let closestHit: HitTestResult | null = null;
  let minDistance = Infinity;

  // 1. Tracks
  for (const t of tracks) {
    const dist = Math.hypot(screenX - t.screenX, screenY - t.screenY);
    if (dist <= TRACK_HIT_RADIUS && dist < minDistance) {
      minDistance = dist;
      closestHit = { type: 'track', id: t.id, screenX: t.screenX, screenY: t.screenY, distancePixels: dist };
    }
  }
  if (closestHit) return closestHit;

  // 2. Sensors
  for (const s of sensors) {
    const dist = Math.hypot(screenX - s.screenX, screenY - s.screenY);
    if (dist <= SENSOR_HIT_RADIUS && dist < minDistance) {
      minDistance = dist;
      closestHit = { type: 'sensor', id: s.id, screenX: s.screenX, screenY: s.screenY, distancePixels: dist };
    }
  }
  if (closestHit) return closestHit;

  // 3. Geofences
  for (const g of geofences) {
    if (g.geometryType === 'CIRCLE' && g.radiusPixels && g.screenCoordinates.length > 0) {
      const center = g.screenCoordinates[0];
      const dist = Math.hypot(screenX - center.x, screenY - center.y);
      if (dist <= g.radiusPixels) {
        return { type: 'geofence', id: g.id, screenX: center.x, screenY: center.y, distancePixels: dist };
      }
    } else if (g.screenCoordinates.length >= 3) {
      if (isPointInPolygon(screenX, screenY, g.screenCoordinates)) {
        return { type: 'geofence', id: g.id, screenX, screenY, distancePixels: 0 };
      }
    }
  }

  return null;
}

describe('AeroGuard Stage MAP2 Tactical Visualization & Renderer Unit Tests', () => {
  describe('Coordinate Projection & Viewport Math', () => {
    it('projects the center lat/lon directly to viewport center', () => {
      const centerLat = 37.7749;
      const centerLon = -122.4194;
      const p = projectLatLon(centerLat, centerLon, centerLat, centerLon, 1.0, 0, 0, 800, 600);
      assert.strictEqual(p.x, 400);
      assert.strictEqual(p.y, 300);
    });

    it('scales coordinate offsets with zoom and cosine latitude correction', () => {
      const centerLat = 37.7749;
      const centerLon = -122.4194;
      const pZoom1 = projectLatLon(centerLat + 0.01, centerLon, centerLat, centerLon, 1.0, 0, 0, 800, 600);
      const pZoom2 = projectLatLon(centerLat + 0.01, centerLon, centerLat, centerLon, 2.0, 0, 0, 800, 600);

      // Y offset from center should double with 2x zoom
      const dy1 = 300 - pZoom1.y;
      const dy2 = 300 - pZoom2.y;
      assert.strictEqual(Math.round(dy2), Math.round(dy1 * 2));
    });
  });

  describe('Point-in-Polygon & Spatial Hit Testing', () => {
    const polygon = [
      { x: 100, y: 100 },
      { x: 200, y: 100 },
      { x: 200, y: 200 },
      { x: 100, y: 200 },
    ];

    it('identifies points inside a polygon', () => {
      assert.strictEqual(isPointInPolygon(150, 150, polygon), true);
    });

    it('rejects points outside a polygon', () => {
      assert.strictEqual(isPointInPolygon(50, 50, polygon), false);
      assert.strictEqual(isPointInPolygon(250, 150, polygon), false);
    });

    it('prioritizes track hits over background geofence hits', () => {
      const tracks: RenderTrackItem[] = [
        {
          id: 'TRK-001',
          latitude: 37.7749,
          longitude: -122.4194,
          screenX: 150,
          screenY: 150,
          state: 'ACTIVE',
          confidence: 0.95,
          isSelected: false,
          isThreatElevated: false,
        },
      ];
      const geofences: RenderGeofenceItem[] = [
        {
          id: 'GEO-001',
          name: 'Sector Alpha',
          geometryType: 'POLYGON',
          screenCoordinates: polygon,
          status: 'ENABLED',
          isSelected: false,
        },
      ];

      const hit = hitTestScene(152, 151, tracks, [], geofences);
      assert.ok(hit !== null);
      assert.strictEqual(hit.type, 'track');
      assert.strictEqual(hit.id, 'TRK-001');
    });

    it('hits geofence when clicking within boundary away from tracks', () => {
      const tracks: RenderTrackItem[] = [
        {
          id: 'TRK-001',
          latitude: 37.7749,
          longitude: -122.4194,
          screenX: 500,
          screenY: 500,
          state: 'ACTIVE',
          confidence: 0.95,
          isSelected: false,
          isThreatElevated: false,
        },
      ];
      const geofences: RenderGeofenceItem[] = [
        {
          id: 'GEO-001',
          name: 'Sector Alpha',
          geometryType: 'POLYGON',
          screenCoordinates: polygon,
          status: 'ENABLED',
          isSelected: false,
        },
      ];

      const hit = hitTestScene(150, 150, tracks, [], geofences);
      assert.ok(hit !== null);
      assert.strictEqual(hit.type, 'geofence');
      assert.strictEqual(hit.id, 'GEO-001');
    });
  });

  describe('Bounded Trail History Decay', () => {
    it('bounds trail length to configured maximum', () => {
      const rawPoints = Array.from({ length: 50 }, (_, i) => ({
        latitude: 37.77 + i * 0.001,
        longitude: -122.41 + i * 0.001,
      }));
      const maxLen = 20;
      const bounded = rawPoints.slice(-maxLen);
      assert.strictEqual(bounded.length, 20);
      assert.strictEqual(bounded[bounded.length - 1].latitude, rawPoints[49].latitude);
    });

    it('calculates increasing opacity for recent trail nodes', () => {
      const count = 10;
      const alphas = Array.from({ length: count }, (_, i) => 0.3 + (0.7 * (i + 1)) / count);
      assert.strictEqual(alphas[0] < alphas[count - 1], true);
      assert.strictEqual(Math.round(alphas[count - 1] * 10) / 10, 1.0);
    });
  });

  describe('High-Density Track Culling & Performance', () => {
    it('culls off-screen tracks outside viewport padding', () => {
      const width = 800;
      const height = 600;
      const CULL_PADDING = 60;

      // 1000 tracks distributed across wide coordinate space
      const rawTracks = Array.from({ length: 1000 }, (_, i) => ({
        id: `TRK-${i}`,
        screenX: (i % 50) * 40 - 500, // Range: -500 to +1500
        screenY: Math.floor(i / 50) * 40 - 200, // Range: -200 to +600
      }));

      const visibleTracks = rawTracks.filter(
        (t) =>
          t.screenX >= -CULL_PADDING &&
          t.screenX <= width + CULL_PADDING &&
          t.screenY >= -CULL_PADDING &&
          t.screenY <= height + CULL_PADDING
      );

      assert.ok(visibleTracks.length < rawTracks.length, 'Off-screen tracks must be culled');
      assert.ok(visibleTracks.length > 0, 'Visible tracks must be retained');
    });

    it('throttles labels when track density exceeds threshold', () => {
      const isDense = (count: number) => count > 80;
      const shouldDrawLabel = (
        isDenseScene: boolean,
        showLabels: boolean,
        isSelected: boolean,
        isThreat: boolean
      ) => {
        return (showLabels && (!isDenseScene || isSelected || isThreat)) || isSelected;
      };

      // In sparse scene: show labels for all
      assert.strictEqual(shouldDrawLabel(isDense(30), true, false, false), true);

      // In dense scene: hide labels for nominal unselected track
      assert.strictEqual(shouldDrawLabel(isDense(250), true, false, false), false);

      // In dense scene: always show labels for selected track or elevated threat
      assert.strictEqual(shouldDrawLabel(isDense(250), true, true, false), true);
      assert.strictEqual(shouldDrawLabel(isDense(250), true, false, true), true);
    });
  });

  describe('Capability Detection & Fallback Policy', () => {
    const resolveRenderer = (hasWebGPU: boolean, hasCanvas: boolean): 'WEBGPU' | 'CANVAS' | 'LEGACY' => {
      if (hasWebGPU) return 'WEBGPU';
      if (hasCanvas) return 'CANVAS';
      return 'LEGACY';
    };

    it('selects WEBGPU when hardware WebGPU is available', () => {
      assert.strictEqual(resolveRenderer(true, true), 'WEBGPU');
    });

    it('falls back to CANVAS when WebGPU is unavailable', () => {
      assert.strictEqual(resolveRenderer(false, true), 'CANVAS');
    });

    it('falls back to LEGACY when canvas is completely unavailable', () => {
      assert.strictEqual(resolveRenderer(false, false), 'LEGACY');
    });
  });
});
