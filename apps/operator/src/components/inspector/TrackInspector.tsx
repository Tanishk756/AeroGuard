import React from 'react';
import { Alert, Geofence, ThreatAssessment, Track, TrackHistoryPoint } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';

interface TrackInspectorProps {
  track: Track;
  threat?: ThreatAssessment | null;
  relatedAlerts?: Alert[];
  geofences?: Geofence[];
  historyPoints?: TrackHistoryPoint[];
  isHistoryLoading?: boolean;
  onClose?: () => void;
  onSelectAlert?: (alertId: string) => void;
}

export const TrackInspector: React.FC<TrackInspectorProps> = ({
  track,
  threat,
  relatedAlerts = [],
  geofences = [],
  historyPoints = [],
  isHistoryLoading = false,
  onClose,
  onSelectAlert,
}) => {
  // Format staleness / age
  const lastSeenDate = new Date(track.last_seen_at);
  const now = new Date();
  const ageSeconds = Math.max(0, Math.round((now.getTime() - lastSeenDate.getTime()) / 1000));

  const breachedGeofenceIds = (threat?.factors?.breached_geofences as string[]) || [];
  const breachedGeofenceObjects = geofences.filter((g) => breachedGeofenceIds.includes(g.id));

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-accent)', borderRadius: '1px' }} />
          <h3 className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            TRACK: {track.id}
          </h3>
        </div>

        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕ Close
          </Button>
        )}
      </div>

      {/* Identity & Status */}
      <Card title="Identity & Lifecycle">
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
            <span className="kv-key">Confidence</span>
            <span className="kv-value font-mono">{Math.round(track.confidence * 100)}%</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Source Count</span>
            <span className="kv-value font-mono">{track.source_count} sensor(s)</span>
          </div>
        </div>
      </Card>

      {/* Kinematics */}
      <Card title="Kinematics & Positioning">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
          <div className="kv-row">
            <span className="kv-key">Latitude</span>
            <span className="kv-value font-mono">{track.latitude.toFixed(6)}°</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Longitude</span>
            <span className="kv-value font-mono">{track.longitude.toFixed(6)}°</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Altitude</span>
            <span className="kv-value font-mono">{track.altitude != null ? `${track.altitude.toFixed(1)} m` : 'N/A'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Velocity</span>
            <span className="kv-value font-mono">{track.velocity != null ? `${track.velocity.toFixed(1)} m/s` : 'N/A'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Heading</span>
            <span className="kv-value font-mono">{track.heading != null ? `${track.heading.toFixed(1)}°` : 'N/A'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Telemetry Age</span>
            <span className="kv-value font-mono">{ageSeconds}s ago</span>
          </div>
        </div>
      </Card>

      {/* Threat Triage Assessment */}
      <Card
        title="Operational Threat Assessment"
        badge={
          threat ? (
            <StatusBadge status={threat.level} />
          ) : (
            <span className="font-mono text-xs text-muted">UNEVALUATED</span>
          )
        }
      >
        {threat ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            <div className="kv-row">
              <span className="kv-key">Operational Priority</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                <div style={{ width: '60px', height: '6px', backgroundColor: 'var(--bg-canvas)', borderRadius: '3px', overflow: 'hidden' }}>
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
                    }}
                  />
                </div>
                <span className="font-mono text-sm" style={{ fontWeight: 600 }}>{threat.score.toFixed(1)}</span>
              </div>
            </div>

            {threat.factors && (
              <div>
                <div className="uppercase-tracking text-muted" style={{ fontSize: '9px', marginBottom: '4px' }}>
                  Factor Breakdown
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px', fontSize: '11px' }}>
                  {Object.entries(threat.factors).map(([k, v]) => {
                    if (Array.isArray(v)) return null;
                    return (
                      <div key={k} className="font-mono" style={{ color: 'var(--text-secondary)' }}>
                        <span className="text-muted">{k.replace('_factor', '')}: </span>
                        {typeof v === 'number' ? v.toFixed(2) : String(v ?? 'N/A')}
                      </div>
                    );
                  })}
                </div>
              </div>
            )}

            {breachedGeofenceObjects.length > 0 && (
              <div style={{ marginTop: '4px', padding: '4px 6px', backgroundColor: 'var(--status-critical-bg)', border: '1px solid var(--status-critical-border)', borderRadius: 'var(--radius-sm)' }}>
                <span className="font-mono text-xs" style={{ color: '#fca5a5', fontWeight: 600 }}>
                  ⚠ BREACHED GEOFENCE: {breachedGeofenceObjects.map((g) => g.name).join(', ')}
                </span>
              </div>
            )}
          </div>
        ) : (
          <p className="font-mono text-xs text-muted">No elevated threat assessment evaluated for this track.</p>
        )}
      </Card>

      {/* Related Operational Alerts */}
      <Card
        title="Associated Alerts"
        badge={<span className="font-mono text-xs text-muted">{relatedAlerts.length}</span>}
      >
        {relatedAlerts.length === 0 ? (
          <p className="font-mono text-xs text-muted">No open alerts targeting this track.</p>
        ) : (
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
        )}
      </Card>

      {/* Trajectory Points Table */}
      <Card
        title="Trajectory History"
        badge={<span className="font-mono text-xs text-muted">{historyPoints.length} PTS</span>}
        bodyStyle={{ padding: 0 }}
      >
        {isHistoryLoading ? (
          <LoadingState message="Fetching trajectory points..." compact />
        ) : historyPoints.length === 0 ? (
          <p className="font-mono text-xs text-muted" style={{ padding: 'var(--space-sm)' }}>
            No trajectory history points recorded.
          </p>
        ) : (
          <div className="tactical-table-wrapper" style={{ maxHeight: '180px' }}>
            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Seq</th>
                  <th>Time (UTC)</th>
                  <th>Lat / Lon</th>
                  <th>Alt</th>
                  <th>Vel</th>
                </tr>
              </thead>
              <tbody>
                {historyPoints.slice(-10).map((pt) => (
                  <tr key={pt.id || pt.sequence}>
                    <td className="font-mono text-xs">{pt.sequence}</td>
                    <td className="font-mono text-xs text-muted">{pt.timestamp.substring(11, 19)}</td>
                    <td className="font-mono text-xs">{pt.latitude.toFixed(4)}°, {pt.longitude.toFixed(4)}°</td>
                    <td className="font-mono text-xs">{pt.altitude != null ? `${pt.altitude.toFixed(0)}m` : '-'}</td>
                    <td className="font-mono text-xs">{pt.velocity != null ? `${pt.velocity.toFixed(1)}m/s` : '-'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
