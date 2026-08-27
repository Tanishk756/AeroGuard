/**
 * AeroGuard MAP2 Tactical Renderer Types & Contracts
 */

import { AnomalySeverity, Geofence, Sensor, Track, TrackHistoryPoint, TrajectoryPrediction } from '../../../types';

export type RendererType = 'WEBGPU' | 'CANVAS' | 'LEGACY';

export interface RendererCapabilities {
  preferredType: RendererType;
  hasWebGPU: boolean;
  hasCanvas2D: boolean;
  adapterInfo?: {
    vendor?: string;
    architecture?: string;
    device?: string;
    description?: string;
  };
  maxTextureDimension2D?: number;
  devicePixelRatio: number;
  diagnosticsMessage: string;
}

export interface RenderViewport {
  centerLat: number;
  centerLon: number;
  zoom: number;
  panOffsetX: number;
  panOffsetY: number;
  width: number;
  height: number;
  devicePixelRatio: number;
}

export interface RenderTrackItem {
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
  anomalyLevel?: AnomalySeverity | null;
  groupId?: string | null;
  behaviorState?: string | null;
  priorityScore?: number | null;
  priorityLevel?: string | null;
  isCoordinated?: boolean;
  isSelected: boolean;
  isThreatElevated: boolean;
}

export interface RenderTrailPoint {
  screenX: number;
  screenY: number;
  alpha: number;
}

export interface RenderTrackTrail {
  trackId: string;
  points: RenderTrailPoint[];
  isSelected: boolean;
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

export interface RenderGeofenceItem {
  id: string;
  name: string;
  geometryType: 'BBOX' | 'POLYGON' | 'CIRCLE';
  screenCoordinates: Array<{ x: number; y: number }>;
  radiusPixels?: number;
  minAltitude?: number | null;
  maxAltitude?: number | null;
  status: 'ENABLED' | 'DISABLED' | 'SELECTED' | 'WARNING';
  isSelected: boolean;
}

export interface RenderSensorItem {
  id: string;
  name: string;
  screenX: number;
  screenY: number;
  rangeRadiusPixels?: number | null;
  status: string;
  sourceType: string;
  isSelected: boolean;
}

export interface RenderPredictionItem {
  trackId: string;
  waypoints: Array<{
    screenX: number;
    screenY: number;
    timeOffsetSeconds: number;
    uncertaintyRadiusPixels: number;
  }>;
  ingressIntersections?: Array<{
    geofenceId: string;
    geofenceName: string;
    screenX: number;
    screenY: number;
    timeToBreachSeconds?: number | null;
    status: 'INSIDE' | 'APPROACHING';
  }>;
}

export interface RenderLayerVisibility {
  grid: boolean;
  rangeRings: boolean;
  geofences: boolean;
  sensors: boolean;
  trajectories: boolean;
  tracks: boolean;
  labels: boolean;
  groups?: boolean;
}

export interface RenderScene {
  viewport: RenderViewport;
  layers: RenderLayerVisibility;
  tracks: RenderTrackItem[];
  trails: RenderTrackTrail[];
  prediction: RenderPredictionItem | null;
  geofences: RenderGeofenceItem[];
  sensors: RenderSensorItem[];
  groups?: RenderGroupItem[];
  selectedTrackId?: string | null;
  selectedSensorId?: string | null;
  selectedGeofenceId?: string | null;
  selectedGroupId?: string | null;
  timestamp: number;
}

export interface HitTestResult {
  type: 'track' | 'sensor' | 'geofence' | 'group';
  id: string;
  screenX: number;
  screenY: number;
  distancePixels: number;
}

export interface IMapRenderer {
  readonly type: RendererType;
  readonly isInitialized: boolean;
  initialize(canvas: HTMLCanvasElement): Promise<boolean>;
  render(scene: RenderScene): void;
  resize(width: number, height: number): void;
  hitTest(screenX: number, screenY: number, scene: RenderScene): HitTestResult | null;
  destroy(): void;
}
