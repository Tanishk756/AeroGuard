import React from 'react';
import { Alert } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';

interface AlertInspectorProps {
  alert: Alert;
  onClose?: () => void;
  onSelectTrack?: (trackId: string) => void;
  onSelectSensor?: (sensorId: string) => void;
}

export const AlertInspector: React.FC<AlertInspectorProps> = ({
  alert,
  onClose,
  onSelectTrack,
  onSelectSensor,
}) => {
  const metadataEntries = alert.metadata
    ? Object.entries(alert.metadata)
    : [];

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--status-critical)', borderRadius: '1px' }} />
          <h3 className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            ALERT: {alert.type}
          </h3>
        </div>

        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕ Close
          </Button>
        )}
      </div>

      {/* Alert Severity & Status */}
      <Card title="Alert Classification & Lifecycle">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
          <div className="kv-row">
            <span className="kv-key">Severity</span>
            <StatusBadge status={alert.severity} />
          </div>
          <div className="kv-row">
            <span className="kv-key">Status</span>
            <StatusBadge status={alert.status} />
          </div>
          <div className="kv-row">
            <span className="kv-key">Alert Type</span>
            <span className="kv-value font-mono">{alert.type}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Alert ID</span>
            <span className="kv-value font-mono text-xs text-muted" title={alert.id}>
              {alert.id.length > 18 ? `${alert.id.substring(0, 18)}...` : alert.id}
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Generated (UTC)</span>
            <span className="kv-value font-mono text-xs text-muted">
              {alert.created_at.substring(0, 19).replace('T', ' ')}
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Resolved (UTC)</span>
            <span className="kv-value font-mono text-xs text-muted">
              {alert.resolved_at ? alert.resolved_at.substring(0, 19).replace('T', ' ') : 'ACTIVE (UNRESOLVED)'}
            </span>
          </div>
        </div>
      </Card>

      {/* Reason Description */}
      <Card title="Rule Evaluation Description">
        <div
          style={{
            padding: '8px',
            backgroundColor: 'var(--bg-canvas)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            color: 'var(--text-primary)',
            fontSize: 'var(--text-sm)',
            lineHeight: 1.4,
          }}
        >
          {alert.reason || 'No description provided by rule evaluation engine.'}
        </div>
      </Card>

      {/* Entity References & Navigation Links */}
      <Card title="Associated Operational Targets">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
          {alert.track_id ? (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 8px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span className="text-muted text-xs uppercase-tracking">Target Track ID</span>
                <span className="font-mono" style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
                  {alert.track_id}
                </span>
              </div>
              <Button
                variant="secondary"
                size="sm"
                onClick={() => onSelectTrack?.(alert.track_id!)}
                style={{ padding: '3px 8px', fontSize: '11px' }}
              >
                ⌖ Lock Track on Map
              </Button>
            </div>
          ) : (
            <div className="text-muted font-mono text-xs">No track referenced in this alert.</div>
          )}

          {alert.sensor_id && (
            <div
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                padding: '6px 8px',
                backgroundColor: 'var(--bg-canvas)',
                border: '1px solid var(--border-subtle)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span className="text-muted text-xs uppercase-tracking">Source Sensor ID</span>
                <span className="font-mono text-xs">{alert.sensor_id}</span>
              </div>
              <Button
                variant="ghost"
                size="sm"
                onClick={() => onSelectSensor?.(alert.sensor_id!)}
                style={{ padding: '3px 8px', fontSize: '11px' }}
              >
                ⋉ Inspect Sensor
              </Button>
            </div>
          )}
        </div>
      </Card>

      {/* Rule Metadata */}
      {metadataEntries.length > 0 && (
        <Card title="Rule Context Metadata" badge={<span className="font-mono text-xs text-muted">{metadataEntries.length} KEYS</span>}>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)', fontSize: '11px' }}>
            {metadataEntries.map(([k, v]) => (
              <div key={k} className="kv-row">
                <span className="kv-key font-mono">{k}</span>
                <span className="kv-value font-mono">
                  {typeof v === 'object' ? JSON.stringify(v) : String(v ?? '-')}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Defensive Boundary Integrity Notice */}
      <div
        style={{
          padding: '6px 8px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        <p className="font-mono text-muted" style={{ margin: 0, fontSize: '10px', lineHeight: 1.3 }}>
          ℹ Operational alerts are evaluated deterministically by backend rules and persisted immutably in the operational audit log.
        </p>
      </div>
    </div>
  );
};
