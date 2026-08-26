import React from 'react';
import { Geofence, Track } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';

interface GeofenceInspectorProps {
  geofence: Geofence;
  containedTracks?: Track[];
  onClose?: () => void;
  onSelectTrack?: (trackId: string) => void;
}

export const GeofenceInspector: React.FC<GeofenceInspectorProps> = ({
  geofence,
  containedTracks = [],
  onClose,
  onSelectTrack,
}) => {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', backgroundColor: '#f59e0b', borderRadius: '1px' }} />
          <h3 className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            GEOFENCE: {geofence.name}
          </h3>
        </div>

        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕ Close
          </Button>
        )}
      </div>

      {/* Boundary Specification */}
      <Card title="Geofence Boundary Details">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
          <div className="kv-row">
            <span className="kv-key">Status</span>
            <StatusBadge status={geofence.enabled ? 'ACTIVE' : 'INACTIVE'} label={geofence.enabled ? 'ENABLED' : 'DISABLED'} />
          </div>
          <div className="kv-row">
            <span className="kv-key">Geometry Type</span>
            <span className="kv-value font-mono uppercase-tracking">{geofence.geometry.type}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Min Altitude</span>
            <span className="kv-value font-mono">{geofence.min_altitude != null ? `${geofence.min_altitude} m` : 'Surface (0m)'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Max Altitude</span>
            <span className="kv-value font-mono">{geofence.max_altitude != null ? `${geofence.max_altitude} m` : 'Unlimited'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Geofence ID</span>
            <span className="kv-value font-mono text-xs text-muted">{geofence.id}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Last Updated</span>
            <span className="kv-value font-mono text-xs text-muted">{geofence.updated_at.substring(0, 10)}</span>
          </div>
        </div>
      </Card>

      {/* Geometry Coordinates */}
      <Card title="Coordinate Bounds">
        {geofence.geometry.type === 'bbox' ? (
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '4px', fontSize: '11px' }}>
            <div className="font-mono text-muted">Min Lat: <span style={{ color: 'var(--text-primary)' }}>{geofence.geometry.min_lat.toFixed(4)}°</span></div>
            <div className="font-mono text-muted">Max Lat: <span style={{ color: 'var(--text-primary)' }}>{geofence.geometry.max_lat.toFixed(4)}°</span></div>
            <div className="font-mono text-muted">Min Lon: <span style={{ color: 'var(--text-primary)' }}>{geofence.geometry.min_lon.toFixed(4)}°</span></div>
            <div className="font-mono text-muted">Max Lon: <span style={{ color: 'var(--text-primary)' }}>{geofence.geometry.max_lon.toFixed(4)}°</span></div>
          </div>
        ) : (
          <div style={{ maxHeight: '120px', overflowY: 'auto' }}>
            <div className="font-mono text-xs text-muted" style={{ marginBottom: '4px' }}>
              Vertices: {geofence.geometry.coordinates?.length || 0} Points
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
              {geofence.geometry.coordinates?.map(([lat, lon], idx) => (
                <div key={idx} className="font-mono text-xs" style={{ color: 'var(--text-secondary)' }}>
                  P{idx + 1}: {lat.toFixed(4)}°, {lon.toFixed(4)}°
                </div>
              ))}
            </div>
          </div>
        )}
      </Card>

      {/* Contained / Breaching Tracks */}
      {containedTracks.length > 0 && (
        <Card title="Tracks in Geofence Zone" badge={<span className="font-mono text-xs">{containedTracks.length}</span>}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            {containedTracks.map((t) => (
              <div
                key={t.id}
                onClick={() => onSelectTrack?.(t.id)}
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
                  <StatusBadge status={t.state} />
                  <span className="font-mono">{t.id}</span>
                </div>
                <span className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                  {t.classification}
                </span>
              </div>
            ))}
          </div>
        </Card>
      )}
    </div>
  );
};
