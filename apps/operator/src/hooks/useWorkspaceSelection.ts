import { useCallback, useState } from 'react';
import { EntityType, SelectedEntity } from '../types';

export interface WorkspaceSelectionHookReturn {
  selectedEntity: SelectedEntity | null;
  selectedTrackId: string | null;
  selectedSensorId: string | null;
  selectedGeofenceId: string | null;
  selectedAlertId: string | null;
  selectedThreatId: string | null;
  selectTrack: (trackId: string) => void;
  selectSensor: (sensorId: string) => void;
  selectGeofence: (geofenceId: string) => void;
  selectAlert: (alertId: string, trackId?: string | null) => void;
  selectThreat: (threatId: string, trackId?: string | null) => void;
  selectEntity: (type: EntityType, id: string) => void;
  clearSelection: () => void;
}

export function useWorkspaceSelection(initialSelectedEntity: SelectedEntity | null = null): WorkspaceSelectionHookReturn {
  const [selectedEntity, setSelectedEntity] = useState<SelectedEntity | null>(initialSelectedEntity);

  const selectTrack = useCallback((trackId: string) => {
    setSelectedEntity({ type: 'track', id: trackId });
  }, []);

  const selectSensor = useCallback((sensorId: string) => {
    setSelectedEntity({ type: 'sensor', id: sensorId });
  }, []);

  const selectGeofence = useCallback((geofenceId: string) => {
    setSelectedEntity({ type: 'geofence', id: geofenceId });
  }, []);

  const selectAlert = useCallback((alertId: string, trackId?: string | null) => {
    if (trackId) {
      setSelectedEntity({ type: 'track', id: trackId });
    } else {
      setSelectedEntity({ type: 'alert', id: alertId });
    }
  }, []);

  const selectThreat = useCallback((threatId: string, trackId?: string | null) => {
    if (trackId) {
      setSelectedEntity({ type: 'track', id: trackId });
    } else {
      setSelectedEntity({ type: 'threat', id: threatId });
    }
  }, []);

  const selectEntity = useCallback((type: EntityType, id: string) => {
    setSelectedEntity({ type, id });
  }, []);

  const clearSelection = useCallback(() => {
    setSelectedEntity(null);
  }, []);

  const selectedTrackId = selectedEntity?.type === 'track' ? selectedEntity.id : null;
  const selectedSensorId = selectedEntity?.type === 'sensor' ? selectedEntity.id : null;
  const selectedGeofenceId = selectedEntity?.type === 'geofence' ? selectedEntity.id : null;
  const selectedAlertId = selectedEntity?.type === 'alert' ? selectedEntity.id : null;
  const selectedThreatId = selectedEntity?.type === 'threat' ? selectedEntity.id : null;

  return {
    selectedEntity,
    selectedTrackId,
    selectedSensorId,
    selectedGeofenceId,
    selectedAlertId,
    selectedThreatId,
    selectTrack,
    selectSensor,
    selectGeofence,
    selectAlert,
    selectThreat,
    selectEntity,
    clearSelection,
  };
}
