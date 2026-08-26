import React from 'react';
import { Geofence } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';

interface GeofencePanelProps {
  geofences: Geofence[];
  selectedGeofenceId?: string | null;
  onSelectGeofence?: (geofenceId: string) => void;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

export const GeofencePanel: React.FC<GeofencePanelProps> = ({
  geofences,
  selectedGeofenceId,
  onSelectGeofence,
  isLoading = false,
  error,
  onRefresh,
}) => {
  return (
    <Card
      title="Configured Geofences"
      badge={<span className="font-mono text-xs text-muted">TOTAL: {geofences.length}</span>}
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
      {isLoading && geofences.length === 0 ? (
        <LoadingState message="Loading geofence registry..." />
      ) : error ? (
        <div style={{ padding: 'var(--space-md)' }}>
          <ErrorState message={error} onRetry={onRefresh} />
        </div>
      ) : geofences.length === 0 ? (
        <EmptyState title="No Geofences Configured" description="No perimeter or exclusion zones defined." />
      ) : (
        <div className="tactical-table-wrapper" style={{ maxHeight: '360px' }}>
          <table className="tactical-table">
            <thead>
              <tr>
                <th>Name</th>
                <th>Status</th>
                <th>Geometry</th>
                <th>Altitude Bounds</th>
                <th>Geofence ID</th>
              </tr>
            </thead>
            <tbody>
              {geofences.map((g) => {
                const isSelected = g.id === selectedGeofenceId;
                const minAlt = g.min_altitude != null ? `${g.min_altitude}m` : '0m';
                const maxAlt = g.max_altitude != null ? `${g.max_altitude}m` : '∞';

                return (
                  <tr
                    key={g.id}
                    onClick={() => onSelectGeofence?.(g.id)}
                    style={{
                      cursor: 'pointer',
                      backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                    }}
                  >
                    <td className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {g.name}
                    </td>
                    <td>
                      <StatusBadge status={g.enabled ? 'ACTIVE' : 'INACTIVE'} label={g.enabled ? 'ENABLED' : 'DISABLED'} />
                    </td>
                    <td className="font-mono text-xs uppercase-tracking">
                      {g.geometry.type}
                    </td>
                    <td className="font-mono text-xs text-muted">
                      {minAlt} - {maxAlt}
                    </td>
                    <td className="font-mono text-xs text-muted">
                      {g.id}
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
