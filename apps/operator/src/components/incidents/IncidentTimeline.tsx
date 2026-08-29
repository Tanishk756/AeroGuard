/**
 * AeroGuard Incident Chronological Timeline Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React from 'react';
import { IncidentEvent } from '../../types';

export interface IncidentTimelineProps {
  events: IncidentEvent[];
  isLoading?: boolean;
}

export const getEventTypeTagStyle = (eventType: string) => {
  switch (eventType) {
    case 'CREATED':
      return { bg: 'rgba(59, 130, 246, 0.15)', color: '#60a5fa', border: '#3b82f6' };
    case 'ACKNOWLEDGED':
      return { bg: 'rgba(234, 179, 8, 0.15)', color: '#facc15', border: '#eab308' };
    case 'TRIAGED':
      return { bg: 'rgba(168, 85, 247, 0.15)', color: '#c084fc', border: '#a855f7' };
    case 'ESCALATED':
      return { bg: 'rgba(239, 68, 68, 0.2)', color: '#f87171', border: '#ef4444' };
    case 'DE_ESCALATED':
      return { bg: 'rgba(34, 197, 94, 0.15)', color: '#4ade80', border: '#22c55e' };
    case 'RESOLVED':
      return { bg: 'rgba(34, 197, 94, 0.2)', color: '#4ade80', border: '#22c55e' };
    case 'CLOSED':
      return { bg: 'rgba(107, 114, 128, 0.2)', color: '#9ca3af', border: '#6b7280' };
    case 'NOTE_ADDED':
      return { bg: 'rgba(14, 165, 233, 0.15)', color: '#38bdf8', border: '#0ea5e9' };
    case 'ACTION_LOGGED':
      return { bg: 'rgba(249, 115, 22, 0.15)', color: '#fb923c', border: '#f97316' };
    default:
      return { bg: 'rgba(148, 163, 184, 0.1)', color: '#cbd5e1', border: '#475569' };
  }
};

export const IncidentTimeline: React.FC<IncidentTimelineProps> = ({ events, isLoading = false }) => {
  if (isLoading && events.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }} className="font-mono text-xs text-muted">
        Loading event timeline...
      </div>
    );
  }

  if (events.length === 0) {
    return (
      <div style={{ padding: '24px', textAlign: 'center' }} className="font-mono text-xs text-muted">
        No timeline events recorded.
      </div>
    );
  }

  // Ensure sequence ordering
  const sortedEvents = [...events].sort((a, b) => a.sequence - b.sequence);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        padding: '16px 20px',
      }}
      role="feed"
      aria-label="Incident Timeline"
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <h3
          style={{
            margin: 0,
            fontSize: '13px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.05em',
            color: 'var(--text-secondary, #94a3b8)',
          }}
        >
          Immutable Event Timeline ({sortedEvents.length})
        </h3>
        <span className="font-mono text-xs text-muted">Append-Only Audit Ledger</span>
      </div>

      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '10px',
          position: 'relative',
        }}
      >
        {sortedEvents.map((evt) => {
          const style = getEventTypeTagStyle(evt.event_type);
          const isNote = evt.event_type === 'NOTE_ADDED';
          const isAction = evt.event_type === 'ACTION_LOGGED';

          return (
            <div
              key={evt.id}
              style={{
                display: 'flex',
                gap: '12px',
                padding: '10px 14px',
                borderRadius: '4px',
                backgroundColor: 'var(--bg-surface, #1e293b)',
                border: '1px solid var(--border-subtle, #273549)',
                borderLeft: `4px solid ${style.border}`,
              }}
            >
              {/* Sequence badge */}
              <div
                className="font-mono text-xs font-bold"
                style={{
                  color: 'var(--text-muted, #64748b)',
                  minWidth: '28px',
                  paddingTop: '1px',
                }}
              >
                #{evt.sequence}
              </div>

              {/* Event Content */}
              <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '6px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <span
                      className="font-mono"
                      style={{
                        fontSize: '11px',
                        fontWeight: 700,
                        padding: '2px 6px',
                        borderRadius: '3px',
                        backgroundColor: style.bg,
                        color: style.color,
                        border: `1px solid ${style.border}`,
                      }}
                    >
                      {evt.event_type}
                    </span>
                    {evt.category && (
                      <span
                        className="font-mono text-xs"
                        style={{
                          color: '#fb923c',
                          backgroundColor: 'rgba(249, 115, 22, 0.1)',
                          padding: '1px 5px',
                          borderRadius: '2px',
                        }}
                      >
                        {evt.category}
                      </span>
                    )}
                    {evt.actor_user_id && (
                      <span className="font-mono text-xs text-muted">
                        BY: <strong>{evt.actor_user_id}</strong>
                      </span>
                    )}
                  </div>
                  <span className="font-mono text-xs text-muted">
                    {new Date(evt.timestamp).toLocaleString()}
                  </span>
                </div>

                {/* Transition Summary or Message */}
                {(evt.previous_status || evt.new_status) && (
                  <div className="font-mono text-xs" style={{ color: 'var(--text-secondary, #cbd5e1)' }}>
                    Status transition:{' '}
                    <span style={{ color: 'var(--text-muted, #94a3b8)' }}>{evt.previous_status || 'NONE'}</span>
                    {' → '}
                    <strong style={{ color: style.color }}>{evt.new_status}</strong>
                  </div>
                )}

                {evt.message && (
                  <div
                    style={{
                      fontSize: '13px',
                      color: isNote ? 'var(--text-primary, #f8fafc)' : 'var(--text-secondary, #cbd5e1)',
                      backgroundColor: isNote ? 'rgba(0, 0, 0, 0.25)' : 'transparent',
                      padding: isNote ? '6px 8px' : '2px 0',
                      borderRadius: '3px',
                      marginTop: '2px',
                      lineHeight: '1.4',
                      fontStyle: isAction ? 'italic' : 'normal',
                    }}
                  >
                    {evt.message}
                  </div>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
