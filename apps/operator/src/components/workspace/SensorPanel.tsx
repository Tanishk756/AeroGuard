import React from 'react';
import { Sensor } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';

interface SensorPanelProps {
  sensors: Sensor[];
  selectedSensorId?: string | null;
  onSelectSensor?: (sensorId: string) => void;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

export const SensorPanel: React.FC<SensorPanelProps> = ({
  sensors,
  selectedSensorId,
  onSelectSensor,
  isLoading = false,
  error,
  onRefresh,
}) => {
  return (
    <Card
      title="Sensor Assets"
      badge={<span className="font-mono text-xs text-muted">TOTAL: {sensors.length}</span>}
      actions={
        onRefresh && (
          <Button variant="ghost" size="sm" onClick={onRefresh} isLoading={isLoading}>
            Refresh
          </Button>
        )
      }
      style={{ height: '100%' }}
      bodyStyle={{ padding: 0 }}
    >
      {isLoading && sensors.length === 0 ? (
        <LoadingState message="Loading sensor registry..." />
      ) : error ? (
        <div style={{ padding: 'var(--space-md)' }}>
          <ErrorState message={error} onRetry={onRefresh} />
        </div>
      ) : sensors.length === 0 ? (
        <EmptyState title="No Sensors Registered" description="No sensor assets found in registry." />
      ) : (
        <div className="tactical-table-wrapper" style={{ maxHeight: '360px' }}>
          <table className="tactical-table">
            <thead>
              <tr>
                <th>Sensor Name</th>
                <th>Modality</th>
                <th>Source Class</th>
                <th>Status</th>
                <th>Range (m)</th>
                <th>Coordinates</th>
              </tr>
            </thead>
            <tbody>
              {sensors.map((s) => {
                const isSelected = s.id === selectedSensorId;
                const lat = s.configuration_metadata?.latitude;
                const lon = s.configuration_metadata?.longitude;
                const range = s.configuration_metadata?.range_meters;

                return (
                  <tr
                    key={s.id}
                    onClick={() => onSelectSensor?.(s.id)}
                    style={{
                      cursor: 'pointer',
                      backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                    }}
                  >
                    <td className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {s.name}
                    </td>
                    <td className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                      {s.source_type.toUpperCase()}
                    </td>
                    <td>
                      <StatusBadge status={s.source_class} />
                    </td>
                    <td>
                      <StatusBadge status={s.status} />
                    </td>
                    <td className="font-mono text-xs">
                      {range != null ? `${Number(range).toLocaleString()} m` : 'N/A'}
                    </td>
                    <td className="font-mono text-xs text-muted">
                      {lat != null && lon != null ? `${Number(lat).toFixed(4)}°, ${Number(lon).toFixed(4)}°` : 'Stationary / Unset'}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
