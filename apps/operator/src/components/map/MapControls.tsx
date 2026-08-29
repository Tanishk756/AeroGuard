import React, { useState } from 'react';
import { MapLayerVisibility } from '../../types';
import { Button } from '../common/Button';

interface MapControlsProps {
  onZoomIn: () => void;
  onZoomOut: () => void;
  onResetView: () => void;
  onFitBounds: () => void;
  layers: MapLayerVisibility;
  onToggleLayer: (layerName: keyof MapLayerVisibility) => void;
}

export const MapControls: React.FC<MapControlsProps> = ({
  onZoomIn,
  onZoomOut,
  onResetView,
  onFitBounds,
  layers,
  onToggleLayer,
}) => {
  const [showLayerMenu, setShowLayerMenu] = useState<boolean>(false);

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: '6px',
        backgroundColor: 'rgba(6, 13, 21, 0.85)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        padding: '3px 6px',
        backdropFilter: 'blur(4px)',
        position: 'relative',
        userSelect: 'none',
      }}
    >
      <Button
        variant="ghost"
        size="sm"
        onClick={onZoomIn}
        title="Zoom In (+)"
        style={{ padding: '3px 8px', fontSize: '12px' }}
      >
        +
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={onZoomOut}
        title="Zoom Out (-)"
        style={{ padding: '3px 8px', fontSize: '12px' }}
      >
        -
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={onFitBounds}
        title="Fit Map to All Visible Operational Data"
        style={{ padding: '3px 8px', fontSize: '11px' }}
      >
        Fit All
      </Button>

      <Button
        variant="ghost"
        size="sm"
        onClick={onResetView}
        title="Reset Map Center and Zoom"
        style={{ padding: '3px 8px', fontSize: '11px' }}
      >
        Reset
      </Button>

      <div style={{ position: 'relative' }}>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowLayerMenu((prev) => !prev)}
          title="Toggle Map Overlays and Layers"
          style={{ padding: '3px 8px', fontSize: '11px', display: 'flex', alignItems: 'center', gap: '4px' }}
        >
          <span>Layers</span>
          <span style={{ fontSize: '9px' }}>{showLayerMenu ? '▲' : '▼'}</span>
        </Button>

        {showLayerMenu && (
          <div
            style={{
              position: 'absolute',
              top: '100%',
              right: 0,
              marginTop: '4px',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-sm)',
              padding: 'var(--space-xs) var(--space-sm)',
              boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)',
              zIndex: 100,
              minWidth: '150px',
              display: 'flex',
              flexDirection: 'column',
              gap: '4px',
            }}
          >
            <div className="uppercase-tracking text-muted" style={{ fontSize: '9px', marginBottom: '2px' }}>
              Map Layers
            </div>

            {(
              [
                ['tracks', 'Tracks'],
                ['incidents', 'Incidents'],
                ['sensors', 'Sensors'],
                ['geofences', 'Geofences'],
                ['trajectories', 'Trajectories'],
                ['rangeRings', 'Range Rings'],
                ['grid', 'Coordinate Grid'],
                ['labels', 'Labels'],
              ] as [keyof MapLayerVisibility, string][]
            ).map(([key, label]) => (
              <label
                key={key}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  gap: '6px',
                  fontSize: '11px',
                  color: layers[key] !== false ? 'var(--text-primary)' : 'var(--text-muted)',
                  cursor: 'pointer',
                }}
              >
                <input
                  type="checkbox"
                  checked={layers[key] !== false}
                  onChange={() => onToggleLayer(key)}
                  style={{ cursor: 'pointer', accentColor: 'var(--color-accent)' }}
                />
                <span>{label}</span>
              </label>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};
