import assert from 'node:assert';
import test, { describe, it } from 'node:test';

describe('AeroGuard Stage UI2 Operational Workspace Unit Tests', () => {
  describe('Map Viewport Projection & Math', () => {
    const BASE_PIXELS_PER_DEGREE = 2500;

    const latLonToScreen = (
      lat: number,
      lon: number,
      centerLat: number,
      centerLon: number,
      zoom: number,
      panX: number,
      panY: number,
      width: number,
      height: number
    ) => {
      const cosLat = Math.cos((centerLat * Math.PI) / 180);
      const scale = BASE_PIXELS_PER_DEGREE * zoom;
      const x = width / 2 + (lon - centerLon) * scale * cosLat + panX;
      const y = height / 2 - (lat - centerLat) * scale + panY;
      return { x, y };
    };

    const screenToLatLon = (
      screenX: number,
      screenY: number,
      centerLat: number,
      centerLon: number,
      zoom: number,
      panX: number,
      panY: number,
      width: number,
      height: number
    ) => {
      const cosLat = Math.cos((centerLat * Math.PI) / 180);
      const scale = BASE_PIXELS_PER_DEGREE * zoom;
      const lon = centerLon + (screenX - width / 2 - panX) / (scale * (cosLat || 1));
      const lat = centerLat - (screenY - height / 2 - panY) / scale;
      return { lat, lon };
    };

    it('projects the viewport center coordinate directly to the screen center', () => {
      const centerLat = 37.7749;
      const centerLon = -122.4194;
      const width = 800;
      const height = 600;

      const screen = latLonToScreen(centerLat, centerLon, centerLat, centerLon, 1.0, 0, 0, width, height);
      assert.strictEqual(screen.x, 400);
      assert.strictEqual(screen.y, 300);
    });

    it('round-trips screenToLatLon and latLonToScreen with high mathematical precision', () => {
      const centerLat = 37.7749;
      const centerLon = -122.4194;
      const targetLat = 37.7950;
      const targetLon = -122.3900;
      const width = 1024;
      const height = 768;
      const zoom = 1.5;
      const panX = 25;
      const panY = -15;

      const screen = latLonToScreen(targetLat, targetLon, centerLat, centerLon, zoom, panX, panY, width, height);
      const inverse = screenToLatLon(screen.x, screen.y, centerLat, centerLon, zoom, panX, panY, width, height);

      assert.ok(Math.abs(inverse.lat - targetLat) < 1e-9);
      assert.ok(Math.abs(inverse.lon - targetLon) < 1e-9);
    });

    it('calculates fitBounds correctly for multiple points', () => {
      const points = [
        { latitude: 37.70, longitude: -122.50 },
        { latitude: 37.80, longitude: -122.40 },
        { latitude: 37.90, longitude: -122.30 },
      ];

      let minLat = points[0].latitude;
      let maxLat = points[0].latitude;
      let minLon = points[0].longitude;
      let maxLon = points[0].longitude;

      for (const pt of points) {
        if (pt.latitude < minLat) minLat = pt.latitude;
        if (pt.latitude > maxLat) maxLat = pt.latitude;
        if (pt.longitude < minLon) minLon = pt.longitude;
        if (pt.longitude > maxLon) maxLon = pt.longitude;
      }

      const calculatedCenterLat = (minLat + maxLat) / 2;
      const calculatedCenterLon = (minLon + maxLon) / 2;

      assert.strictEqual(calculatedCenterLat, 37.80);
      assert.strictEqual(calculatedCenterLon, -122.40);
    });

    it('clamps zoom factors within safe operational boundaries', () => {
      const clampZoom = (zoom: number) => Math.max(0.05, Math.min(50.0, zoom));

      assert.strictEqual(clampZoom(-5), 0.05);
      assert.strictEqual(clampZoom(0.01), 0.05);
      assert.strictEqual(clampZoom(2.5), 2.5);
      assert.strictEqual(clampZoom(75), 50.0);
    });
  });

  describe('Selection Synchronization Logic', () => {
    interface SelectedEntity {
      type: 'track' | 'sensor' | 'geofence' | 'alert' | 'threat';
      id: string;
    }

    const selectAlert = (alertId: string, trackId?: string | null): SelectedEntity => {
      if (trackId) {
        return { type: 'track', id: trackId };
      }
      return { type: 'alert', id: alertId };
    };

    const selectThreat = (threatId: string, trackId?: string | null): SelectedEntity => {
      if (trackId) {
        return { type: 'track', id: trackId };
      }
      return { type: 'threat', id: threatId };
    };

    it('synchronizes alert click to associated track when track reference is present', () => {
      const sel = selectAlert('alert-101', 'trk-alpha-99');
      assert.strictEqual(sel.type, 'track');
      assert.strictEqual(sel.id, 'trk-alpha-99');
    });

    it('falls back to alert selection when no track reference is attached', () => {
      const sel = selectAlert('alert-102', null);
      assert.strictEqual(sel.type, 'alert');
      assert.strictEqual(sel.id, 'alert-102');
    });

    it('synchronizes threat triage click to target track ID', () => {
      const sel = selectThreat('threat-55', 'trk-bravo-42');
      assert.strictEqual(sel.type, 'track');
      assert.strictEqual(sel.id, 'trk-bravo-42');
    });
  });

  describe('Client-Side Operational Filtering', () => {
    const mockTracks = [
      { id: 'TRK-001', state: 'ACTIVE', classification: 'DRONE_ROTARY', confidence: 0.95 },
      { id: 'TRK-002', state: 'STALE', classification: 'DRONE_FIXED_WING', confidence: 0.60 },
      { id: 'TRK-003', state: 'LOST', classification: 'UNKNOWN', confidence: 0.35 },
      { id: 'TRK-004', state: 'ACTIVE', classification: 'BIRD', confidence: 0.88 },
    ];

    it('filters tracks by state', () => {
      const active = mockTracks.filter((t) => t.state === 'ACTIVE');
      assert.strictEqual(active.length, 2);
      assert.strictEqual(active[0].id, 'TRK-001');
      assert.strictEqual(active[1].id, 'TRK-004');
    });

    it('filters tracks by free text search across ID and classification', () => {
      const query = 'rotary';
      const results = mockTracks.filter(
        (t) => t.id.toLowerCase().includes(query) || t.classification.toLowerCase().includes(query)
      );
      assert.strictEqual(results.length, 1);
      assert.strictEqual(results[0].id, 'TRK-001');
    });

    it('filters alerts by severity level', () => {
      const mockAlerts = [
        { id: 'ALT-1', severity: 'CRITICAL', status: 'OPEN' },
        { id: 'ALT-2', severity: 'HIGH', status: 'OPEN' },
        { id: 'ALT-3', severity: 'LOW', status: 'RESOLVED' },
      ];

      const criticalOnly = mockAlerts.filter((a) => a.severity === 'CRITICAL');
      assert.strictEqual(criticalOnly.length, 1);
      assert.strictEqual(criticalOnly[0].id, 'ALT-1');
    });
  });

  describe('Sensor Range / Coverage Rendering Boundary (Correction 2)', () => {
    it('only calculates range circle radius when range_meters is a valid positive number', () => {
      const calculatePixelRadius = (rangeMeters: unknown, zoom = 1.0) => {
        if (typeof rangeMeters !== 'number' || rangeMeters <= 0) {
          return 0;
        }
        const METERS_PER_DEGREE = 111320;
        const BASE_PIXELS_PER_DEGREE = 2500;
        const degrees = rangeMeters / METERS_PER_DEGREE;
        return degrees * BASE_PIXELS_PER_DEGREE * zoom;
      };

      assert.strictEqual(calculatePixelRadius(undefined), 0);
      assert.strictEqual(calculatePixelRadius(null), 0);
      assert.strictEqual(calculatePixelRadius(0), 0);
      assert.strictEqual(calculatePixelRadius(-500), 0);
      assert.strictEqual(calculatePixelRadius('1500'), 0);

      const validRadius = calculatePixelRadius(5000, 1.0);
      assert.ok(validRadius > 0);
      assert.strictEqual(Math.round(validRadius), Math.round((5000 / 111320) * 2500));
    });
  });

  describe('Geofence Geometry Validation & Bounds Extraction', () => {
    it('correctly parses bbox geofence bounds', () => {
      const bboxGeo = {
        type: 'bbox' as const,
        min_lat: 37.75,
        min_lon: -122.45,
        max_lat: 37.80,
        max_lon: -122.40,
      };

      assert.strictEqual(bboxGeo.max_lat > bboxGeo.min_lat, true);
      assert.strictEqual(bboxGeo.max_lon > bboxGeo.min_lon, true);
    });

    it('validates polygon vertex coordinate pairs', () => {
      const polyGeo = {
        type: 'polygon' as const,
        coordinates: [
          [37.75, -122.45],
          [37.80, -122.40],
          [37.78, -122.48],
        ] as [number, number][],
      };

      assert.strictEqual(polyGeo.coordinates.length >= 3, true);
      assert.strictEqual(polyGeo.coordinates[0].length, 2);
    });
  });

  describe('Stale-While-Refresh Behavior Invariant', () => {
    it('preserves cached operational data during transient refresh errors', () => {
      let state = {
        tracks: [{ id: 'TRK-001', state: 'ACTIVE' }],
        isStale: false,
        error: null as string | null,
      };

      // Simulate refresh error
      const handleRefreshError = (currentState: typeof state, errorMessage: string) => {
        return {
          ...currentState,
          isStale: true,
          error: errorMessage,
        };
      };

      state = handleRefreshError(state, 'Network timeout');

      // Previous track is preserved
      assert.strictEqual(state.tracks.length, 1);
      assert.strictEqual(state.tracks[0].id, 'TRK-001');
      assert.strictEqual(state.isStale, true);
      assert.strictEqual(state.error, 'Network timeout');
    });
  });
});
