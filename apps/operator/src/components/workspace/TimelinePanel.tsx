import React, { useMemo, useState } from 'react';
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
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('ALL');
  const [timeWindowPreset, setTimeWindowPreset] = useState<'ALL' | '15m' | '1h' | '6h'>('ALL');

  const filteredTimeline = useMemo(() => {
    let result = timeline;

    if (eventTypeFilter !== 'ALL') {
      result = result.filter((item) =>
        item.event_type.toUpperCase().includes(eventTypeFilter)
      );
    }

    if (timeWindowPreset !== 'ALL') {
      const now = new Date().getTime();
      const cutoffMinutes =
        timeWindowPreset === '15m' ? 15 : timeWindowPreset === '1h' ? 60 : 360;
      const cutoffTime = now - cutoffMinutes * 60 * 1000;

      result = result.filter((item) => {
        const itemTime = new Date(item.timestamp).getTime();
        return itemTime >= cutoffTime;
      });
    }

    return result;
  }, [timeline, eventTypeFilter, timeWindowPreset]);

  return (
    <Card
      title="Operational Timeline Feed"
      badge={
        <span className="font-mono text-xs text-muted">
          EVENTS: {filteredTimeline.length} / {timeline.length}
        </span>
      }
      actions={
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
          {/* Time Window Presets */}
          <div style={{ display: 'flex', gap: '2px' }}>
            {(['ALL', '15m', '1h', '6h'] as const).map((preset) => (
              <button
                key={preset}
                onClick={() => setTimeWindowPreset(preset)}
                className="tactical-btn font-mono"
                style={{
                  padding: '2px 6px',
                  fontSize: '10px',
                  backgroundColor: timeWindowPreset === preset ? 'var(--bg-surface-active)' : 'transparent',
                  borderColor: timeWindowPreset === preset ? 'var(--color-accent)' : 'transparent',
                  color: timeWindowPreset === preset ? 'var(--color-accent)' : 'var(--text-muted)',
                }}
              >
                {preset}
              </button>
            ))}
          </div>

          {/* Event Type Filter */}
          <select
            className="tactical-select font-mono"
            value={eventTypeFilter}
            onChange={(e) => setEventTypeFilter(e.target.value)}
            style={{ padding: '2px 6px', fontSize: '11px' }}
          >
            <option value="ALL">ALL TYPES</option>
            <option value="TRACK">TRACKS</option>
            <option value="ALERT">ALERTS</option>
            <option value="THREAT">THREATS</option>
            <option value="SENSOR">SENSORS</option>
            <option value="GEOFENCE">GEOFENCES</option>
          </select>

          {onRefresh && (
            <Button variant="ghost" size="sm" onClick={onRefresh} isLoading={isLoading} style={{ padding: '2px 6px', fontSize: '11px' }}>
              ↻
            </Button>
          )}
        </div>
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
      ) : filteredTimeline.length === 0 ? (
        <EmptyState
          title="No Events Found"
          description={
            timeline.length > 0
              ? 'No events match the selected type or time window filter.'
              : 'No timeline events currently recorded in the active operational window.'
          }
        />
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
              {filteredTimeline.map((item, idx) => (
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
                  <td style={{ color: 'var(--text-primary)', maxWidth: '360px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
