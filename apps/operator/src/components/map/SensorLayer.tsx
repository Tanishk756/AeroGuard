import React from 'react';
import { Sensor } from '../../types';

interface SensorLayerProps {
  sensors: Sensor[];
  selectedSensorId?: string | null;
  onSelectSensor?: (sensorId: string) => void;
  latLonToScreen: (lat: number, lon: number) => { x: number; y: number };
  zoom: number;
}

export const SensorLayer: React.FC<SensorLayerProps> = ({
  sensors,
  selectedSensorId,
  onSelectSensor,
  latLonToScreen,
  zoom,
}) => {
  // 1 degree lat is approx 111,320 meters
  const METERS_PER_DEGREE = 111320;
  const BASE_PIXELS_PER_DEGREE = 2500;

  return (
    <g className="sensor-layer">
      {sensors.map((s) => {
        const meta = s.configuration_metadata;
        const lat = typeof meta?.latitude === 'number' ? meta.latitude : null;
        const lon = typeof meta?.longitude === 'number' ? meta.longitude : null;

        // Skip sensors that have no geographical position configured
        if (lat === null || lon === null) return null;

        const { x, y } = latLonToScreen(lat, lon);
        const isSelected = s.id === selectedSensorId;
        const rangeMeters = typeof meta?.range_meters === 'number' && meta.range_meters > 0 ? meta.range_meters : null;

        // Only compute range radius if valid range_meters is provided
        let rangePixelRadius = 0;
        if (rangeMeters) {
          const degrees = rangeMeters / METERS_PER_DEGREE;
          rangePixelRadius = degrees * BASE_PIXELS_PER_DEGREE * zoom;
        }

        const isOnline = s.status === 'ACTIVE';
        const sensorColor = isOnline ? '#38bdf8' : '#64748b';

        return (
          <g
            key={s.id}
            onClick={(e) => {
              e.stopPropagation();
              onSelectSensor?.(s.id);
            }}
            style={{ cursor: 'pointer' }}
            tabIndex={0}
            role="button"
            aria-label={`Sensor ${s.name} (${s.source_type})`}
          >
            {/* Range coverage circle (Rendered ONLY when range_meters is explicitly provided) */}
            {rangeMeters && rangePixelRadius > 2 && (
              <circle
                cx={x}
                cy={y}
                r={rangePixelRadius}
                fill={isSelected ? 'rgba(56, 189, 248, 0.08)' : 'rgba(56, 189, 248, 0.03)'}
                stroke={isSelected ? 'rgba(56, 189, 248, 0.5)' : 'rgba(56, 189, 248, 0.25)'}
                strokeWidth={isSelected ? '1.5' : '1'}
                strokeDasharray="4 4"
              />
            )}

            {/* Selection Reticle */}
            {isSelected && (
              <circle
                cx={x}
                cy={y}
                r={16}
                fill="none"
                stroke="var(--color-accent)"
                strokeWidth="1.5"
                strokeDasharray="2 3"
              />
            )}

            {/* Sensor Triangle Marker */}
            <polygon
              points={`${x},${y - 8} ${x + 7},${y + 6} ${x - 7},${y + 6}`}
              fill="rgba(6, 13, 21, 0.95)"
              stroke={sensorColor}
              strokeWidth={isSelected ? '2.2' : '1.5'}
            />

            {/* Modality Icon / Dot */}
            <circle cx={x} cy={y + 1} r={2} fill={sensorColor} />

            {/* Sensor Label Tag */}
            <g transform={`translate(${x + 10}, ${y - 4})`}>
              <rect
                x={-2}
                y={-8}
                width={s.name.length * 6 + 4}
                height={12}
                fill="rgba(6, 13, 21, 0.85)"
                stroke="var(--border-subtle)"
                strokeWidth="0.8"
                rx="2"
              />
              <text
                x={0}
                y={1}
                fill={isSelected ? 'var(--color-accent)' : 'var(--text-secondary)'}
                fontSize="8.5px"
                fontFamily="monospace"
              >
                {s.name}
              </text>
            </g>
          </g>
        );
      })}
    </g>
  );
};
