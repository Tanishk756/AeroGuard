/**
 * AeroGuard Tactical Map Renderer Base Abstraction
 */

import { HitTestResult, IMapRenderer, RenderScene, RendererType } from './types';

export abstract class BaseMapRenderer implements IMapRenderer {
  abstract readonly type: RendererType;
  protected canvas: HTMLCanvasElement | null = null;
  protected width = 800;
  protected height = 600;
  protected _isInitialized = false;

  get isInitialized(): boolean {
    return this._isInitialized;
  }

  abstract initialize(canvas: HTMLCanvasElement): Promise<boolean>;
  abstract render(scene: RenderScene): void;

  resize(width: number, height: number): void {
    this.width = Math.max(1, width);
    this.height = Math.max(1, height);

    if (this.canvas) {
      const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
      this.canvas.width = Math.floor(this.width * dpr);
      this.canvas.height = Math.floor(this.height * dpr);
      this.canvas.style.width = `${this.width}px`;
      this.canvas.style.height = `${this.height}px`;
    }
  }

  /**
   * Deterministic spatial hit testing across tracks, sensors, and geofences.
   */
  hitTest(screenX: number, screenY: number, scene: RenderScene): HitTestResult | null {
    const TRACK_HIT_RADIUS = 16;
    const SENSOR_HIT_RADIUS = 14;
    let closestHit: HitTestResult | null = null;
    let minDistance = Infinity;

    // 1. Test Incident Markers (highest priority)
    const INCIDENT_HIT_RADIUS = 14;
    if (scene.incidents && scene.incidents.length > 0) {
      for (const inc of scene.incidents) {
        const dx = screenX - inc.screenX;
        const dy = screenY - inc.screenY;
        const dist = Math.sqrt(dx * dx + dy * dy);

        if (dist <= INCIDENT_HIT_RADIUS && dist < minDistance) {
          minDistance = dist;
          closestHit = {
            type: 'incident',
            id: inc.incidentId,
            screenX: inc.screenX,
            screenY: inc.screenY,
            distancePixels: dist,
          };
        }
      }
    }

    if (closestHit) return closestHit;

    // 2. Test Track Markers
    for (const track of scene.tracks) {
      const dx = screenX - track.screenX;
      const dy = screenY - track.screenY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist <= TRACK_HIT_RADIUS && dist < minDistance) {
        minDistance = dist;
        closestHit = {
          type: 'track',
          id: track.id,
          screenX: track.screenX,
          screenY: track.screenY,
          distancePixels: dist,
        };
      }
    }

    if (closestHit) return closestHit;

    // 2. Test Sensor Assets
    for (const sensor of scene.sensors) {
      const dx = screenX - sensor.screenX;
      const dy = screenY - sensor.screenY;
      const dist = Math.sqrt(dx * dx + dy * dy);

      if (dist <= SENSOR_HIT_RADIUS && dist < minDistance) {
        minDistance = dist;
        closestHit = {
          type: 'sensor',
          id: sensor.id,
          screenX: sensor.screenX,
          screenY: sensor.screenY,
          distancePixels: dist,
        };
      }
    }

    if (closestHit) return closestHit;

    // 3. Test Geofence Volumes (point in polygon or near boundary)
    for (const geofence of scene.geofences) {
      if (geofence.geometryType === 'CIRCLE' && geofence.radiusPixels && geofence.screenCoordinates.length > 0) {
        const center = geofence.screenCoordinates[0];
        const dist = Math.hypot(screenX - center.x, screenY - center.y);
        if (dist <= geofence.radiusPixels) {
          return {
            type: 'geofence',
            id: geofence.id,
            screenX: center.x,
            screenY: center.y,
            distancePixels: dist,
          };
        }
      } else if (geofence.screenCoordinates.length >= 3) {
        if (isPointInPolygon(screenX, screenY, geofence.screenCoordinates)) {
          return {
            type: 'geofence',
            id: geofence.id,
            screenX,
            screenY,
            distancePixels: 0,
          };
        }
      }
    }

    return null;
  }

  destroy(): void {
    this._isInitialized = false;
    this.canvas = null;
  }
}

export function isPointInPolygon(
  x: number,
  y: number,
  polygon: Array<{ x: number; y: number }>
): boolean {
  let inside = false;
  for (let i = 0, j = polygon.length - 1; i < polygon.length; j = i++) {
    const xi = polygon[i].x;
    const yi = polygon[i].y;
    const xj = polygon[j].x;
    const yj = polygon[j].y;

    const intersect = yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi;
    if (intersect) inside = !inside;
  }
  return inside;
}
