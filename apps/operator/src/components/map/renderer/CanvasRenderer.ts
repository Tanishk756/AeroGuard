/**
 * High-Performance HTML5 2D Batch Tactical Renderer for AeroGuard MAP2
 */

import { BaseMapRenderer } from './MapRenderer';
import {
  RenderGeofenceItem,
  RenderPredictionItem,
  RenderScene,
  RenderSensorItem,
  RenderTrackItem,
  RenderTrackTrail,
  RendererType,
} from './types';

export class CanvasRenderer extends BaseMapRenderer {
  readonly type: RendererType = 'CANVAS';
  private ctx: CanvasRenderingContext2D | null = null;

  async initialize(canvas: HTMLCanvasElement): Promise<boolean> {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d', {
      alpha: true,
      desynchronized: true,
    });

    if (!this.ctx) {
      this._isInitialized = false;
      return false;
    }

    this._isInitialized = true;
    const dpr = typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1;
    this.resize(canvas.clientWidth || 800, canvas.clientHeight || 600);
    return true;
  }

  render(scene: RenderScene): void {
    if (!this.ctx || !this.canvas) return;

    const ctx = this.ctx;
    const { width, height, devicePixelRatio: dpr } = scene.viewport;

    // Reset and scale for High-DPI
    ctx.save();
    ctx.scale(dpr, dpr);
    ctx.clearRect(0, 0, width, height);

    // 1. Render Grid Layer
    if (scene.layers.grid) {
      this.renderGrid(ctx, scene);
    }

    // 2. Render Range Rings
    if (scene.layers.rangeRings) {
      this.renderRangeRings(ctx, scene);
    }

    // 3. Render Geofences
    if (scene.layers.geofences) {
      this.renderGeofences(ctx, scene.geofences);
    }

    // 4. Render Sensor Coverage
    if (scene.layers.sensors) {
      this.renderSensors(ctx, scene.sensors);
    }

    // 5. Render Track Trails
    if (scene.layers.trajectories) {
      this.renderTrails(ctx, scene.trails);
    }

    // 6. Render AI Forward Trajectory Predictions
    if (scene.layers.trajectories && scene.prediction) {
      this.renderPrediction(ctx, scene.prediction);
    }

    // 7. Render Track Markers
    if (scene.layers.tracks) {
      this.renderTracks(ctx, scene.tracks, scene.layers.labels);
    }

    ctx.restore();
  }

  private renderGrid(ctx: CanvasRenderingContext2D, scene: RenderScene): void {
    const { width, height } = scene.viewport;
    ctx.save();
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.12)';
    ctx.lineWidth = 0.8;
    ctx.setLineDash([2, 4]);

    const GRID_SIZE = 80;
    ctx.beginPath();
    for (let x = GRID_SIZE; x < width; x += GRID_SIZE) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, height);
    }
    for (let y = GRID_SIZE; y < height; y += GRID_SIZE) {
      ctx.moveTo(0, y);
      ctx.lineTo(width, y);
    }
    ctx.stroke();
    ctx.restore();
  }

  private renderRangeRings(ctx: CanvasRenderingContext2D, scene: RenderScene): void {
    const { width, height, zoom } = scene.viewport;
    const centerX = width / 2 + scene.viewport.panOffsetX;
    const centerY = height / 2 + scene.viewport.panOffsetY;

    const BASE_SCALE = 2500 * zoom;
    const cosLat = Math.cos((scene.viewport.centerLat * Math.PI) / 180);
    const pixelsPerMeter = (BASE_SCALE * cosLat) / ((2 * Math.PI * 6371000) / 360);

    const distances = [500, 1000, 2000, 5000];

    ctx.save();
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.18)';
    ctx.fillStyle = 'rgba(56, 189, 248, 0.5)';
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.font = '9px monospace';

    for (const meters of distances) {
      const radius = meters * pixelsPerMeter;
      if (radius > 15 && radius < Math.max(width, height) * 1.5) {
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, Math.PI * 2);
        ctx.stroke();
        ctx.fillText(`${meters}m`, centerX + radius + 4, centerY - 2);
      }
    }

    // Viewport Reticle
    ctx.setLineDash([]);
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.6)';
    ctx.beginPath();
    ctx.arc(centerX, centerY, 4, 0, Math.PI * 2);
    ctx.moveTo(centerX - 10, centerY);
    ctx.lineTo(centerX + 10, centerY);
    ctx.moveTo(centerX, centerY - 10);
    ctx.lineTo(centerX, centerY + 10);
    ctx.stroke();

    ctx.restore();
  }

  private renderGeofences(ctx: CanvasRenderingContext2D, geofences: RenderGeofenceItem[]): void {
    ctx.save();

    for (const g of geofences) {
      if (g.screenCoordinates.length === 0) continue;

      ctx.beginPath();
      const first = g.screenCoordinates[0];
      ctx.moveTo(first.x, first.y);
      for (let i = 1; i < g.screenCoordinates.length; i++) {
        ctx.lineTo(g.screenCoordinates[i].x, g.screenCoordinates[i].y);
      }
      ctx.closePath();

      if (g.status === 'SELECTED') {
        ctx.fillStyle = 'rgba(56, 189, 248, 0.15)';
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 2;
        ctx.setLineDash([4, 2]);
      } else if (g.status === 'WARNING') {
        ctx.fillStyle = 'rgba(239, 68, 68, 0.18)';
        ctx.strokeStyle = '#ef4444';
        ctx.lineWidth = 2;
        ctx.setLineDash([]);
      } else if (g.status === 'DISABLED') {
        ctx.fillStyle = 'rgba(100, 116, 139, 0.05)';
        ctx.strokeStyle = 'rgba(100, 116, 139, 0.4)';
        ctx.lineWidth = 1;
        ctx.setLineDash([2, 4]);
      } else {
        // ENABLED
        ctx.fillStyle = 'rgba(245, 158, 11, 0.08)';
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.7)';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([]);
      }

      ctx.fill();
      ctx.stroke();

      // Label
      if (first) {
        ctx.font = '10px monospace';
        ctx.fillStyle = g.status === 'SELECTED' ? '#38bdf8' : g.status === 'WARNING' ? '#ef4444' : 'rgba(245, 158, 11, 0.9)';
        ctx.fillText(`⬡ ${g.name}`, first.x + 4, first.y - 4);
      }
    }

    ctx.restore();
  }

  private renderSensors(ctx: CanvasRenderingContext2D, sensors: RenderSensorItem[]): void {
    ctx.save();

    for (const s of sensors) {
      // Coverage Circle
      if (s.rangeRadiusPixels && s.rangeRadiusPixels > 5) {
        ctx.beginPath();
        ctx.arc(s.screenX, s.screenY, s.rangeRadiusPixels, 0, Math.PI * 2);
        ctx.fillStyle = s.isSelected ? 'rgba(34, 197, 94, 0.08)' : 'rgba(34, 197, 94, 0.03)';
        ctx.strokeStyle = s.isSelected ? '#22c55e' : 'rgba(34, 197, 94, 0.35)';
        ctx.lineWidth = s.isSelected ? 1.5 : 1;
        ctx.setLineDash([3, 3]);
        ctx.fill();
        ctx.stroke();
      }

      // Sensor Node Marker
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(s.screenX, s.screenY, s.isSelected ? 6 : 4.5, 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(15, 23, 42, 0.9)';
      ctx.strokeStyle = s.status === 'ACTIVE' ? '#22c55e' : '#eab308';
      ctx.lineWidth = 1.5;
      ctx.fill();
      ctx.stroke();

      // Center Core
      ctx.beginPath();
      ctx.arc(s.screenX, s.screenY, 2, 0, Math.PI * 2);
      ctx.fillStyle = s.status === 'ACTIVE' ? '#22c55e' : '#eab308';
      ctx.fill();

      // Label
      ctx.font = '9px monospace';
      ctx.fillStyle = s.isSelected ? '#22c55e' : 'rgba(148, 163, 184, 0.8)';
      ctx.fillText(`📡 ${s.name}`, s.screenX + 8, s.screenY + 3);
    }

    ctx.restore();
  }

  private renderTrails(ctx: CanvasRenderingContext2D, trails: RenderTrackTrail[]): void {
    ctx.save();

    for (const trail of trails) {
      if (trail.points.length < 2) continue;

      ctx.beginPath();
      ctx.moveTo(trail.points[0].screenX, trail.points[0].screenY);
      for (let i = 1; i < trail.points.length; i++) {
        ctx.lineTo(trail.points[i].screenX, trail.points[i].screenY);
      }
      ctx.strokeStyle = '#38bdf8';
      ctx.lineWidth = 1.5;
      ctx.setLineDash([3, 3]);
      ctx.stroke();

      // Nodes
      for (const pt of trail.points) {
        ctx.beginPath();
        ctx.arc(pt.screenX, pt.screenY, 2, 0, Math.PI * 2);
        ctx.fillStyle = `rgba(56, 189, 248, ${pt.alpha})`;
        ctx.fill();
      }
    }

    ctx.restore();
  }

  private renderPrediction(ctx: CanvasRenderingContext2D, prediction: RenderPredictionItem): void {
    ctx.save();
    const waypoints = prediction.waypoints;
    if (waypoints.length === 0) return;

    // Projected flight line
    ctx.beginPath();
    ctx.moveTo(waypoints[0].screenX, waypoints[0].screenY);
    for (let i = 1; i < waypoints.length; i++) {
      ctx.lineTo(waypoints[i].screenX, waypoints[i].screenY);
    }
    ctx.strokeStyle = '#38bdf8';
    ctx.lineWidth = 2;
    ctx.setLineDash([4, 2]);
    ctx.stroke();

    // Waypoint nodes & uncertainty envelopes
    for (let i = 0; i < waypoints.length; i++) {
      const wp = waypoints[i];
      const isKeyNode = i === Math.floor(waypoints.length / 2) || i === waypoints.length - 1;

      // Uncertainty ring
      ctx.beginPath();
      ctx.arc(wp.screenX, wp.screenY, Math.max(4, Math.min(25, wp.uncertaintyRadiusPixels * 0.15)), 0, Math.PI * 2);
      ctx.fillStyle = 'rgba(56, 189, 248, 0.08)';
      ctx.strokeStyle = 'rgba(56, 189, 248, 0.5)';
      ctx.lineWidth = 1;
      ctx.setLineDash([2, 2]);
      ctx.fill();
      ctx.stroke();

      // Waypoint dot
      ctx.setLineDash([]);
      ctx.beginPath();
      ctx.arc(wp.screenX, wp.screenY, isKeyNode ? 3.5 : 2, 0, Math.PI * 2);
      ctx.fillStyle = '#38bdf8';
      ctx.fill();

      // Time tag label
      if (isKeyNode) {
        ctx.font = '9px monospace';
        ctx.fillStyle = '#38bdf8';
        ctx.fillText(`+${wp.timeOffsetSeconds}s`, wp.screenX + 6, wp.screenY - 4);
      }
    }

    ctx.restore();
  }

  private renderTracks(ctx: CanvasRenderingContext2D, tracks: RenderTrackItem[], showLabels: boolean): void {
    ctx.save();
    const isDense = tracks.length > 80;

    for (let i = 0; i < tracks.length; i++) {
      const track = tracks[i];
      const { screenX: x, screenY: y, isSelected, heading, velocity, altitude } = track;

      // 1. Anomaly Halo Indicator (if anomalyScore >= 30)
      if (track.anomalyScore && track.anomalyScore >= 30) {
        ctx.beginPath();
        ctx.arc(x, y, 14, 0, Math.PI * 2);
        const haloColor =
          track.anomalyScore >= 80
            ? 'rgba(239, 68, 68, 0.25)'
            : track.anomalyScore >= 60
            ? 'rgba(251, 146, 60, 0.25)'
            : 'rgba(234, 179, 8, 0.25)';
        ctx.fillStyle = haloColor;
        ctx.fill();
      }

      // 2. Selection Ring
      if (isSelected) {
        ctx.beginPath();
        ctx.arc(x, y, 11, 0, Math.PI * 2);
        ctx.strokeStyle = '#38bdf8';
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 2]);
        ctx.stroke();
      }

      // 3. Track Marker Chevron / Circle
      const baseColor =
        track.isThreatElevated
          ? '#ef4444'
          : track.anomalyScore && track.anomalyScore >= 60
          ? '#fb923c'
          : isSelected
          ? '#38bdf8'
          : '#22c55e';

      ctx.setLineDash([]);
      if (heading != null) {
        // Directional Chevron
        const rad = (heading * Math.PI) / 180;
        ctx.save();
        ctx.translate(x, y);
        ctx.rotate(rad);

        ctx.beginPath();
        ctx.moveTo(0, -8);
        ctx.lineTo(6, 6);
        ctx.lineTo(0, 3);
        ctx.lineTo(-6, 6);
        ctx.closePath();

        ctx.fillStyle = baseColor;
        ctx.fill();
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.lineWidth = 1;
        ctx.stroke();
        ctx.restore();
      } else {
        // Standard Circular Marker
        ctx.beginPath();
        ctx.arc(x, y, 5, 0, Math.PI * 2);
        ctx.fillStyle = baseColor;
        ctx.fill();
        ctx.strokeStyle = 'rgba(15, 23, 42, 0.9)';
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // 4. Track Callout Labels (Throttled under high density unless selected or threat elevated)
      const shouldDrawLabel = (showLabels && (!isDense || isSelected || track.isThreatElevated || (track.anomalyScore && track.anomalyScore >= 60))) || isSelected;

      if (shouldDrawLabel) {
        ctx.font = '10px monospace';
        ctx.fillStyle = isSelected ? '#38bdf8' : 'rgba(226, 232, 240, 0.9)';
        ctx.fillText(track.id, x + 9, y - 5);

        if (velocity != null || altitude != null) {
          ctx.font = '8.5px monospace';
          ctx.fillStyle = 'rgba(148, 163, 184, 0.85)';
          const altStr = altitude != null ? `${altitude.toFixed(0)}m` : '';
          const velStr = velocity != null ? `${velocity.toFixed(0)}m/s` : '';
          const subText = [altStr, velStr].filter(Boolean).join(' • ');
          if (subText) {
            ctx.fillText(subText, x + 9, y + 6);
          }
        }
      }
    }

    ctx.restore();
  }
}
