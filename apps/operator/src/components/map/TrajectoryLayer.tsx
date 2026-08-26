import React from 'react';
import { TrackHistoryPoint } from '../../types';

interface TrajectoryLayerProps {
  historyPoints: TrackHistoryPoint[];
  latLonToScreen: (lat: number, lon: number) => { x: number; y: number };
}

export const TrajectoryLayer: React.FC<TrajectoryLayerProps> = ({
  historyPoints,
  latLonToScreen,
}) => {
  if (historyPoints.length < 2) return null;

  // Convert points to screen coordinates
  const screenPoints = historyPoints.map((pt) => {
    const { x, y } = latLonToScreen(pt.latitude, pt.longitude);
    return { ...pt, screenX: x, screenY: y };
  });

  const polylinePoints = screenPoints.map((p) => `${p.screenX},${p.screenY}`).join(' ');

  return (
    <g className="trajectory-layer">
      {/* Historical Track Path Polyline */}
      <polyline
        points={polylinePoints}
        fill="none"
        stroke="var(--color-accent)"
        strokeWidth="1.5"
        strokeDasharray="3 3"
        opacity={0.65}
      />

      {/* Historical Breadcrumb Nodes */}
      {screenPoints.map((p, idx) => (
        <g key={p.id || `${p.sequence}-${idx}`}>
          <circle
            cx={p.screenX}
            cy={p.screenY}
            r={2.5}
            fill="var(--bg-canvas)"
            stroke="var(--color-accent)"
            strokeWidth="1"
            opacity={0.75}
          />
        </g>
      ))}
    </g>
  );
};
