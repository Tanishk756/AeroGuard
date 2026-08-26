import React from 'react';
import { Geofence, GeofenceGeometry } from '../../types';

interface GeofenceLayerProps {
  geofences: Geofence[];
  selectedGeofenceId?: string | null;
  draftGeometry?: GeofenceGeometry | null;
  onSelectGeofence?: (geofenceId: string) => void;
  latLonToScreen: (lat: number, lon: number) => { x: number; y: number };
}

export const GeofenceLayer: React.FC<GeofenceLayerProps> = ({
  geofences,
  selectedGeofenceId,
  draftGeometry,
  onSelectGeofence,
  latLonToScreen,
}) => {
  return (
    <g className="geofence-layer">
      {geofences.map((g) => {
        const isSelected = g.id === selectedGeofenceId;
        const strokeColor = g.enabled
          ? isSelected
            ? 'var(--color-accent)'
            : '#f59e0b' // Amber
          : '#64748b'; // Inactive slate

        const fillColor = g.enabled
          ? isSelected
            ? 'rgba(56, 189, 248, 0.12)'
            : 'rgba(245, 158, 11, 0.05)'
          : 'rgba(100, 116, 139, 0.03)';

        if (g.geometry.type === 'bbox') {
          const { min_lat, min_lon, max_lat, max_lon } = g.geometry;
          const topLeft = latLonToScreen(max_lat, min_lon);
          const bottomRight = latLonToScreen(min_lat, max_lon);

          const x = Math.min(topLeft.x, bottomRight.x);
          const y = Math.min(topLeft.y, bottomRight.y);
          const width = Math.abs(bottomRight.x - topLeft.x);
          const height = Math.abs(bottomRight.y - topLeft.y);

          return (
            <g
              key={g.id}
              onClick={(e) => {
                e.stopPropagation();
                onSelectGeofence?.(g.id);
              }}
              style={{ cursor: 'pointer' }}
              tabIndex={0}
              role="button"
              aria-label={`Geofence ${g.name} (BBox)`}
            >
              <rect
                x={x}
                y={y}
                width={width}
                height={height}
                fill={fillColor}
                stroke={strokeColor}
                strokeWidth={isSelected ? '2' : '1.2'}
                strokeDasharray={g.enabled ? '4 2' : '2 4'}
              />
              <text
                x={x + 4}
                y={y + 12}
                fill={strokeColor}
                fontSize="9px"
                fontFamily="monospace"
                fontWeight={isSelected ? 'bold' : 'normal'}
                opacity={0.9}
              >
                GEOFENCE: {g.name}
              </text>
            </g>
          );
        }

        if (g.geometry.type === 'polygon' && g.geometry.coordinates?.length >= 3) {
          const pointsString = g.geometry.coordinates
            .map(([lat, lon]) => {
              const pt = latLonToScreen(lat, lon);
              return `${pt.x},${pt.y}`;
            })
            .join(' ');

          const firstPt = latLonToScreen(g.geometry.coordinates[0][0], g.geometry.coordinates[0][1]);

          return (
            <g
              key={g.id}
              onClick={(e) => {
                e.stopPropagation();
                onSelectGeofence?.(g.id);
              }}
              style={{ cursor: 'pointer' }}
              tabIndex={0}
              role="button"
              aria-label={`Geofence ${g.name} (Polygon)`}
            >
              <polygon
                points={pointsString}
                fill={fillColor}
                stroke={strokeColor}
                strokeWidth={isSelected ? '2' : '1.2'}
                strokeDasharray={g.enabled ? '4 2' : '2 4'}
              />
              <text
                x={firstPt.x + 4}
                y={firstPt.y + 12}
                fill={strokeColor}
                fontSize="9px"
                fontFamily="monospace"
                fontWeight={isSelected ? 'bold' : 'normal'}
                opacity={0.9}
              >
                GEOFENCE: {g.name}
              </text>
            </g>
          );
        }

        return null;
      })}

      {/* Render Live Draft Geometry Preview */}
      {draftGeometry && draftGeometry.type === 'bbox' && (
        <g className="draft-geofence-preview">
          {(() => {
            const { min_lat, min_lon, max_lat, max_lon } = draftGeometry;
            const topLeft = latLonToScreen(max_lat, min_lon);
            const bottomRight = latLonToScreen(min_lat, max_lon);
            const x = Math.min(topLeft.x, bottomRight.x);
            const y = Math.min(topLeft.y, bottomRight.y);
            const width = Math.abs(bottomRight.x - topLeft.x);
            const height = Math.abs(bottomRight.y - topLeft.y);

            return (
              <>
                <rect
                  x={x}
                  y={y}
                  width={width}
                  height={height}
                  fill="rgba(56, 189, 248, 0.18)"
                  stroke="#38bdf8"
                  strokeWidth="2"
                  strokeDasharray="6 3"
                />
                <text
                  x={x + 4}
                  y={y + 14}
                  fill="#38bdf8"
                  fontSize="10px"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  ✎ DRAFT BBOX ZONE
                </text>
              </>
            );
          })()}
        </g>
      )}

      {draftGeometry && draftGeometry.type === 'polygon' && draftGeometry.coordinates?.length >= 3 && (
        <g className="draft-geofence-preview">
          {(() => {
            const pointsString = draftGeometry.coordinates
              .map(([lat, lon]) => {
                const pt = latLonToScreen(lat, lon);
                return `${pt.x},${pt.y}`;
              })
              .join(' ');

            const firstPt = latLonToScreen(draftGeometry.coordinates[0][0], draftGeometry.coordinates[0][1]);

            return (
              <>
                <polygon
                  points={pointsString}
                  fill="rgba(56, 189, 248, 0.18)"
                  stroke="#38bdf8"
                  strokeWidth="2"
                  strokeDasharray="6 3"
                />
                <text
                  x={firstPt.x + 4}
                  y={firstPt.y + 14}
                  fill="#38bdf8"
                  fontSize="10px"
                  fontFamily="monospace"
                  fontWeight="bold"
                >
                  ✎ DRAFT POLYGON ({draftGeometry.coordinates.length} VERTICES)
                </text>
              </>
            );
          })()}
        </g>
      )}
    </g>
  );
};
