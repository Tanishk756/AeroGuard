import React from 'react';
import { Track } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';

interface TrackPanelProps {
  tracks: Track[];
  selectedTrackId?: string | null;
  onSelectTrack?: (trackId: string) => void;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

export const TrackPanel: React.FC<TrackPanelProps> = ({
  tracks,
  selectedTrackId,
  onSelectTrack,
  isLoading = false,
  error,
  onRefresh,
}) => {
  return (
    <Card
      title="Track Registry"
      badge={
        <span className="font-mono text-xs text-muted">
          TOTAL: {tracks.length}
        </span>
      }
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
      {isLoading && tracks.length === 0 ? (
        <LoadingState message="Loading active tracks..." />
      ) : error ? (
        <div style={{ padding: 'var(--space-md)' }}>
          <ErrorState message={error} onRetry={onRefresh} />
        </div>
      ) : tracks.length === 0 ? (
        <EmptyState title="No Active Tracks" description="No correlated tracks currently maintained in operational memory." />
      ) : (
        <div className="tactical-table-wrapper" style={{ maxHeight: '360px' }}>
          <table className="tactical-table">
            <thead>
              <tr>
                <th>Track ID</th>
                <th>State</th>
                <th>Classification</th>
                <th>Qual / Conf</th>
                <th>Sources</th>
                <th>Coordinates</th>
              </tr>
            </thead>
            <tbody>
              {tracks.map((t) => {
                const isSelected = t.id === selectedTrackId;
                return (
                  <tr
                    key={t.id}
                    onClick={() => onSelectTrack?.(t.id)}
                    style={{
                      cursor: 'pointer',
                      backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                    }}
                  >
                    <td className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {t.id}
                    </td>
                    <td>
                      <StatusBadge status={t.state} />
                    </td>
                    <td className="uppercase-tracking" style={{ fontSize: 'var(--text-xs)' }}>
                      {t.classification || 'UNKNOWN'}
                    </td>
                    <td className="font-mono text-xs">
                      {Math.round(t.confidence * 100)}%
                    </td>
                    <td className="font-mono text-xs" style={{ textAlign: 'center' }}>
                      {t.source_count}
                    </td>
                    <td className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
                      {t.latitude.toFixed(4)}°, {t.longitude.toFixed(4)}°
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
