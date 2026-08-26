import React from 'react';
import { Alert, Geofence, SelectedEntity, Sensor, ThreatAssessment, Track, TrackHistoryPoint } from '../../types';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { AlertInspector } from './AlertInspector';
import { GeofenceInspector } from './GeofenceInspector';
import { SensorInspector } from './SensorInspector';
import { ThreatInspector } from './ThreatInspector';
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
  onSelectSensor?: (sensorId: string) => void;
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
  onSelectSensor,
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
          description="Select any track marker, sensor asset, geofence boundary, alert, or threat triage row to inspect telemetry, kinematics, and threat breakdown."
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

  if (selectedEntity.type === 'alert') {
    const alert = alerts.find((a) => a.id === selectedEntity.id);
    if (!alert) {
      return (
        <Card title="Alert Inspection">
          <EmptyState title="Alert Not Found" description={`Alert ${selectedEntity.id} was not found in operational feed.`} />
        </Card>
      );
    }

    return (
      <AlertInspector
        alert={alert}
        onClose={onClearSelection}
        onSelectTrack={onSelectTrack}
        onSelectSensor={onSelectSensor}
      />
    );
  }

  if (selectedEntity.type === 'threat') {
    // threat id might be the threat.id or threat.track_id
    const threat = threats.find((th) => th.id === selectedEntity.id || th.track_id === selectedEntity.id);
    if (!threat) {
      return (
        <Card title="Threat Inspection">
          <EmptyState title="Threat Assessment Not Found" description={`Threat assessment for ${selectedEntity.id} is not available.`} />
        </Card>
      );
    }

    const track = tracks.find((t) => t.id === threat.track_id) || null;
    const relatedAlerts = alerts.filter((a) => a.track_id === threat.track_id);

    return (
      <ThreatInspector
        threat={threat}
        track={track}
        relatedAlerts={relatedAlerts}
        geofences={geofences}
        onClose={onClearSelection}
        onSelectTrack={onSelectTrack}
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
