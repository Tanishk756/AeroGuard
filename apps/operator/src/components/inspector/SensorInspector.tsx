import React from 'react';
import { Sensor } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';

interface SensorInspectorProps {
  sensor: Sensor;
  onClose?: () => void;
}

export const SensorInspector: React.FC<SensorInspectorProps> = ({ sensor, onClose }) => {
  const meta = sensor.configuration_metadata;
  const lat = typeof meta?.latitude === 'number' ? meta.latitude : null;
  const lon = typeof meta?.longitude === 'number' ? meta.longitude : null;
  const alt = typeof meta?.altitude === 'number' ? meta.altitude : null;
  const range = typeof meta?.range_meters === 'number' ? meta.range_meters : null;
  const detProb = typeof meta?.detection_probability === 'number' ? meta.detection_probability : null;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-accent)', borderRadius: '1px' }} />
          <h3 className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
            SENSOR: {sensor.name}
          </h3>
        </div>

        {onClose && (
          <Button variant="ghost" size="sm" onClick={onClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕ Close
          </Button>
        )}
      </div>

      {/* Identity & Status */}
      <Card title="Sensor Specification">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
          <div className="kv-row">
            <span className="kv-key">Status</span>
            <StatusBadge status={sensor.status} />
          </div>
          <div className="kv-row">
            <span className="kv-key">Source Class</span>
            <StatusBadge status={sensor.source_class} />
          </div>
          <div className="kv-row">
            <span className="kv-key">Modality</span>
            <span className="kv-value font-mono uppercase-tracking" style={{ color: 'var(--color-accent)' }}>
              {sensor.source_type}
            </span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Config Version</span>
            <span className="kv-value font-mono">v{sensor.configuration_version}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Sensor ID</span>
            <span className="kv-value font-mono text-xs text-muted">{sensor.id}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Registered</span>
            <span className="kv-value font-mono text-xs text-muted">{sensor.created_at.substring(0, 10)}</span>
          </div>
        </div>
      </Card>

      {/* Location & Coverage Parameters */}
      <Card title="Geographic & Coverage Parameters">
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
          <div className="kv-row">
            <span className="kv-key">Latitude</span>
            <span className="kv-value font-mono">{lat !== null ? `${lat.toFixed(6)}°` : 'Stationary / Unset'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Longitude</span>
            <span className="kv-value font-mono">{lon !== null ? `${lon.toFixed(6)}°` : 'Stationary / Unset'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Altitude</span>
            <span className="kv-value font-mono">{alt !== null ? `${alt.toFixed(1)} m` : 'N/A'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Range Radius</span>
            <span className="kv-value font-mono">{range !== null ? `${range.toLocaleString()} m` : 'N/A'}</span>
          </div>
          <div className="kv-row">
            <span className="kv-key">Detection Prob</span>
            <span className="kv-value font-mono">{detProb !== null ? `${Math.round(detProb * 100)}%` : 'N/A'}</span>
          </div>
        </div>
      </Card>
    </div>
  );
};
