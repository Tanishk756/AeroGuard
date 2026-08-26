import { useCallback, useState } from 'react';
import { MapViewportState } from '../types';

export interface GeoPoint {
  latitude: number;
  longitude: number;
}

export interface ViewportHookReturn {
  viewport: MapViewportState;
  latLonToScreen: (lat: number, lon: number, width: number, height: number) => { x: number; y: number };
  screenToLatLon: (screenX: number, screenY: number, width: number, height: number) => { lat: number; lon: number };
  zoomIn: () => void;
  zoomOut: () => void;
  setZoom: (zoom: number) => void;
  pan: (dx: number, dy: number) => void;
  centerOn: (lat: number, lon: number) => void;
  resetView: () => void;
  fitBounds: (points: GeoPoint[], width: number, height: number) => void;
}

const DEFAULT_CENTER_LAT = 37.7749;
const DEFAULT_CENTER_LON = -122.4194;
const DEFAULT_ZOOM = 1.0;
const BASE_PIXELS_PER_DEGREE = 2500;

export function useMapViewport(
  initialCenterLat = DEFAULT_CENTER_LAT,
  initialCenterLon = DEFAULT_CENTER_LON,
  initialZoom = DEFAULT_ZOOM
): ViewportHookReturn {
  const [viewport, setViewport] = useState<MapViewportState>({
    centerLat: initialCenterLat,
    centerLon: initialCenterLon,
    zoom: initialZoom,
    panOffset: { x: 0, y: 0 },
  });

  const latLonToScreen = useCallback(
    (lat: number, lon: number, width: number, height: number): { x: number; y: number } => {
      const cosLat = Math.cos((viewport.centerLat * Math.PI) / 180);
      const scale = BASE_PIXELS_PER_DEGREE * viewport.zoom;

      const x = width / 2 + (lon - viewport.centerLon) * scale * cosLat + viewport.panOffset.x;
      const y = height / 2 - (lat - viewport.centerLat) * scale + viewport.panOffset.y;

      return { x, y };
    },
    [viewport.centerLat, viewport.centerLon, viewport.zoom, viewport.panOffset]
  );

  const screenToLatLon = useCallback(
    (screenX: number, screenY: number, width: number, height: number): { lat: number; lon: number } => {
      const cosLat = Math.cos((viewport.centerLat * Math.PI) / 180);
      const scale = BASE_PIXELS_PER_DEGREE * viewport.zoom;

      const lon = viewport.centerLon + (screenX - width / 2 - viewport.panOffset.x) / (scale * (cosLat || 1));
      const lat = viewport.centerLat - (screenY - height / 2 - viewport.panOffset.y) / scale;

      return { lat, lon };
    },
    [viewport.centerLat, viewport.centerLon, viewport.zoom, viewport.panOffset]
  );

  const zoomIn = useCallback(() => {
    setViewport((prev) => ({
      ...prev,
      zoom: Math.min(50.0, Number((prev.zoom * 1.25).toFixed(3))),
    }));
  }, []);

  const zoomOut = useCallback(() => {
    setViewport((prev) => ({
      ...prev,
      zoom: Math.max(0.05, Number((prev.zoom / 1.25).toFixed(3))),
    }));
  }, []);

  const setZoom = useCallback((zoom: number) => {
    setViewport((prev) => ({
      ...prev,
      zoom: Math.max(0.05, Math.min(50.0, zoom)),
    }));
  }, []);

  const pan = useCallback((dx: number, dy: number) => {
    setViewport((prev) => ({
      ...prev,
      panOffset: {
        x: prev.panOffset.x + dx,
        y: prev.panOffset.y + dy,
      },
    }));
  }, []);

  const centerOn = useCallback((lat: number, lon: number) => {
    setViewport((prev) => ({
      ...prev,
      centerLat: lat,
      centerLon: lon,
      panOffset: { x: 0, y: 0 },
    }));
  }, []);

  const resetView = useCallback(() => {
    setViewport({
      centerLat: initialCenterLat,
      centerLon: initialCenterLon,
      zoom: initialZoom,
      panOffset: { x: 0, y: 0 },
    });
  }, [initialCenterLat, initialCenterLon, initialZoom]);

  const fitBounds = useCallback(
    (points: GeoPoint[], width: number, height: number) => {
      if (points.length === 0) return;

      if (points.length === 1) {
        setViewport({
          centerLat: points[0].latitude,
          centerLon: points[0].longitude,
          zoom: 1.5,
          panOffset: { x: 0, y: 0 },
        });
        return;
      }

      let minLat = points[0].latitude;
      let maxLat = points[0].latitude;
      let minLon = points[0].longitude;
      let maxLon = points[0].longitude;

      for (const pt of points) {
        if (pt.latitude < minLat) minLat = pt.latitude;
        if (pt.latitude > maxLat) maxLat = pt.latitude;
        if (pt.longitude < minLon) minLon = pt.longitude;
        if (pt.longitude > maxLon) maxLon = pt.longitude;
      }

      const centerLat = (minLat + maxLat) / 2;
      const centerLon = (minLon + maxLon) / 2;

      const dLat = Math.max(maxLat - minLat, 0.005);
      const cosLat = Math.cos((centerLat * Math.PI) / 180) || 1;
      const dLon = Math.max((maxLon - minLon) * cosLat, 0.005);

      const padding = 60;
      const availWidth = Math.max(width - padding * 2, 100);
      const availHeight = Math.max(height - padding * 2, 100);

      const zoomX = availWidth / (dLon * BASE_PIXELS_PER_DEGREE);
      const zoomY = availHeight / (dLat * BASE_PIXELS_PER_DEGREE);
      const targetZoom = Math.min(zoomX, zoomY, 15.0);

      setViewport({
        centerLat,
        centerLon,
        zoom: Math.max(0.1, Math.min(20.0, Number(targetZoom.toFixed(2)))),
        panOffset: { x: 0, y: 0 },
      });
    },
    []
  );

  return {
    viewport,
    latLonToScreen,
    screenToLatLon,
    zoomIn,
    zoomOut,
    setZoom,
    pan,
    centerOn,
    resetView,
    fitBounds,
  };
}
