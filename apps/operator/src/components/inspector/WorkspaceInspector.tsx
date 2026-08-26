import React from 'react';
import { Alert, Geofence, SelectedEntity, Sensor, ThreatAssessment, Track, TrackHistoryPoint } from '../../types';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { GeofenceInspector } from './GeofenceInspector';
import { SensorInspector } from './SensorInspector';
import { TrackInspector } from './TrackInspector';

interface WorkspaceInspectorProps {
  selectedEntity: SelectedEntity | null;
  tracks: Track[];
  sensors: Sensor[];
  geofences: Geofence[];
  alerts: Alert[];
  threats: ThreatAssessment[];
  selectedTrackHistory?: TrackHistoryPoint[];
  isHistoryLoading?: boolean;
  onClearSelection: () => void;
  onSelectTrack: (trackId: string) => void;
  onSelectAlert: (alertId: string) => void;
}

export const WorkspaceInspector: React.FC<WorkspaceInspectorProps> = ({
  selectedEntity,
  tracks,
  sensors,
  geofences,
  alerts,
  threats,
  selectedTrackHistory = [],
  isHistoryLoading = false,
  onClearSelection,
  onSelectTrack,
  onSelectAlert,
}) => {
  if (!selectedEntity) {
    return (
      <Card
        title="Operational Inspector"
        badge={<span className="font-mono text-xs text-muted">IDLE</span>}
        style={{ height: '100%' }}
      >
        <EmptyState
          title="No Object Selected"
          description="Select any track marker, sensor asset, geofence, or registry row to inspect telemetry, kinematics, and threat breakdown."
          icon="🔍"
        />
      </Card>
    );
  }

  if (selectedEntity.type === 'track') {
    const track = tracks.find((t) => t.id === selectedEntity.id);
    if (!track) {
      return (
        <Card title="Track Inspection">
          <EmptyState title="Track Not Found" description={`Track ${selectedEntity.id} is no longer in active memory.`} />
        </Card>
      );
    }

    const threat = threats.find((th) => th.track_id === track.id) || null;
    const relatedAlerts = alerts.filter((a) => a.track_id === track.id);

    return (
      <TrackInspector
        track={track}
        threat={threat}
        relatedAlerts={relatedAlerts}
        geofences={geofences}
        historyPoints={selectedTrackHistory}
        isHistoryLoading={isHistoryLoading}
        onClose={onClearSelection}
        onSelectAlert={onSelectAlert}
      />
    );
  }

  if (selectedEntity.type === 'sensor') {
    const sensor = sensors.find((s) => s.id === selectedEntity.id);
    if (!sensor) {
      return (
        <Card title="Sensor Inspection">
          <EmptyState title="Sensor Not Found" description={`Sensor ${selectedEntity.id} is not in registered inventory.`} />
        </Card>
      );
    }

    return <SensorInspector sensor={sensor} onClose={onClearSelection} />;
  }

  if (selectedEntity.type === 'geofence') {
    const geofence = geofences.find((g) => g.id === selectedEntity.id);
    if (!geofence) {
      return (
        <Card title="Geofence Inspection">
          <EmptyState title="Geofence Not Found" description={`Geofence ${selectedEntity.id} is not configured.`} />
        </Card>
      );
    }

    return (
      <GeofenceInspector
        geofence={geofence}
        onClose={onClearSelection}
        onSelectTrack={onSelectTrack}
      />
    );
  }

  return (
    <Card title="Inspection">
      <EmptyState title="Unknown Entity" description="Selected entity type is not supported for inspection." />
    </Card>
  );
};
