/**
 * AeroGuard Tactical Map Component
 * Upgraded in MAP2 with WebGPU / Canvas 2D Hardware Acceleration
 */

import React, { useEffect, useRef, useState } from 'react';
import { useMapViewport } from '../../hooks/useMapViewport';
import {
  DefensiveIntelligenceSummary,
  Geofence,
  GeofenceGeometry,
  MapLayerVisibility,
  Sensor,
  ThreatAssessment,
  Track,
  TrackHistoryPoint,
  TrajectoryPrediction,
} from '../../types';
import { CoordinateReadout } from './CoordinateReadout';
import { GeofenceLayer } from './GeofenceLayer';
import { MapControls } from './MapControls';
import { TacticalMapCanvas } from './TacticalMapCanvas';

interface TacticalMapProps {
  tracks: Track[];
  threats?: ThreatAssessment[];
  intelligence?: Record<string, DefensiveIntelligenceSummary>;
  sensors: Sensor[];
  geofences: Geofence[];
  selectedTrackHistory?: TrackHistoryPoint[];
  selectedTrackPrediction?: TrajectoryPrediction | null;
  selectedTrackId?: string | null;
  selectedSensorId?: string | null;
  selectedGeofenceId?: string | null;
  draftGeometry?: GeofenceGeometry | null;
  onSelectTrack?: (trackId: string) => void;
  onSelectSensor?: (sensorId: string) => void;
  onSelectGeofence?: (geofenceId: string) => void;
  onClearSelection?: () => void;
}

export const TacticalMap: React.FC<TacticalMapProps> = ({
  tracks,
  threats = [],
  intelligence = {},
  sensors,
  geofences,
  selectedTrackHistory = [],
  selectedTrackPrediction = null,
  selectedTrackId,
  selectedSensorId,
  selectedGeofenceId,
  draftGeometry,
  onSelectTrack,
  onSelectSensor,
  onSelectGeofence,
  onClearSelection,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 800, height: 500 });
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

  // ResizeObserver for responsive canvas dimensions
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

  // Keyboard navigation & accessibility handlers
  const handleKeyDown = (e: React.KeyboardEvent<HTMLDivElement>) => {
    const PAN_STEP = 30;
    if (e.key === 'ArrowUp' || e.key === 'w' || e.key === 'W') {
      pan(0, PAN_STEP);
      e.preventDefault();
    } else if (e.key === 'ArrowDown' || e.key === 's' || e.key === 'S') {
      pan(0, -PAN_STEP);
      e.preventDefault();
    } else if (e.key === 'ArrowLeft' || e.key === 'a' || e.key === 'A') {
      pan(PAN_STEP, 0);
      e.preventDefault();
    } else if (e.key === 'ArrowRight' || e.key === 'd' || e.key === 'D') {
      pan(-PAN_STEP, 0);
      e.preventDefault();
    } else if (e.key === '+' || e.key === '=') {
      zoomIn();
      e.preventDefault();
    } else if (e.key === '-' || e.key === '_') {
      zoomOut();
      e.preventDefault();
    } else if (e.key === '0' || e.key === 'r' || e.key === 'R') {
      resetView();
      e.preventDefault();
    } else if (e.key === 'Escape') {
      onClearSelection?.();
      e.preventDefault();
    }
  };

  const handleMouseMove = (e: React.MouseEvent) => {
    const rect = containerRef.current?.getBoundingClientRect();
    if (rect) {
      const relX = e.clientX - rect.left;
      const relY = e.clientY - rect.top;
      const geo = screenToLatLon(relX, relY, dimensions.width, dimensions.height);
      setCursorLatLon(geo);
    }
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

  // Selected track summary for screen readers
  const selectedTrack = tracks.find((t) => t.id === selectedTrackId);
  const selectedIntel = selectedTrackId ? intelligence[selectedTrackId] : null;

  return (
    <div
      ref={containerRef}
      role="region"
      aria-label="Tactical Operational Map"
      tabIndex={0}
      onKeyDown={handleKeyDown}
      onMouseMove={handleMouseMove}
      onWheel={handleWheel}
      style={{
        width: '100%',
        height: '100%',
        minHeight: '420px',
        position: 'relative',
        overflow: 'hidden',
        backgroundColor: '#040910',
        userSelect: 'none',
        outline: 'none',
      }}
    >
      {/* 1. High-Performance WebGPU / Canvas 2D Accelerated Tactical Map */}
      <TacticalMapCanvas
        tracks={tracks}
        threats={threats}
        intelligence={intelligence}
        sensors={sensors}
        geofences={geofences}
        selectedTrackHistory={selectedTrackHistory}
        selectedTrackPrediction={selectedTrackPrediction}
        selectedTrackId={selectedTrackId}
        selectedSensorId={selectedSensorId}
        selectedGeofenceId={selectedGeofenceId}
        layers={layers}
        centerLat={viewport.centerLat}
        centerLon={viewport.centerLon}
        zoom={viewport.zoom}
        panOffsetX={viewport.panOffset.x}
        panOffsetY={viewport.panOffset.y}
        onSelectTrack={onSelectTrack}
        onSelectSensor={onSelectSensor}
        onSelectGeofence={onSelectGeofence}
        onPan={pan}
      />

      {/* 2. Draft Geometry SVG Overlay (for Zone Studio interactive authoring) */}
      {draftGeometry && (
        <svg
          width={dimensions.width}
          height={dimensions.height}
          style={{
            position: 'absolute',
            top: 0,
            left: 0,
            width: '100%',
            height: '100%',
            pointerEvents: 'none',
          }}
        >
          <GeofenceLayer
            geofences={[]}
            draftGeometry={draftGeometry}
            latLonToScreen={projectedScreen}
          />
        </svg>
      )}

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

      {/* Visually Hidden Semantic Status for Screen Readers */}
      <div
        aria-live="polite"
        style={{
          position: 'absolute',
          width: '1px',
          height: '1px',
          padding: '0',
          margin: '-1px',
          overflow: 'hidden',
          clip: 'rect(0, 0, 0, 0)',
          whiteSpace: 'nowrap',
          border: '0',
        }}
      >
        {selectedTrack
          ? `Selected track ${selectedTrack.id}, classification ${selectedTrack.classification || 'unknown'}, state ${selectedTrack.state}, anomaly score ${selectedIntel?.anomaly?.anomaly_score ?? 'none'}`
          : `Tactical map showing ${tracks.length} tracks, ${sensors.length} sensors, ${geofences.length} geofences.`}
      </div>
    </div>
  );
};
