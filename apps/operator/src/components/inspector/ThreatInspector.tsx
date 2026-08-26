import React from 'react';
import { Alert, Geofence, ThreatAssessment, Track } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';

interface ThreatInspectorProps {
  threat: ThreatAssessment;
  track?: Track | null;
  relatedAlerts?: Alert[];
  geofences?: Geofence[];
  onClose?: () => void;
  onSelectTrack?: (trackId: string) => void;
  onSelectAlert?: (alertId: string) => void;
}

export const ThreatInspector: React.FC<ThreatInspectorProps> = ({
  threat,
  track,
  relatedAlerts = [],
  geofences = [],
  onClose,
  onSelectTrack,
  onSelectAlert,
}) => {
  const breachedGeofenceIds = (threat.factors?.breached_geofences as string[]) || [];
  const breachedGeofences = geofences.filter((g) => breachedGeofenceIds.includes(g.id));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--status-warning)', borderRadius: '1px' }} />
          <h3 className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            THREAT TRIAGE: {threat.track_id}
          </h3>
        </div>

        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕ Close
          </Button>
        )}
      </div>

      {/* Operational Priority Score & Level */}
      <Card
        title="Operational Priority / Triage"
        badge={<StatusBadge status={threat.level} />}
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="text-muted text-xs uppercase-tracking">Triage Score</span>
            <div style={{ display: 'flex', alignItems: 'baseline', gap: '4px' }}>
              <span className="font-mono" style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--color-accent)' }}>
                {threat.score.toFixed(1)}
              </span>
              <span className="text-muted font-mono text-xs">/ 100.0</span>
            </div>
          </div>

          {/* Score Meter Bar */}
          <div style={{ width: '100%', height: '8px', backgroundColor: 'var(--bg-canvas)', borderRadius: '4px', overflow: 'hidden' }}>
            <div
              style={{
                width: `${Math.min(100, Math.max(0, threat.score))}%`,
                height: '100%',
                backgroundColor:
                  threat.score >= 75
                    ? 'var(--status-critical)'
                    : threat.score >= 50
                    ? 'var(--status-warning)'
                    : 'var(--status-info)',
                transition: 'width var(--transition-normal)',
              }}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)', marginTop: '4px' }}>
            <div className="kv-row">
              <span className="kv-key">Threat Level</span>
              <span className="kv-value font-mono">{threat.level}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Target Track</span>
              <span className="kv-value font-mono">{threat.track_id}</span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Evaluated (UTC)</span>
              <span className="kv-value font-mono text-xs text-muted">
                {threat.updated_at ? threat.updated_at.substring(0, 19).replace('T', ' ') : 'N/A'}
              </span>
            </div>
            <div className="kv-row">
              <span className="kv-key">Assessment ID</span>
              <span className="kv-value font-mono text-xs text-muted" title={threat.id}>
                {threat.id.length > 16 ? `${threat.id.substring(0, 16)}...` : threat.id}
              </span>
            </div>
          </div>
        </div>
      </Card>

      {/* Threat Factors Breakdown */}
      {threat.factors && (
        <Card title="Threat Factor Contributions">
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)', fontSize: '11px' }}>
            {Object.entries(threat.factors).map(([k, v]) => {
              if (Array.isArray(v)) return null;
              return (
                <div key={k} className="kv-row">
                  <span className="kv-key font-mono">{k.replace('_factor', '').replace('_', ' ')}</span>
                  <span className="kv-value font-mono" style={{ fontWeight: 600 }}>
                    {typeof v === 'number' ? v.toFixed(3) : String(v ?? '-')}
                  </span>
                </div>
              );
            })}
          </div>

          {breachedGeofences.length > 0 && (
            <div
              style={{
                marginTop: 'var(--space-sm)',
                padding: '6px 8px',
                backgroundColor: 'var(--status-critical-bg)',
                border: '1px solid var(--status-critical-border)',
                borderRadius: 'var(--radius-sm)',
              }}
            >
              <div className="font-mono text-xs" style={{ color: '#fca5a5', fontWeight: 600 }}>
                ⚠ GEOFENCE BOUNDARY BREACH:
              </div>
              <div className="font-mono text-xs" style={{ color: 'var(--text-primary)', marginTop: '2px' }}>
                {breachedGeofences.map((g) => g.name).join(', ')}
              </div>
            </div>
          )}
        </Card>
      )}

      {/* Target Track Quick Inspection */}
      <Card title="Target Track Status">
        {track ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
              <div className="kv-row">
                <span className="kv-key">State</span>
                <StatusBadge status={track.state} />
              </div>
              <div className="kv-row">
                <span className="kv-key">Classification</span>
                <span className="kv-value uppercase-tracking">{track.classification || 'N/A'}</span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Coordinates</span>
                <span className="kv-value font-mono text-xs">
                  {track.latitude.toFixed(4)}°, {track.longitude.toFixed(4)}°
                </span>
              </div>
              <div className="kv-row">
                <span className="kv-key">Velocity</span>
                <span className="kv-value font-mono text-xs">
                  {track.velocity != null ? `${track.velocity.toFixed(1)} m/s` : 'N/A'}
                </span>
              </div>
            </div>

            <Button
              variant="secondary"
              size="sm"
              onClick={() => onSelectTrack?.(threat.track_id)}
              style={{ marginTop: '4px', width: '100%', padding: '4px 8px', fontSize: '11px' }}
            >
              ⌖ Inspect Full Kinematics & Trajectory
            </Button>
          </div>
        ) : (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
            <span className="font-mono text-xs text-muted">Track ID: {threat.track_id}</span>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => onSelectTrack?.(threat.track_id)}
              style={{ padding: '2px 6px', fontSize: '11px' }}
            >
              Select Track
            </Button>
          </div>
        )}
      </Card>

      {/* Related Operational Alerts */}
      {relatedAlerts.length > 0 && (
        <Card title="Associated Operational Alerts" badge={<span className="font-mono text-xs text-muted">{relatedAlerts.length}</span>}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {relatedAlerts.map((a) => (
              <div
                key={a.id}
                onClick={() => onSelectAlert?.(a.id)}
                style={{
                  padding: '4px 6px',
                  backgroundColor: 'var(--bg-canvas)',
                  border: '1px solid var(--border-subtle)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  cursor: 'pointer',
                  fontSize: '11px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <StatusBadge status={a.severity} />
                  <span className="font-mono">{a.type}</span>
                </div>
                <span className="text-muted font-mono text-xs">{a.created_at.substring(11, 19)}</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      {/* Counter-UAS Research Scope Boundary Disclaimer */}
      <div
        style={{
          padding: '6px 8px',
          backgroundColor: 'var(--bg-surface)',
          border: '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        <p className="font-mono text-muted" style={{ margin: 0, fontSize: '10px', lineHeight: 1.3 }}>
          ℹ Operational Priority / Triage score indicates defensive monitoring priority based on kinematics, proximity, and boundary conditions. It is NOT an estimate of hostile intent.
        </p>
      </div>
    </div>
  );
};
