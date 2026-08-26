import React from 'react';
import { Alert } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';

interface AlertPanelProps {
  alerts: Alert[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

export const AlertPanel: React.FC<AlertPanelProps> = ({
  alerts,
  isLoading = false,
  error,
  onRefresh,
}) => {
  return (
    <Card
      title="Alert Feed"
      badge={
        <span className="font-mono text-xs text-muted">
          ACTIVE: {alerts.filter((a) => a.status === 'OPEN').length}
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
      {isLoading && alerts.length === 0 ? (
        <LoadingState message="Querying alert status..." />
      ) : error ? (
        <div style={{ padding: 'var(--space-md)' }}>
          <ErrorState message={error} onRetry={onRefresh} />
        </div>
      ) : alerts.length === 0 ? (
        <EmptyState title="No Active Alerts" description="No unacknowledged operational alerts currently recorded in the system." />
      ) : (
        <div className="tactical-table-wrapper" style={{ maxHeight: '280px' }}>
          <table className="tactical-table">
            <thead>
              <tr>
                <th>Severity</th>
                <th>Alert Type</th>
                <th>Reason / Summary</th>
                <th>Track Ref</th>
                <th>Status</th>
                <th>Timestamp</th>
              </tr>
            </thead>
            <tbody>
              {alerts.map((a) => (
                <tr key={a.id}>
                  <td>
                    <StatusBadge status={a.severity} />
                  </td>
                  <td className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {a.type}
                  </td>
                  <td style={{ maxWidth: '240px', overflow: 'hidden', textOverflow: 'ellipsis', color: 'var(--text-primary)' }}>
                    {a.reason}
                  </td>
                  <td className="font-mono text-xs text-muted">
                    {a.track_id || 'N/A'}
                  </td>
                  <td>
                    <StatusBadge status={a.status} />
                  </td>
                  <td className="font-mono text-xs text-muted">
                    {a.created_at.substring(11, 19)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </Card>
  );
};
