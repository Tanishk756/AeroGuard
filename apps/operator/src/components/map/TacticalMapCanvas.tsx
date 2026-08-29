/**
 * Hardware-Accelerated Tactical Map Canvas for AeroGuard MAP2
 */

import React, { useEffect, useRef, useState } from 'react';
import {
  DefensiveIntelligenceSummary,
  Geofence,
  Incident,
  MapLayerVisibility,
  MultiTrackIntelligenceSummary,
  Sensor,
  ThreatAssessment,
  Track,
  TrackHistoryPoint,
  TrajectoryPrediction,
} from '../../types';
import {
  buildRenderScene,
  CanvasRenderer,
  detectRendererCapabilities,
  IMapRenderer,
  RendererCapabilities,
  RendererType,
  WebGPURenderer,
} from './renderer';

interface TacticalMapCanvasProps {
  tracks: Track[];
  threats?: ThreatAssessment[];
  intelligence?: Record<string, DefensiveIntelligenceSummary>;
  multiTrackIntelligence?: MultiTrackIntelligenceSummary | null;
  sensors: Sensor[];
  geofences: Geofence[];
  incidents?: Incident[];
  selectedTrackHistory?: TrackHistoryPoint[];
  selectedTrackPrediction?: TrajectoryPrediction | null;
  selectedTrackId?: string | null;
  selectedSensorId?: string | null;
  selectedGeofenceId?: string | null;
  selectedGroupId?: string | null;
  selectedIncidentId?: string | null;
  layers?: Partial<MapLayerVisibility>;
  centerLat: number;
  centerLon: number;
  zoom: number;
  panOffsetX: number;
  panOffsetY: number;
  onSelectTrack?: (trackId: string) => void;
  onSelectSensor?: (sensorId: string) => void;
  onSelectGeofence?: (geofenceId: string) => void;
  onSelectGroup?: (groupId: string) => void;
  onSelectIncident?: (incidentId: string) => void;
  onPan?: (dx: number, dy: number) => void;
}

export const TacticalMapCanvas: React.FC<TacticalMapCanvasProps> = ({
  tracks,
  threats = [],
  intelligence = {},
  multiTrackIntelligence = null,
  sensors,
  geofences,
  incidents = [],
  selectedTrackHistory = [],
  selectedTrackPrediction = null,
  selectedTrackId = null,
  selectedSensorId = null,
  selectedGeofenceId = null,
  selectedGroupId = null,
  selectedIncidentId = null,
  layers = {},
  centerLat,
  centerLon,
  zoom,
  panOffsetX,
  panOffsetY,
  onSelectTrack,
  onSelectSensor,
  onSelectGeofence,
  onSelectGroup,
  onSelectIncident,
  onPan,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const rendererRef = useRef<IMapRenderer | null>(null);
  const [capabilities, setCapabilities] = useState<RendererCapabilities | null>(null);
  const [rendererType, setRendererType] = useState<RendererType>('CANVAS');
  const [dimensions, setDimensions] = useState<{ width: number; height: number }>({ width: 800, height: 600 });
  const [isDragging, setIsDragging] = useState<boolean>(false);
  const dragStartRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const hasMovedRef = useRef<boolean>(false);

  // 1. Detect capabilities and initialize renderer
  useEffect(() => {
    let isMounted = true;

    detectRendererCapabilities().then(async (caps) => {
      if (!isMounted) return;
      setCapabilities(caps);

      if (!canvasRef.current) return;

      let r: IMapRenderer;
      if (caps.preferredType === 'WEBGPU') {
        r = new WebGPURenderer();
      } else {
        r = new CanvasRenderer();
      }

      const success = await r.initialize(canvasRef.current);
      if (isMounted) {
        if (success) {
          rendererRef.current = r;
          setRendererType(r.type);
        } else {
          // Fallback to Canvas
          const fallback = new CanvasRenderer();
          await fallback.initialize(canvasRef.current);
          rendererRef.current = fallback;
          setRendererType('CANVAS');
        }
      }
    });

    return () => {
      isMounted = false;
      if (rendererRef.current) {
        rendererRef.current.destroy();
        rendererRef.current = null;
      }
    };
  }, []);

  // 2. ResizeObserver for fluid responsive dimensions
  useEffect(() => {
    if (!containerRef.current) return;

    const observer = new ResizeObserver((entries) => {
      for (const entry of entries) {
        const { width, height } = entry.contentRect;
        if (width > 0 && height > 0) {
          setDimensions({ width, height });
          if (rendererRef.current) {
            rendererRef.current.resize(width, height);
          }
        }
      }
    });

    observer.observe(containerRef.current);
    return () => observer.disconnect();
  }, []);

  // 3. Continuous frame render triggered on scene changes
  useEffect(() => {
    if (!rendererRef.current || !rendererRef.current.isInitialized) return;

    const scene = buildRenderScene({
      width: dimensions.width,
      height: dimensions.height,
      centerLat,
      centerLon,
      zoom,
      panOffsetX,
      panOffsetY,
      layers,
      tracks,
      threats,
      intelligence,
      multiTrackIntelligence,
      selectedTrackId,
      selectedSensorId,
      selectedGeofenceId,
      selectedGroupId,
      selectedIncidentId,
      selectedTrackHistory,
      selectedTrackPrediction,
      geofences,
      sensors,
      incidents,
    });

    rendererRef.current.render(scene);
  }, [
    dimensions,
    centerLat,
    centerLon,
    zoom,
    panOffsetX,
    panOffsetY,
    layers,
    tracks,
    threats,
    intelligence,
    multiTrackIntelligence,
    selectedTrackId,
    selectedSensorId,
    selectedGeofenceId,
    selectedGroupId,
    selectedIncidentId,
    selectedTrackHistory,
    selectedTrackPrediction,
    geofences,
    sensors,
    incidents,
  ]);

  // 4. Pointer interactions & Hit Testing
  const handlePointerDown = (e: React.PointerEvent<HTMLCanvasElement>) => {
    setIsDragging(true);
    hasMovedRef.current = false;
    dragStartRef.current = { x: e.clientX, y: e.clientY };
    (e.target as HTMLElement).setPointerCapture(e.pointerId);
  };

  const handlePointerMove = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (!isDragging) return;

    const dx = e.clientX - dragStartRef.current.x;
    const dy = e.clientY - dragStartRef.current.y;

    if (Math.abs(dx) > 3 || Math.abs(dy) > 3) {
      hasMovedRef.current = true;
    }

    if (hasMovedRef.current && onPan) {
      onPan(dx, dy);
      dragStartRef.current = { x: e.clientX, y: e.clientY };
    }
  };

  const handlePointerUp = (e: React.PointerEvent<HTMLCanvasElement>) => {
    setIsDragging(false);
    try {
      (e.target as HTMLElement).releasePointerCapture(e.pointerId);
    } catch {}

    // If it was a click (not a drag pan), execute hit test
    if (!hasMovedRef.current && rendererRef.current && canvasRef.current) {
      const rect = canvasRef.current.getBoundingClientRect();
      const clickX = e.clientX - rect.left;
      const clickY = e.clientY - rect.top;

      const scene = buildRenderScene({
        width: dimensions.width,
        height: dimensions.height,
        centerLat,
        centerLon,
        zoom,
        panOffsetX,
        panOffsetY,
        layers,
        tracks,
        threats,
        intelligence,
        multiTrackIntelligence,
        selectedTrackId,
        selectedSensorId,
        selectedGeofenceId,
        selectedGroupId,
        selectedIncidentId,
        selectedTrackHistory,
        selectedTrackPrediction,
        geofences,
        sensors,
        incidents,
      });

      const hit = rendererRef.current.hitTest(clickX, clickY, scene);
      if (hit) {
        if (hit.type === 'incident' && onSelectIncident) {
          onSelectIncident(hit.id);
        } else if (hit.type === 'track' && onSelectTrack) {
          onSelectTrack(hit.id);
        } else if (hit.type === 'sensor' && onSelectSensor) {
          onSelectSensor(hit.id);
        } else if (hit.type === 'geofence' && onSelectGeofence) {
          onSelectGeofence(hit.id);
        } else if (hit.type === 'group' && onSelectGroup) {
          onSelectGroup(hit.id);
        }
      }
    }
  };

  return (
    <div
      ref={containerRef}
      style={{
        position: 'relative',
        width: '100%',
        height: '100%',
        overflow: 'hidden',
        backgroundColor: '#0a0f1d',
        userSelect: 'none',
      }}
    >
      <canvas
        ref={canvasRef}
        onPointerDown={handlePointerDown}
        onPointerMove={handlePointerMove}
        onPointerUp={handlePointerUp}
        style={{
          display: 'block',
          width: '100%',
          height: '100%',
          cursor: isDragging ? 'grabbing' : 'crosshair',
        }}
      />

      {/* Subtle Hardware Diagnostics Badge */}
      <div
        style={{
          position: 'absolute',
          bottom: '8px',
          right: '8px',
          padding: '2px 6px',
          backgroundColor: 'rgba(15, 23, 42, 0.75)',
          border: '1px solid rgba(56, 189, 248, 0.2)',
          borderRadius: '3px',
          fontSize: '9px',
          fontFamily: 'monospace',
          color: rendererType === 'WEBGPU' ? '#38bdf8' : '#94a3b8',
          pointerEvents: 'none',
        }}
      >
        RENDERER: {rendererType}
      </div>
    </div>
  );
};
