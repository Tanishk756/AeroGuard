import React from 'react';
import { TimelineItem } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';
import { LoadingState } from '../common/LoadingState';

interface TimelinePanelProps {
  timeline: TimelineItem[];
  onSelectEvent?: (item: TimelineItem) => void;
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

export const TimelinePanel: React.FC<TimelinePanelProps> = ({
  timeline,
  onSelectEvent,
  isLoading = false,
  error,
  onRefresh,
}) => {
  return (
    <Card
      title="Operational Timeline Feed"
      badge={
        <span className="font-mono text-xs text-muted">
          EVENTS: {timeline.length}
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
      {isLoading && timeline.length === 0 ? (
        <LoadingState message="Fetching timeline events..." />
      ) : error ? (
        <div style={{ padding: 'var(--space-md)' }}>
          <ErrorState message={error} onRetry={onRefresh} />
        </div>
      ) : timeline.length === 0 ? (
        <EmptyState title="No Events Recorded" description="No timeline events currently recorded in the active operational window." />
      ) : (
        <div className="tactical-table-wrapper" style={{ maxHeight: '360px' }}>
          <table className="tactical-table">
            <thead>
              <tr>
                <th>Time (UTC)</th>
                <th>Event Type</th>
                <th>Entity / Track</th>
                <th>Summary</th>
              </tr>
            </thead>
            <tbody>
              {timeline.map((item, idx) => (
                <tr
                  key={`${item.timestamp}-${item.entity_id}-${idx}`}
                  onClick={() => onSelectEvent?.(item)}
                  style={{ cursor: 'pointer' }}
                >
                  <td className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                    {item.timestamp.substring(11, 19)}
                  </td>
                  <td className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                    {item.event_type}
                  </td>
                  <td className="font-mono text-xs text-muted">
                    {item.track_id || item.entity_id}
                  </td>
                  <td style={{ color: 'var(--text-primary)', maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {item.summary}
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
