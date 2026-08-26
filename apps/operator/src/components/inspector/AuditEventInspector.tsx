import React from 'react';
import { AuditEvent } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';

interface AuditEventInspectorProps {
  event: AuditEvent;
  onClose?: () => void;
  onFilterByActor?: (actorId: string) => void;
  onFilterByTarget?: (targetType: string, targetId: string) => void;
}

export const AuditEventInspector: React.FC<AuditEventInspectorProps> = ({
  event,
  onClose,
  onFilterByActor,
  onFilterByTarget,
}) => {
  const metadataEntries = event.metadata ? Object.entries(event.metadata) : [];
  const isSuccess = event.result.toUpperCase() === 'SUCCESS';

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              width: '8px',
              height: '8px',
              backgroundColor: isSuccess ? 'var(--status-success)' : 'var(--status-critical)',
              borderRadius: '1px',
            }}
          />
          <h3 className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            AUDIT EVENT: {event.event_type}
          </h3>
        </div>

        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕ Close
          </Button>
        )}
      </div>

      {/* Outcome & Event Classification */}
      <Card
        title="Event Outcome & Classification"
        badge={<StatusBadge status={isSuccess ? 'ACTIVE' : 'CRITICAL'} label={event.result} />}
      >
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
          <div className="kv-row">
            <span className="kv-key">Event Type</span>
            <span className="kv-value font-mono" style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
              {event.event_type}
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Action Method</span>
            <span className="kv-value font-mono">{event.action}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Timestamp (UTC)</span>
            <span className="kv-value font-mono text-xs text-muted">
              {event.timestamp ? event.timestamp.substring(0, 19).replace('T', ' ') : 'N/A'}
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Event ID</span>
            <span className="kv-value font-mono text-xs text-muted" title={event.id}>
              {event.id.length > 18 ? `${event.id.substring(0, 18)}...` : event.id}
            </span>
          </div>
          {event.reason && (
            <div className="kv-row" style={{ gridColumn: '1 / -1' }}>
              <span className="kv-key">Outcome Reason</span>
              <span className="kv-value font-mono text-xs" style={{ color: isSuccess ? 'var(--text-primary)' : 'var(--status-critical)' }}>
                {event.reason}
              </span>
            </div>
          )}
        </div>
      </Card>

      {/* Actor & Security Context */}
      <Card title="Actor & Origin Context">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
            <div className="kv-row">
              <span className="kv-key">Actor User ID</span>
              <span className="kv-value font-mono text-xs text-muted">
                {event.actor_user_id || 'SYSTEM / ANONYMOUS'}
              </span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Permission Tested</span>
              <span className="kv-value font-mono text-xs">
                {event.permission || 'NONE / AUTHENTICATION'}
              </span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Source IP</span>
              <span className="kv-value font-mono text-xs text-muted">
                {event.source_ip || 'N/A (Local / Internal)'}
              </span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Actor Session ID</span>
              <span className="kv-value font-mono text-xs text-muted" title={event.actor_session_id || ''}>
                {event.actor_session_id ? `${event.actor_session_id.substring(0, 14)}...` : 'N/A'}
              </span>
            </div>
          </div>

          <div className="kv-row" style={{ marginTop: '2px' }}>
            <span className="kv-key">Correlation ID</span>
            <span className="kv-value font-mono text-xs text-muted" style={{ wordBreak: 'break-all' }}>
              {event.correlation_id}
            </span>
          </div>

          {event.user_agent && (
            <div className="kv-row">
              <span className="kv-key">User-Agent</span>
              <span className="kv-value font-mono text-xs text-muted" style={{ wordBreak: 'break-all' }}>
                {event.user_agent}
              </span>
            </div>
          )}

          {event.actor_user_id && onFilterByActor && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => onFilterByActor(event.actor_user_id!)}
              style={{ marginTop: '6px', width: '100%', padding: '4px 8px', fontSize: '11px' }}
            >
              ⌕ Filter All Events by this Actor ID
            </Button>
          )}
        </div>
      </Card>

      {/* Target Entity Context */}
      {(event.target_type || event.target_id) && (
        <Card title="Target Entity Reference">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
            <div className="kv-row">
              <span className="kv-key">Target Type</span>
              <span className="kv-value font-mono uppercase-tracking">{event.target_type || 'N/A'}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Target ID</span>
              <span className="kv-value font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                {event.target_id || 'N/A'}
              </span>
            </div>
          </div>

          {event.target_type && event.target_id && onFilterByTarget && (
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onFilterByTarget(event.target_type!, event.target_id!)}
              style={{ marginTop: '6px', width: '100%', padding: '4px 8px', fontSize: '11px' }}
            >
              ⌕ Filter Events for Target {event.target_type}:{event.target_id.substring(0, 8)}
            </Button>
          )}
        </Card>
      )}

      {/* Structured Event Metadata */}
      {metadataEntries.length > 0 && (
        <Card title="Structured Event Metadata" badge={<span className="font-mono text-xs text-muted">{metadataEntries.length} KEYS</span>}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)', fontSize: '11px' }}>
            {metadataEntries.map(([k, v]) => (
              <div key={k} className="kv-row">
                <span className="kv-key font-mono">{k}</span>
                <span className="kv-value font-mono" style={{ wordBreak: 'break-all' }}>
                  {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '-')}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Security Immutability & Compliance Notice */}
      <div
        style={{
          padding: '6px 8px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        <p className="font-mono text-muted" style={{ margin: 0, fontSize: '10px', lineHeight: 1.3 }}>
          🔒 Security Audit Log: Events are cryptographically recorded, append-only, and immutable per AeroGuard platform governance specifications.
        </p>
      </div>
    </div>
  );
};
