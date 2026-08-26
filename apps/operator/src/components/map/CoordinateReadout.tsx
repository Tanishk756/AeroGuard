import React from 'react';

interface CoordinateReadoutProps {
  centerLat: number;
  centerLon: number;
  zoom: number;
  cursorLatLon?: { lat: number; lon: number } | null;
}

export const CoordinateReadout: React.FC<CoordinateReadoutProps> = ({
  centerLat,
  centerLon,
  zoom,
  cursorLatLon,
}) => {
  return (
    <div
      className="font-mono"
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-md)',
        fontSize: '11px',
        backgroundColor: 'rgba(6, 13, 21, 0.85)',
        border: '1px solid var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        padding: '3px 8px',
        color: 'var(--text-secondary)',
        backdropFilter: 'blur(4px)',
        userSelect: 'none',
      }}
    >
      <div>
        <span className="text-muted">CTR: </span>
        <span style={{ color: 'var(--color-accent)' }}>
          {centerLat >= 0 ? `${centerLat.toFixed(4)}°N` : `${Math.abs(centerLat).toFixed(4)}°S`},{' '}
          {centerLon >= 0 ? `${centerLon.toFixed(4)}°E` : `${Math.abs(centerLon).toFixed(4)}°W`}
        </span>
      </div>

      {cursorLatLon && (
        <div style={{ borderLeft: '1px solid var(--border-medium)', paddingLeft: '8px' }}>
          <span className="text-muted">CUR: </span>
          <span>
            {cursorLatLon.lat >= 0 ? `${cursorLatLon.lat.toFixed(4)}°N` : `${Math.abs(cursorLatLon.lat).toFixed(4)}°S`},{' '}
            {cursorLatLon.lon >= 0 ? `${cursorLatLon.lon.toFixed(4)}°E` : `${Math.abs(cursorLatLon.lon).toFixed(4)}°W`}
          </span>
        </div>
      )}

      <div style={{ borderLeft: '1px solid var(--border-medium)', paddingLeft: '8px' }}>
        <span className="text-muted">ZOOM: </span>
        <span style={{ color: 'var(--text-primary)' }}>{zoom.toFixed(2)}x</span>
      </div>

      <div style={{ borderLeft: '1px solid var(--border-medium)', paddingLeft: '8px', color: 'var(--text-muted)' }}>
        WGS84 [DATUM]
      </div>
    </div>
  );
};
