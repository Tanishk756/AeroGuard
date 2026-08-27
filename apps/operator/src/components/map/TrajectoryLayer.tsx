import React from 'react';
import { TrackHistoryPoint, TrajectoryPrediction } from '../../types';

interface TrajectoryLayerProps {
  historyPoints: TrackHistoryPoint[];
  prediction?: TrajectoryPrediction | null;
  latLonToScreen: (lat: number, lon: number) => { x: number; y: number };
}

export const TrajectoryLayer: React.FC<TrajectoryLayerProps> = ({
  historyPoints,
  prediction,
  latLonToScreen,
}) => {
  const hasHistory = historyPoints.length >= 2;
  const hasPrediction = prediction && prediction.waypoints && prediction.waypoints.length > 0;

  if (!hasHistory && !hasPrediction) return null;

  // Convert historical points to screen coordinates
  const screenHistoryPoints = historyPoints.map((pt) => {
    const { x, y } = latLonToScreen(pt.latitude, pt.longitude);
    return { ...pt, screenX: x, screenY: y };
  });

  const historyPolyline = screenHistoryPoints.map((p) => `${p.screenX},${p.screenY}`).join(' ');

  // Convert predicted points to screen coordinates
  const screenPredictionPoints = (prediction?.waypoints || []).map((wp) => {
    const { x, y } = latLonToScreen(wp.latitude, wp.longitude);
    return { ...wp, screenX: x, screenY: y };
  });

  const predictionPolyline = screenPredictionPoints.map((p) => `${p.screenX},${p.screenY}`).join(' ');

  return (
    <g className="trajectory-layer">
      {/* Historical Track Path Polyline */}
      {hasHistory && (
        <>
          <polyline
            points={historyPolyline}
            fill="none"
            stroke="var(--color-accent)"
            strokeWidth="1.5"
            strokeDasharray="3 3"
            opacity={0.65}
          />
          {screenHistoryPoints.map((p, idx) => (
            <circle
              key={p.id || `${p.sequence}-${idx}`}
              cx={p.screenX}
              cy={p.screenY}
              r={2.5}
              fill="var(--bg-canvas)"
              stroke="var(--color-accent)"
              strokeWidth="1"
              opacity={0.75}
            />
          ))}
        </>
      )}

      {/* Forward Projected Trajectory Vector */}
      {hasPrediction && (
        <g className="predicted-trajectory">
          {/* Projected flight line */}
          <polyline
            points={predictionPolyline}
            fill="none"
            stroke="#38bdf8"
            strokeWidth="2"
            strokeDasharray="4 2"
            opacity={0.85}
          />

          {/* Predicted Waypoint Nodes with Uncertainty Envelopes */}
          {screenPredictionPoints.map((wp, idx) => {
            const isKeyNode = idx === Math.floor(screenPredictionPoints.length / 2) || idx === screenPredictionPoints.length - 1;
            return (
              <g key={`pred-${wp.time_offset_seconds}-${idx}`}>
                {/* Uncertainty ring */}
                <circle
                  cx={wp.screenX}
                  cy={wp.screenY}
                  r={Math.max(4, Math.min(25, wp.uncertainty_radius_meters * 0.15))}
                  fill="#38bdf8"
                  fillOpacity={0.08}
                  stroke="#38bdf8"
                  strokeWidth="1"
                  strokeDasharray="2 2"
                  opacity={0.5}
                />
                {/* Center dot */}
                <circle
                  cx={wp.screenX}
                  cy={wp.screenY}
                  r={isKeyNode ? 3.5 : 2}
                  fill="#38bdf8"
                  stroke="var(--bg-canvas)"
                  strokeWidth="1"
                />
                {/* Time marker label */}
                {isKeyNode && (
                  <text
                    x={wp.screenX + 6}
                    y={wp.screenY - 4}
                    fill="#38bdf8"
                    fontSize="9px"
                    fontFamily="monospace"
                    fontWeight={600}
                  >
                    +{wp.time_offset_seconds}s
                  </text>
                )}
              </g>
            );
          })}
        </g>
      )}
    </g>
  );
};
