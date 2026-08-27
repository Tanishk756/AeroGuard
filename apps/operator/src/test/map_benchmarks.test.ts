import assert from 'node:assert';
import test, { describe, it } from 'node:test';

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
  isSelected: boolean;
  isThreatElevated: boolean;
}

const BASE_PIXELS_PER_DEGREE = 2500;

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

function hitTestTracks(screenX: number, screenY: number, tracks: RenderTrackItem[]): RenderTrackItem | null {
  const HIT_RADIUS = 16;
  let closest: RenderTrackItem | null = null;
  let minDist = Infinity;

  for (let i = 0; i < tracks.length; i++) {
    const t = tracks[i];
    const dx = screenX - t.screenX;
    const dy = screenY - t.screenY;
    const dist = Math.hypot(dx, dy);

    if (dist <= HIT_RADIUS && dist < minDist) {
      minDist = dist;
      closest = t;
    }
  }
  return closest;
}

describe('AeroGuard Stage MAP2 Tactical Renderer Performance Benchmarks', () => {
  const trackCounts = [10, 50, 100, 500, 1000];

  for (const count of trackCounts) {
    it(`benchmarks scene projection & culling throughput for ${count} tracks`, () => {
      const rawTracks = Array.from({ length: count }, (_, i) => ({
        id: `TRK-${i}`,
        latitude: 37.77 + (i % 100) * 0.001 - 0.05,
        longitude: -122.41 + Math.floor(i / 100) * 0.001 - 0.05,
        state: 'ACTIVE',
        confidence: 0.9,
      }));

      const width = 1920;
      const height = 1080;
      const centerLat = 37.7749;
      const centerLon = -122.4194;
      const zoom = 1.5;
      const CULL_PADDING = 60;

      const iterations = 50;
      const start = performance.now();

      let lastVisibleCount = 0;
      for (let iter = 0; iter < iterations; iter++) {
        const visibleTracks: RenderTrackItem[] = [];
        for (let i = 0; i < count; i++) {
          const t = rawTracks[i];
          const screen = projectLatLon(t.latitude, t.longitude, centerLat, centerLon, zoom, 0, 0, width, height);
          if (
            screen.x >= -CULL_PADDING &&
            screen.x <= width + CULL_PADDING &&
            screen.y >= -CULL_PADDING &&
            screen.y <= height + CULL_PADDING
          ) {
            visibleTracks.push({
              id: t.id,
              latitude: t.latitude,
              longitude: t.longitude,
              screenX: screen.x,
              screenY: screen.y,
              state: t.state,
              confidence: t.confidence,
              isSelected: false,
              isThreatElevated: false,
            });
          }
        }
        lastVisibleCount = visibleTracks.length;
      }

      const totalTimeMs = performance.now() - start;
      const avgTimeMs = totalTimeMs / iterations;
      const usPerTrack = (avgTimeMs * 1000) / count;

      assert.ok(lastVisibleCount > 0);
      assert.ok(avgTimeMs < 10.0, `Batch projection time (${avgTimeMs.toFixed(3)}ms) must be well under 16ms frame budget`);

      // Microbenchmark logging for verification report
      console.log(`[MAP2 Benchmark] Count: ${count.toString().padStart(4)} tracks | Batch Latency: ${avgTimeMs.toFixed(3)}ms | Per-Track: ${usPerTrack.toFixed(2)}µs`);
    });
  }

  it('benchmarks spatial hit testing latency on 1000 tracks', () => {
    const tracks: RenderTrackItem[] = Array.from({ length: 1000 }, (_, i) => ({
      id: `TRK-${i}`,
      latitude: 37.77,
      longitude: -122.41,
      screenX: (i % 40) * 25,
      screenY: Math.floor(i / 40) * 25,
      state: 'ACTIVE',
      confidence: 0.95,
      isSelected: false,
      isThreatElevated: false,
    }));

    const start = performance.now();
    const iterations = 500;
    for (let i = 0; i < iterations; i++) {
      hitTestTracks(500, 300, tracks);
    }
    const avgLatencyMs = (performance.now() - start) / iterations;

    assert.ok(avgLatencyMs < 0.1, `Hit test latency (${avgLatencyMs.toFixed(4)}ms) must be sub-millisecond`);
    console.log(`[MAP2 Benchmark] 1,000 Tracks Hit-Test Latency: ${(avgLatencyMs * 1000).toFixed(2)}µs`);
  });
});
