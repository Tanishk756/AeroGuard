/**
 * AeroGuard Scene Normalization and Packing for Tactical Renderers
 */

import {
  DefensiveIntelligenceSummary,
  Geofence,
  Incident,
  MapLayerVisibility,
  MultiTrackIntelligenceSummary,
  Sensor,
  ThreatAssessment,
  Track,
  TrackHistoryPoint,
  TrajectoryPrediction,
} from '../../../types';
import {
  RenderGeofenceItem,
  RenderGroupItem,
  RenderIncidentItem,
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
  multiTrackIntelligence?: MultiTrackIntelligenceSummary | null;
  selectedTrackId?: string | null;
  selectedSensorId?: string | null;
  selectedGeofenceId?: string | null;
  selectedGroupId?: string | null;
  selectedIncidentId?: string | null;
  selectedTrackHistory?: TrackHistoryPoint[];
  selectedTrackPrediction?: TrajectoryPrediction | null;
  geofences?: Geofence[];
  sensors?: Sensor[];
  incidents?: Incident[];
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
    multiTrackIntelligence = null,
    selectedTrackId = null,
    selectedSensorId = null,
    selectedGeofenceId = null,
    selectedGroupId = null,
    selectedIncidentId = null,
    selectedTrackHistory = [],
    selectedTrackPrediction = null,
    geofences = [],
    sensors = [],
    incidents = [],
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
    groups: true,
    incidents: layers.incidents !== false,
  };

  // 1. Build threat map for O(1) lookup
  const threatMap = new Map<string, ThreatAssessment>();
  for (const th of threats) {
    if (th.track_id) {
      threatMap.set(th.track_id, th);
    }
  }

  // 2. Build normalized Track items with viewport spatial culling
  const renderTracks: RenderTrackItem[] = [];
  const CULL_PADDING = 60;

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
    const isVisible =
      screen.x >= -CULL_PADDING &&
      screen.x <= width + CULL_PADDING &&
      screen.y >= -CULL_PADDING &&
      screen.y <= height + CULL_PADDING;

    if (isVisible || isSelected) {
      const th = threatMap.get(t.id);
      const intel = intelligence[t.id];

      // Multi-track intelligence lookups
      let groupId: string | null = null;
      let behaviorState: string | null = null;
      let priorityScore: number | null = intel?.priority?.priority_score ?? null;
      let priorityLevel: string | null = intel?.priority?.priority_level ?? null;
      let isCoordinated = false;

      if (multiTrackIntelligence) {
        if (!priorityScore && multiTrackIntelligence.priorities) {
          const p = multiTrackIntelligence.priorities.find((x) => x.track_id === t.id);
          if (p) {
            priorityScore = p.priority_score;
            priorityLevel = p.priority_level;
            if (p.group_id) groupId = p.group_id;
          }
        }
        if (multiTrackIntelligence.behaviors) {
          const b = multiTrackIntelligence.behaviors.find((x) => x.track_id === t.id);
          if (b) behaviorState = b.state;
        }
        if (!groupId && multiTrackIntelligence.groups) {
          const g = multiTrackIntelligence.groups.find((x) => x.member_track_ids.includes(t.id));
          if (g) groupId = g.group_id;
        }
        if (multiTrackIntelligence.formations) {
          isCoordinated = multiTrackIntelligence.formations.some((f) => f.member_track_ids.includes(t.id));
        }
      }

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
        groupId,
        behaviorState,
        priorityScore,
        priorityLevel,
        isCoordinated,
        isSelected,
        isThreatElevated: (th?.score ?? 0) >= 50 || (priorityScore != null && priorityScore >= 60),
      });
    }
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

    // Extract ingress estimates for selected track
    const intel = intelligence[selectedTrackId];
    const ingressIntersections: RenderPredictionItem['ingressIntersections'] = [];

    if (intel?.ingress_estimates) {
      for (const ing of intel.ingress_estimates) {
        if ((ing.status === 'APPROACHING' || ing.status === 'INSIDE') && typeof ing.intersection_latitude === 'number' && typeof ing.intersection_longitude === 'number') {
          const ip = projectLatLon(
            ing.intersection_latitude,
            ing.intersection_longitude,
            centerLat,
            centerLon,
            zoom,
            panOffsetX,
            panOffsetY,
            width,
            height
          );
          ingressIntersections.push({
            geofenceId: ing.geofence_id,
            geofenceName: ing.geofence_name,
            screenX: ip.x,
            screenY: ip.y,
            timeToBreachSeconds: ing.estimated_time_to_breach_seconds,
            status: ing.status,
          });
        }
      }
    }

    renderPrediction = {
      trackId: selectedTrackId,
      waypoints,
      ingressIntersections,
    };
  }

  // 5. Build normalized Geofence items
  const renderGeofences: RenderGeofenceItem[] = [];
  const warningGeofenceIds = new Set<string>();

  if (selectedTrackId && intelligence[selectedTrackId]?.ingress_estimates) {
    for (const ing of intelligence[selectedTrackId].ingress_estimates) {
      if (ing.status === 'APPROACHING' || ing.status === 'INSIDE') {
        warningGeofenceIds.add(ing.geofence_id);
      }
    }
  }

  for (const g of geofences) {
    const isSelected = g.id === selectedGeofenceId;
    const isWarning = warningGeofenceIds.has(g.id);
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
      : isWarning
      ? 'WARNING'
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

  // 7. Build normalized Group items (AI2)
  const renderGroups: RenderGroupItem[] = [];
  if (multiTrackIntelligence?.groups && multiTrackIntelligence.groups.length > 0) {
    const formationMap = new Map<string, any>();
    if (multiTrackIntelligence.formations) {
      for (const f of multiTrackIntelligence.formations) {
        formationMap.set(f.group_id, f);
      }
    }

    const trackCoordMap = new Map<string, { x: number; y: number }>();
    for (const t of renderTracks) {
      trackCoordMap.set(t.id, { x: t.screenX, y: t.screenY });
    }

    const cosLat = Math.cos((centerLat * Math.PI) / 180);
    const pixelsPerMeter = (BASE_PIXELS_PER_DEGREE * zoom * cosLat) / ((2 * Math.PI * EARTH_RADIUS_METERS) / 360);

    for (const g of multiTrackIntelligence.groups) {
      const centroidScreen = projectLatLon(
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

      const radiusPixels = Math.max(20, g.radius_meters * pixelsPerMeter);
      const isSelected = g.group_id === selectedGroupId;

      const memberScreenCoords: Array<{ x: number; y: number; trackId: string }> = [];
      for (const mid of g.member_track_ids) {
        const coord = trackCoordMap.get(mid);
        if (coord) {
          memberScreenCoords.push({ x: coord.x, y: coord.y, trackId: mid });
        }
      }

      const formation = formationMap.get(g.group_id);

      renderGroups.push({
        groupId: g.group_id,
        centroidScreenX: centroidScreen.x,
        centroidScreenY: centroidScreen.y,
        radiusPixels,
        memberTrackIds: g.member_track_ids,
        memberScreenCoords,
        confidence: g.confidence,
        behaviorState: g.behavioral_state,
        isCoordinated: formation != null,
        synchronizationIndex: formation?.synchronization_index,
        isSelected,
      });
    }
  }

  // 8. Build normalized Incident items (IM1-F)
  const renderIncidents: RenderIncidentItem[] = [];
  if (incidents && incidents.length > 0) {
    const trackCoordMap = new Map<string, { x: number; y: number }>();
    for (const t of renderTracks) {
      trackCoordMap.set(t.id, { x: t.screenX, y: t.screenY });
    }

    const groupCoordMap = new Map<string, { x: number; y: number }>();
    if (multiTrackIntelligence?.groups) {
      for (const g of multiTrackIntelligence.groups) {
        const centroidScreen = projectLatLon(
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
        groupCoordMap.set(g.group_id, { x: centroidScreen.x, y: centroidScreen.y });
      }
    }

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
    viewport,
    layers: activeLayers,
    tracks: renderTracks,
    trails: renderTrails,
    prediction: renderPrediction,
    geofences: renderGeofences,
    sensors: renderSensors,
    groups: renderGroups,
    incidents: renderIncidents,
    selectedTrackId,
    selectedSensorId,
    selectedGeofenceId,
    selectedGroupId,
    selectedIncidentId,
    timestamp: Date.now(),
  };
}
