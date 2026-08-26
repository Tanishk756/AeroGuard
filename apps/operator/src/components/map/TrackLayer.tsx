import React from 'react';
import { Track } from '../../types';

interface TrackLayerProps {
  tracks: Track[];
  selectedTrackId?: string | null;
  onSelectTrack?: (trackId: string) => void;
  latLonToScreen: (lat: number, lon: number) => { x: number; y: number };
  showLabels?: boolean;
}

export const TrackLayer: React.FC<TrackLayerProps> = ({
  tracks,
  selectedTrackId,
  onSelectTrack,
  latLonToScreen,
  showLabels = true,
}) => {
  const getTrackColor = (state: string) => {
    switch (state) {
      case 'ACTIVE':
        return '#22c55e'; // Green
      case 'STALE':
        return '#f59e0b'; // Amber
      case 'LOST':
        return '#ef4444'; // Red
      case 'NEW':
        return '#38bdf8'; // Cyan
      case 'ARCHIVED':
      default:
        return '#64748b'; // Slate
    }
  };

  return (
    <g className="track-layer">
      {tracks.map((t) => {
        const { x, y } = latLonToScreen(t.latitude, t.longitude);
        const isSelected = t.id === selectedTrackId;
        const color = getTrackColor(t.state);

        // Heading vector math (0 deg North = negative Y, 90 deg East = positive X)
        let vectorEndX = x;
        let vectorEndY = y;
        const hasHeading = t.heading != null;
        if (hasHeading) {
          const rad = ((t.heading! - 90) * Math.PI) / 180;
          const speedFactor = Math.min(Math.max((t.velocity || 15) * 0.8, 14), 45);
          vectorEndX = x + Math.cos(rad) * speedFactor;
          vectorEndY = y + Math.sin(rad) * speedFactor;
        }

        return (
          <g
            key={t.id}
            onClick={(e) => {
              e.stopPropagation();
              onSelectTrack?.(t.id);
            }}
            style={{ cursor: 'pointer' }}
            tabIndex={0}
            role="button"
            aria-label={`Track ${t.id}, State: ${t.state}`}
          >
            {/* Heading Vector */}
            {hasHeading && (
              <line
                x1={x}
                y1={y}
                x2={vectorEndX}
                y2={vectorEndY}
                stroke={color}
                strokeWidth={isSelected ? '2.5' : '1.5'}
                strokeDasharray={t.state === 'STALE' ? '2 2' : undefined}
                opacity={0.85}
              />
            )}

            {/* Selected Track Lock Reticle */}
            {isSelected && (
              <g>
                <circle
                  cx={x}
                  cy={y}
                  r={16}
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeWidth="1.5"
                  strokeDasharray="4 3"
                  opacity={0.9}
                />
                <circle
                  cx={x}
                  cy={y}
                  r={22}
                  fill="none"
                  stroke="var(--color-accent)"
                  strokeWidth="1"
                  strokeDasharray="1 5"
                  opacity={0.5}
                />
                {/* Crosshairs */}
                <line x1={x - 24} y1={y} x2={x - 18} y2={y} stroke="var(--color-accent)" strokeWidth="1.5" />
                <line x1={x + 18} y1={y} x2={x + 24} y2={y} stroke="var(--color-accent)" strokeWidth="1.5" />
                <line x1={x} y1={y - 24} x2={x} y2={y - 18} stroke="var(--color-accent)" strokeWidth="1.5" />
                <line x1={x} y1={y + 18} x2={x} y2={y + 24} stroke="var(--color-accent)" strokeWidth="1.5" />
              </g>
            )}

            {/* Track Core Diamond */}
            <rect
              x={x - 6}
              y={y - 6}
              width={12}
              height={12}
              fill={isSelected ? color : 'rgba(6, 13, 21, 0.9)'}
              stroke={color}
              strokeWidth={isSelected ? 2.5 : 1.8}
              transform={`rotate(45, ${x}, ${y})`}
            />

            {/* Micro Center Node */}
            <circle cx={x} cy={y} r={2} fill={isSelected ? '#ffffff' : color} />

            {/* Track Label Tag */}
            {showLabels && (
              <g transform={`translate(${x + 12}, ${y - 8})`}>
                <rect
                  x={-2}
                  y={-10}
                  width={t.id.length * 6.5 + 4}
                  height={13}
                  fill="rgba(6, 13, 21, 0.88)"
                  stroke={isSelected ? 'var(--color-accent)' : 'var(--border-subtle)'}
                  strokeWidth="0.8"
                  rx="2"
                />
                <text
                  x={0}
                  y={0}
                  fill={isSelected ? 'var(--color-accent)' : 'var(--text-primary)'}
                  fontSize="9px"
                  fontFamily="monospace"
                  fontWeight={isSelected ? 'bold' : 'normal'}
                >
                  {t.id}
                </text>

                {/* Subtag: Classification + Alt */}
                <text
                  x={0}
                  y={10}
                  fill="var(--text-muted)"
                  fontSize="8px"
                  fontFamily="monospace"
                >
                  {t.classification || 'UAS'}
                  {t.altitude != null ? ` • ${t.altitude.toFixed(0)}m` : ''}
                </text>
              </g>
            )}
          </g>
        );
      })}
    </g>
  );
};
