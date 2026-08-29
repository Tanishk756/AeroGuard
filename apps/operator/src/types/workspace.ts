import { AlertSeverity, AlertStatus } from './alert';
import { ThreatLevel } from './threat';
import { TrackState } from './track';

export type EntityType = 'track' | 'sensor' | 'geofence' | 'alert' | 'threat';

export interface SelectedEntity {
  type: EntityType;
  id: string;
}

export interface WorkspaceFilterState {
  trackState: TrackState | 'ALL';
  trackClassification: string;
  minConfidence: number;
  sensorStatus: string;
  sensorModality: string;
  alertSeverity: AlertSeverity | 'ALL';
  alertStatus: AlertStatus | 'ALL';
  threatLevel: ThreatLevel | 'ALL';
  searchQuery: string;
}

export interface MapLayerVisibility {
  tracks: boolean;
  sensors: boolean;
  geofences: boolean;
  rangeRings: boolean;
  trajectories: boolean;
  labels: boolean;
  grid: boolean;
  incidents?: boolean;
}

export interface MapViewportState {
  centerLat: number;
  centerLon: number;
  zoom: number;
  panOffset: { x: number; y: number };
}
