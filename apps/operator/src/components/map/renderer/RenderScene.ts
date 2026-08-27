/**
 * AeroGuard Scene Normalization and Packing for Tactical Renderers
 */

import {
  DefensiveIntelligenceSummary,
  Geofence,
  MapLayerVisibility,
  Sensor,
  ThreatAssessment,
  Track,
  TrackHistoryPoint,
  TrajectoryPrediction,
} from '../../../types';
import {
  RenderGeofenceItem,
  RenderLayerVisibility,
  RenderPredictionItem,
  RenderScene,
  RenderSensorItem,
  RenderTrackItem,
  RenderTrackTrail,
  RenderViewport,
} from './types';

const BASE_PIXELS_PER_DEGREE = 2500;
const EARTH_RADIUS_METERS = 6371000;

export interface BuildSceneOptions {
  width: number;
  height: number;
  centerLat: number;
  centerLon: number;
  zoom: number;
  panOffsetX?: number;
  panOffsetY?: number;
  devicePixelRatio?: number;
  layers?: Partial<MapLayerVisibility>;
  tracks: Track[];
  threats?: ThreatAssessment[];
  intelligence?: Record<string, DefensiveIntelligenceSummary>;
  selectedTrackId?: string | null;
  selectedSensorId?: string | null;
  selectedGeofenceId?: string | null;
  selectedTrackHistory?: TrackHistoryPoint[];
  selectedTrackPrediction?: TrajectoryPrediction | null;
  geofences?: Geofence[];
  sensors?: Sensor[];
  maxTrailLength?: number;
}

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

export function buildRenderScene(options: BuildSceneOptions): RenderScene {
  const {
    width,
    height,
    centerLat,
    centerLon,
    zoom,
    panOffsetX = 0,
    panOffsetY = 0,
    devicePixelRatio = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1,
    layers = {},
    tracks,
    threats = [],
    intelligence = {},
    selectedTrackId = null,
    selectedSensorId = null,
    selectedGeofenceId = null,
    selectedTrackHistory = [],
    selectedTrackPrediction = null,
    geofences = [],
    sensors = [],
    maxTrailLength = 30,
  } = options;

  const viewport: RenderViewport = {
    centerLat,
    centerLon,
    zoom,
    panOffsetX,
    panOffsetY,
    width,
    height,
    devicePixelRatio,
  };

  const activeLayers: RenderLayerVisibility = {
    grid: layers.grid !== false,
    rangeRings: layers.rangeRings !== false,
    geofences: layers.geofences !== false,
    sensors: layers.sensors !== false,
    trajectories: layers.trajectories !== false,
    tracks: layers.tracks !== false,
    labels: layers.labels !== false,
  };

  // 1. Build threat map for O(1) lookup
  const threatMap = new Map<string, ThreatAssessment>();
  for (const th of threats) {
    if (th.track_id) {
      threatMap.set(th.track_id, th);
    }
  }

  // 2. Build normalized Track items
  const renderTracks: RenderTrackItem[] = [];
  for (const t of tracks) {
    const screen = projectLatLon(
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

    const isSelected = t.id === selectedTrackId;
    const th = threatMap.get(t.id);
    const intel = intelligence[t.id];

    renderTracks.push({
      id: t.id,
      latitude: t.latitude,
      longitude: t.longitude,
      screenX: screen.x,
      screenY: screen.y,
      altitude: t.altitude,
      velocity: t.velocity,
      heading: t.heading,
      state: t.state,
      classification: t.classification,
      confidence: t.confidence,
      anomalyScore: intel?.anomaly?.anomaly_score ?? null,
      anomalyLevel: intel?.anomaly?.anomaly_level ?? null,
      isSelected,
      isThreatElevated: (th?.score ?? 0) >= 50,
    });
  }

  // 3. Build selected track history trails (bounded)
  const renderTrails: RenderTrackTrail[] = [];
  if (selectedTrackId && selectedTrackHistory.length > 1) {
    const boundedPoints = selectedTrackHistory.slice(-maxTrailLength);
    const trailPoints = boundedPoints.map((pt, idx) => {
      const p = projectLatLon(
        pt.latitude,
        pt.longitude,
        centerLat,
        centerLon,
        zoom,
        panOffsetX,
        panOffsetY,
        width,
        height
      );
      const alpha = 0.3 + (0.7 * (idx + 1)) / boundedPoints.length;
      return { screenX: p.x, screenY: p.y, alpha };
    });

    renderTrails.push({
      trackId: selectedTrackId,
      points: trailPoints,
      isSelected: true,
    });
  }

  // 4. Build AI forward trajectory predictions
  let renderPrediction: RenderPredictionItem | null = null;
  if (selectedTrackId && selectedTrackPrediction && selectedTrackPrediction.waypoints?.length > 0) {
    const cosLat = Math.cos((centerLat * Math.PI) / 180);
    const pixelsPerMeter = (BASE_PIXELS_PER_DEGREE * zoom * cosLat) / ((2 * Math.PI * EARTH_RADIUS_METERS) / 360);

    const waypoints = selectedTrackPrediction.waypoints.map((wp) => {
      const p = projectLatLon(
        wp.latitude,
        wp.longitude,
        centerLat,
        centerLon,
        zoom,
        panOffsetX,
        panOffsetY,
        width,
        height
      );
      const radiusPixels = Math.max(3, wp.uncertainty_radius_meters * pixelsPerMeter);
      return {
        screenX: p.x,
        screenY: p.y,
        timeOffsetSeconds: wp.time_offset_seconds,
        uncertaintyRadiusPixels: radiusPixels,
      };
    });

    renderPrediction = {
      trackId: selectedTrackId,
      waypoints,
    };
  }

  // 5. Build normalized Geofence items
  const renderGeofences: RenderGeofenceItem[] = [];
  for (const g of geofences) {
    const isSelected = g.id === selectedGeofenceId;
    let geomType: 'BBOX' | 'POLYGON' | 'CIRCLE' = 'BBOX';
    const screenCoordinates: Array<{ x: number; y: number }> = [];
    const radiusPixels: number | undefined = undefined;

    if (g.geometry.type === 'polygon' && Array.isArray(g.geometry.coordinates)) {
      geomType = 'POLYGON';
      for (const coord of g.geometry.coordinates) {
        if (Array.isArray(coord) && coord.length >= 2) {
          const lat = coord[0];
          const lon = coord[1];
          screenCoordinates.push(
            projectLatLon(lat, lon, centerLat, centerLon, zoom, panOffsetX, panOffsetY, width, height)
          );
        }
      }
    } else if (g.geometry.type === 'bbox') {
      geomType = 'BBOX';
      const minLat = g.geometry.min_lat;
      const maxLat = g.geometry.max_lat;
      const minLon = g.geometry.min_lon;
      const maxLon = g.geometry.max_lon;

      const p1 = projectLatLon(maxLat, minLon, centerLat, centerLon, zoom, panOffsetX, panOffsetY, width, height);
      const p2 = projectLatLon(maxLat, maxLon, centerLat, centerLon, zoom, panOffsetX, panOffsetY, width, height);
      const p3 = projectLatLon(minLat, maxLon, centerLat, centerLon, zoom, panOffsetX, panOffsetY, width, height);
      const p4 = projectLatLon(minLat, minLon, centerLat, centerLon, zoom, panOffsetX, panOffsetY, width, height);
      screenCoordinates.push(p1, p2, p3, p4);
    }

    const status = isSelected
      ? 'SELECTED'
      : !g.enabled
      ? 'DISABLED'
      : 'ENABLED';

    renderGeofences.push({
      id: g.id,
      name: g.name,
      geometryType: geomType,
      screenCoordinates,
      radiusPixels,
      minAltitude: g.min_altitude,
      maxAltitude: g.max_altitude,
      status,
      isSelected,
    });
  }

  // 6. Build normalized Sensor items
  const renderSensors: RenderSensorItem[] = [];
  for (const s of sensors) {
    const isSelected = s.id === selectedSensorId;
    const lat = s.configuration_metadata?.latitude;
    const lon = s.configuration_metadata?.longitude;

    if (typeof lat === 'number' && typeof lon === 'number') {
      const screen = projectLatLon(lat, lon, centerLat, centerLon, zoom, panOffsetX, panOffsetY, width, height);
      let rangeRadiusPixels: number | null = null;
      const rangeMeters = s.configuration_metadata?.range_meters;
      if (typeof rangeMeters === 'number' && rangeMeters > 0) {
        const cosLat = Math.cos((centerLat * Math.PI) / 180);
        const pixelsPerMeter = (BASE_PIXELS_PER_DEGREE * zoom * cosLat) / ((2 * Math.PI * EARTH_RADIUS_METERS) / 360);
        rangeRadiusPixels = rangeMeters * pixelsPerMeter;
      }

      renderSensors.push({
        id: s.id,
        name: s.name,
        screenX: screen.x,
        screenY: screen.y,
        rangeRadiusPixels,
        status: s.status,
        sourceType: s.source_type,
        isSelected,
      });
    }
  }

  return {
    viewport,
    layers: activeLayers,
    tracks: renderTracks,
    trails: renderTrails,
    prediction: renderPrediction,
    geofences: renderGeofences,
    sensors: renderSensors,
    selectedTrackId,
    selectedSensorId,
    selectedGeofenceId,
    timestamp: Date.now(),
  };
}
