import React from 'react';
import { Track } from '../../types';
import { Card } from '../common/Card';

interface MapWorkspaceProps {
  tracks?: Track[];
  selectedTrackId?: string | null;
  onSelectTrack?: (trackId: string) => void;
  centerLat?: number;
  centerLon?: number;
}

export const MapWorkspace: React.FC<MapWorkspaceProps> = ({
  tracks = [],
  selectedTrackId,
  onSelectTrack,
  centerLat = 37.7749,
  centerLon = -122.4194,
}) => {
  return (
    <Card
      title={
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span>Tactical Map View</span>
          <span className="font-mono text-xs text-muted">WGS84 [DATUM]</span>
        </div>
      }
      badge={
        <span
          className="font-mono text-xs"
          style={{
            backgroundColor: 'var(--bg-canvas)',
            padding: '2px 6px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--text-muted)',
          }}
        >
          CTR: {centerLat.toFixed(4)}°, {centerLon.toFixed(4)}°
        </span>
      }
      style={{ height: '100%', minHeight: '340px' }}
      bodyStyle={{ padding: 0, position: 'relative', overflow: 'hidden' }}
    >
      <div
        style={{
          width: '100%',
          height: '100%',
          minHeight: '300px',
          backgroundColor: '#040910',
          position: 'relative',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
        }}
      >
        {/* Coordinate Grid Overlay */}
        <div
          style={{
            position: 'absolute',
            inset: 0,
            backgroundImage: `
              linear-gradient(rgba(56, 189, 248, 0.05) 1px, transparent 1px),
              linear-gradient(90deg, rgba(56, 189, 248, 0.05) 1px, transparent 1px)
            `,
            backgroundSize: '40px 40px',
          }}
        />

        {/* Concentric Range Rings */}
        <div
          style={{
            position: 'absolute',
            width: '140px',
            height: '140px',
            borderRadius: '50%',
            border: '1px dashed rgba(56, 189, 248, 0.25)',
            pointerEvents: 'none',
          }}
        >
          <span
            className="font-mono"
            style={{ position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)', fontSize: '9px', color: 'rgba(56, 189, 248, 0.5)' }}
          >
            500m
          </span>
        </div>

        <div
          style={{
            position: 'absolute',
            width: '260px',
            height: '260px',
            borderRadius: '50%',
            border: '1px dashed rgba(56, 189, 248, 0.2)',
            pointerEvents: 'none',
          }}
        >
          <span
            className="font-mono"
            style={{ position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)', fontSize: '9px', color: 'rgba(56, 189, 248, 0.4)' }}
          >
            1000m
          </span>
        </div>

        <div
          style={{
            position: 'absolute',
            width: '380px',
            height: '380px',
            borderRadius: '50%',
            border: '1px solid rgba(56, 189, 248, 0.12)',
            pointerEvents: 'none',
          }}
        >
          <span
            className="font-mono"
            style={{ position: 'absolute', top: '-14px', left: '50%', transform: 'translateX(-50%)', fontSize: '9px', color: 'rgba(56, 189, 248, 0.3)' }}
          >
            2000m
          </span>
        </div>

        {/* Center Reticle */}
        <div
          style={{
            position: 'absolute',
            width: '12px',
            height: '12px',
            border: '1px solid var(--color-accent)',
            borderRadius: '50%',
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            width: '1px',
            height: '24px',
            backgroundColor: 'rgba(56, 189, 248, 0.4)',
            pointerEvents: 'none',
          }}
        />
        <div
          style={{
            position: 'absolute',
            height: '1px',
            width: '24px',
            backgroundColor: 'rgba(56, 189, 248, 0.4)',
            pointerEvents: 'none',
          }}
        />

        {/* Rendered Track Markers */}
        {tracks.map((track, idx) => {
          const isSelected = track.id === selectedTrackId;
          // Normalize pseudo-display offset for tactical map surface placeholder
          const offsetX = ((track.longitude - centerLon) * 8000) || (idx % 2 === 0 ? 40 * (idx + 1) : -40 * (idx + 1));
          const offsetY = (-(track.latitude - centerLat) * 8000) || (idx % 2 === 0 ? -30 * (idx + 1) : 30 * (idx + 1));

          return (
            <div
              key={track.id}
              onClick={() => onSelectTrack?.(track.id)}
              style={{
                position: 'absolute',
                transform: `translate(${offsetX}px, ${offsetY}px)`,
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'center',
                cursor: 'pointer',
                zIndex: isSelected ? 20 : 10,
              }}
              title={`Track ${track.id} [${track.classification}] - Alt: ${track.altitude ?? 'N/A'}m`}
            >
              <div
                style={{
                  width: isSelected ? '14px' : '10px',
                  height: isSelected ? '14px' : '10px',
                  border: isSelected ? '2px solid #38bdf8' : '1px solid #ef4444',
                  backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.3)' : 'rgba(239, 68, 68, 0.3)',
                  transform: 'rotate(45deg)',
                  boxShadow: isSelected ? '0 0 8px rgba(56, 189, 248, 0.8)' : 'none',
                }}
              />
              <span
                className="font-mono"
                style={{
                  fontSize: '9px',
                  color: isSelected ? 'var(--color-accent)' : 'var(--text-secondary)',
                  backgroundColor: 'rgba(6, 13, 21, 0.85)',
                  padding: '1px 3px',
                  borderRadius: '2px',
                  marginTop: '4px',
                  border: '1px solid var(--border-subtle)',
                  whiteSpace: 'nowrap',
                }}
              >
                {track.id}
              </span>
            </div>
          );
        })}

        {/* North Indicator */}
        <div
          className="font-mono"
          style={{
            position: 'absolute',
            top: '12px',
            right: '12px',
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            backgroundColor: 'rgba(11, 23, 36, 0.75)',
            border: '1px solid var(--border-medium)',
            padding: '4px 6px',
            borderRadius: 'var(--radius-sm)',
            fontSize: '10px',
            color: 'var(--color-accent)',
          }}
        >
          <span style={{ fontSize: '12px' }}>▲</span>
          <span>N</span>
        </div>

        {/* Tactical Map Notice */}
        <div
          className="font-mono text-xs"
          style={{
            position: 'absolute',
            bottom: '8px',
            left: '12px',
            color: 'var(--text-muted)',
            backgroundColor: 'rgba(6, 13, 21, 0.8)',
            padding: '2px 6px',
            borderRadius: '2px',
            fontSize: '10px',
          }}
        >
          TACTICAL MAP FOUNDATION • GIS TILES DEFERRED (UI2)
        </div>
      </div>
    </Card>
  );
};
