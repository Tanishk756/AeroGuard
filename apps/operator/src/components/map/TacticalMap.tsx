import React, { useEffect, useRef, useState } from 'react';
import { useMapViewport } from '../../hooks/useMapViewport';
import { Geofence, MapLayerVisibility, Sensor, Track, TrackHistoryPoint } from '../../types';
import { CoordinateReadout } from './CoordinateReadout';
import { GeofenceLayer } from './GeofenceLayer';
import { MapControls } from './MapControls';
import { SensorLayer } from './SensorLayer';
import { TrackLayer } from './TrackLayer';
import { TrajectoryLayer } from './TrajectoryLayer';

interface TacticalMapProps {
  tracks: Track[];
  sensors: Sensor[];
  geofences: Geofence[];
  selectedTrackHistory?: TrackHistoryPoint[];
  selectedTrackId?: string | null;
  selectedSensorId?: string | null;
  selectedGeofenceId?: string | null;
  onSelectTrack?: (trackId: string) => void;
  onSelectSensor?: (sensorId: string) => void;
  onSelectGeofence?: (geofenceId: string) => void;
  onClearSelection?: () => void;
}

export const TacticalMap: React.FC<TacticalMapProps> = ({
  tracks,
  sensors,
  geofences,
  selectedTrackHistory = [],
  selectedTrackId,
  selectedSensorId,
  selectedGeofenceId,
  onSelectTrack,
  onSelectSensor,
  onSelectGeofence,
  onClearSelection,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 800, height: 500 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const [dragStart, setDragStart] = useState<{ x: number; y: number }>({ x: 0, y: 0 });
  const [cursorLatLon, setCursorLatLon] = useState<{ lat: number; lon: number } | null>(null);

  const [layers, setLayers] = useState<MapLayerVisibility>({
    tracks: true,
    sensors: true,
    geofences: true,
    rangeRings: true,
    trajectories: true,
    labels: true,
    grid: true,
  });

  const {
    viewport,
    latLonToScreen,
    screenToLatLon,
    zoomIn,
    zoomOut,
    pan,
    resetView,
    fitBounds,
  } = useMapViewport(37.7749, -122.4194, 1.2);

  // ResizeObserver for responsive SVG dimensions
  useEffect(() => {
    if (!containerRef.current) return;
    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width, height });
        }
      }
    });
    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // Fit all visible operational points
  const handleFitAll = () => {
    const points: Array<{ latitude: number; longitude: number }> = [];

    tracks.forEach((t) => points.push({ latitude: t.latitude, longitude: t.longitude }));

    sensors.forEach((s) => {
      const lat = s.configuration_metadata?.latitude;
      const lon = s.configuration_metadata?.longitude;
      if (typeof lat === 'number' && typeof lon === 'number') {
        points.push({ latitude: lat, longitude: lon });
      }
    });

    geofences.forEach((g) => {
      if (g.geometry.type === 'bbox') {
        points.push({ latitude: g.geometry.min_lat, longitude: g.geometry.min_lon });
        points.push({ latitude: g.geometry.max_lat, longitude: g.geometry.max_lon });
      } else if (g.geometry.type === 'polygon' && g.geometry.coordinates) {
        g.geometry.coordinates.forEach(([lat, lon]) => points.push({ latitude: lat, longitude: lon }));
      }
    });

    fitBounds(points, dimensions.width, dimensions.height);
  };

  // Initial fit when data first loads
  const hasFittedRef = useRef<boolean>(false);
  useEffect(() => {
    if (!hasFittedRef.current && (tracks.length > 0 || sensors.length > 0 || geofences.length > 0)) {
      handleFitAll();
      hasFittedRef.current = true;
    }
  }, [tracks, sensors, geofences]);

  const handleMouseDown = (e: React.MouseEvent) => {
    if (e.button !== 0) return; // Only main left-click
    setIsDragging(true);
    setDragStart({ x: e.clientX, y: e.clientY });
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      const relX = e.clientX - rect.left;
      const relY = e.clientY - rect.top;
      const geo = screenToLatLon(relX, relY, dimensions.width, dimensions.height);
      setCursorLatLon(geo);
    }

    if (isDragging) {
      const dx = e.clientX - dragStart.x;
      const dy = e.clientY - dragStart.y;
      pan(dx, dy);
      setDragStart({ x: e.clientX, y: e.clientY });
    }
  };

  const handleMouseUp = () => {
    setIsDragging(false);
  };

  const handleWheel = (e: React.WheelEvent) => {
    e.preventDefault();
    if (e.deltaY < 0) {
      zoomIn();
    } else {
      zoomOut();
    }
  };

  const handleToggleLayer = (layerName: keyof MapLayerVisibility) => {
    setLayers((prev) => ({ ...prev, [layerName]: !prev[layerName] }));
  };

  const projectedScreen = (lat: number, lon: number) =>
    latLonToScreen(lat, lon, dimensions.width, dimensions.height);

  const centerScreen = projectedScreen(viewport.centerLat, viewport.centerLon);

  // Concentric range rings radii in pixels
  const METERS_PER_DEGREE = 111320;
  const BASE_PIXELS_PER_DEGREE = 2500;
  const getRadiusPixels = (meters: number) => {
    return (meters / METERS_PER_DEGREE) * BASE_PIXELS_PER_DEGREE * viewport.zoom;
  };

  const ring500 = getRadiusPixels(500);
  const ring1000 = getRadiusPixels(1000);
  const ring2000 = getRadiusPixels(2000);
  const ring5000 = getRadiusPixels(5000);

  return (
    <div
      ref={containerRef}
      onMouseDown={handleMouseDown}
      onMouseMove={handleMouseMove}
      onMouseUp={handleMouseUp}
      onMouseLeave={handleMouseUp}
      onWheel={handleWheel}
      onClick={() => onClearSelection?.()}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '420px',
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: '#040910',
        cursor: isDragging ? 'grabbing' : 'crosshair',
        userSelect: 'none',
      }}
    >
      <svg
        width={dimensions.width}
        height={dimensions.height}
        style={{ display: 'block', width: '100%', height: '100%' }}
      >
        {/* Adaptive Coordinate Grid Lines */}
        {layers.grid && (
          <g className="grid-layer" opacity={0.35}>
            {[-0.04, -0.02, 0, 0.02, 0.04].map((dLat) => {
              const latVal = viewport.centerLat + dLat / viewport.zoom;
              const p = projectedScreen(latVal, viewport.centerLon);
              return (
                <g key={`lat-${dLat}`}>
                  <line
                    x1={0}
                    y1={p.y}
                    x2={dimensions.width}
                    y2={p.y}
                    stroke="rgba(56, 189, 248, 0.25)"
                    strokeWidth="0.8"
                    strokeDasharray="2 4"
                  />
                  <text
                    x={8}
                    y={p.y - 3}
                    fill="rgba(56, 189, 248, 0.6)"
                    fontSize="8px"
                    fontFamily="monospace"
                  >
                    {latVal.toFixed(3)}°
                  </text>
                </g>
              );
            })}

            {[-0.04, -0.02, 0, 0.02, 0.04].map((dLon) => {
              const lonVal = viewport.centerLon + dLon / viewport.zoom;
              const p = projectedScreen(viewport.centerLat, lonVal);
              return (
                <g key={`lon-${dLon}`}>
                  <line
                    x1={p.x}
                    y1={0}
                    x2={p.x}
                    y2={dimensions.height}
                    stroke="rgba(56, 189, 248, 0.25)"
                    strokeWidth="0.8"
                    strokeDasharray="2 4"
                  />
                  <text
                    x={p.x + 3}
                    y={dimensions.height - 8}
                    fill="rgba(56, 189, 248, 0.6)"
                    fontSize="8px"
                    fontFamily="monospace"
                  >
                    {lonVal.toFixed(3)}°
                  </text>
                </g>
              );
            })}
          </g>
        )}

        {/* Concentric Range Rings */}
        {layers.rangeRings && (
          <g className="range-rings-layer" opacity={0.65}>
            {ring500 > 10 && (
              <g>
                <circle
                  cx={centerScreen.x}
                  cy={centerScreen.y}
                  r={ring500}
                  fill="none"
                  stroke="rgba(56, 189, 248, 0.25)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <text
                  x={centerScreen.x + ring500 + 4}
                  y={centerScreen.y - 2}
                  fill="rgba(56, 189, 248, 0.6)"
                  fontSize="8.5px"
                  fontFamily="monospace"
                >
                  500m
                </text>
              </g>
            )}

            {ring1000 > 15 && (
              <g>
                <circle
                  cx={centerScreen.x}
                  cy={centerScreen.y}
                  r={ring1000}
                  fill="none"
                  stroke="rgba(56, 189, 248, 0.2)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <text
                  x={centerScreen.x + ring1000 + 4}
                  y={centerScreen.y - 2}
                  fill="rgba(56, 189, 248, 0.5)"
                  fontSize="8.5px"
                  fontFamily="monospace"
                >
                  1000m
                </text>
              </g>
            )}

            {ring2000 > 25 && (
              <g>
                <circle
                  cx={centerScreen.x}
                  cy={centerScreen.y}
                  r={ring2000}
                  fill="none"
                  stroke="rgba(56, 189, 248, 0.15)"
                  strokeWidth="1"
                  strokeDasharray="4 4"
                />
                <text
                  x={centerScreen.x + ring2000 + 4}
                  y={centerScreen.y - 2}
                  fill="rgba(56, 189, 248, 0.4)"
                  fontSize="8.5px"
                  fontFamily="monospace"
                >
                  2000m
                </text>
              </g>
            )}

            {ring5000 > 40 && (
              <g>
                <circle
                  cx={centerScreen.x}
                  cy={centerScreen.y}
                  r={ring5000}
                  fill="none"
                  stroke="rgba(56, 189, 248, 0.1)"
                  strokeWidth="1"
                />
                <text
                  x={centerScreen.x + ring5000 + 4}
                  y={centerScreen.y - 2}
                  fill="rgba(56, 189, 248, 0.3)"
                  fontSize="8.5px"
                  fontFamily="monospace"
                >
                  5000m
                </text>
              </g>
            )}

            {/* Viewport Center Reticle */}
            <circle cx={centerScreen.x} cy={centerScreen.y} r={4} fill="none" stroke="var(--color-accent)" strokeWidth="1" />
            <line x1={centerScreen.x - 10} y1={centerScreen.y} x2={centerScreen.x + 10} y2={centerScreen.y} stroke="var(--color-accent)" strokeWidth="1" opacity={0.6} />
            <line x1={centerScreen.x} y1={centerScreen.y - 10} x2={centerScreen.x} y2={centerScreen.y + 10} stroke="var(--color-accent)" strokeWidth="1" opacity={0.6} />
          </g>
        )}

        {/* 1. Geofence Layer */}
        {layers.geofences && (
          <GeofenceLayer
            geofences={geofences}
            selectedGeofenceId={selectedGeofenceId}
            onSelectGeofence={onSelectGeofence}
            latLonToScreen={projectedScreen}
          />
        )}

        {/* 2. Sensor Layer */}
        {layers.sensors && (
          <SensorLayer
            sensors={sensors}
            selectedSensorId={selectedSensorId}
            onSelectSensor={onSelectSensor}
            latLonToScreen={projectedScreen}
            zoom={viewport.zoom}
          />
        )}

        {/* 3. Trajectory History Layer */}
        {layers.trajectories && (
          <TrajectoryLayer
            historyPoints={selectedTrackHistory}
            latLonToScreen={projectedScreen}
          />
        )}

        {/* 4. Track Layer */}
        {layers.tracks && (
          <TrackLayer
            tracks={tracks}
            selectedTrackId={selectedTrackId}
            onSelectTrack={onSelectTrack}
            latLonToScreen={projectedScreen}
            showLabels={layers.labels}
          />
        )}
      </svg>

      {/* Top Left: Controls Bar */}
      <div style={{ position: 'absolute', top: '10px', left: '10px', zIndex: 10 }}>
        <MapControls
          onZoomIn={zoomIn}
          onZoomOut={zoomOut}
          onResetView={resetView}
          onFitBounds={handleFitAll}
          layers={layers}
          onToggleLayer={handleToggleLayer}
        />
      </div>

      {/* Top Right: North Compass Rose */}
      <div
        className="font-mono"
        style={{
          position: 'absolute',
          top: '10px',
          right: '10px',
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          backgroundColor: 'rgba(6, 13, 21, 0.85)',
          border: '1px solid var(--border-subtle)',
          padding: '3px 8px',
          borderRadius: 'var(--radius-sm)',
          fontSize: '11px',
          color: 'var(--color-accent)',
          userSelect: 'none',
          backdropFilter: 'blur(4px)',
          zIndex: 10,
        }}
      >
        <span style={{ fontSize: '13px' }}>▲</span>
        <span>N</span>
      </div>

      {/* Bottom Left: Coordinate & Datum Readout */}
      <div style={{ position: 'absolute', bottom: '10px', left: '10px', zIndex: 10 }}>
        <CoordinateReadout
          centerLat={viewport.centerLat}
          centerLon={viewport.centerLon}
          zoom={viewport.zoom}
          cursorLatLon={cursorLatLon}
        />
      </div>
    </div>
  );
};
