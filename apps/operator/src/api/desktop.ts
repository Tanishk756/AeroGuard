/**
 * AeroGuard Desktop API Bridge (Tauri 2)
 *
 * Provides strongly-typed, safely fallbacked desktop window, environment,
 * native notification, and system tray abstractions.
 * All functions gracefully no-op or return safe defaults in standard web browsers.
 */
import { getCurrentWindow } from '@tauri-apps/api/window';
import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification';
import { Alert } from '../types/alert';

export interface DesktopEnvironmentInfo {
  isDesktop: boolean;
  platform: 'windows' | 'browser';
  version: string;
}

/**
 * Checks whether the application is running inside a Tauri desktop webview.
 */
export function isTauri(): boolean {
  if (typeof window === 'undefined') return false;
  return Boolean(
    (window as unknown as { __TAURI_INTERNALS__?: unknown }).__TAURI_INTERNALS__ ||
    (window as unknown as { __TAURI__?: unknown }).__TAURI__
  );
}

/**
 * Minimizes the desktop window. No-ops in web browsers.
 */
export async function minimizeWindow(): Promise<void> {
  if (!isTauri()) return;
  try {
    const win = getCurrentWindow();
    await win.minimize();
  } catch (err) {
    console.warn('[DesktopBridge] Failed to minimize window:', err);
  }
}

/**
 * Maximizes the desktop window. No-ops in web browsers.
 */
export async function maximizeWindow(): Promise<void> {
  if (!isTauri()) return;
  try {
    const win = getCurrentWindow();
    await win.maximize();
  } catch (err) {
    console.warn('[DesktopBridge] Failed to maximize window:', err);
  }
}

/**
 * Unmaximizes / restores the desktop window. No-ops in web browsers.
 */
export async function unmaximizeWindow(): Promise<void> {
  if (!isTauri()) return;
  try {
    const win = getCurrentWindow();
    await win.unmaximize();
  } catch (err) {
    console.warn('[DesktopBridge] Failed to unmaximize window:', err);
  }
}

/**
 * Toggles window maximization. Returns the new maximized state (or false in browser).
 */
export async function toggleMaximizeWindow(): Promise<boolean> {
  if (!isTauri()) return false;
  try {
    const win = getCurrentWindow();
    await win.toggleMaximize();
    return await win.isMaximized();
  } catch (err) {
    console.warn('[DesktopBridge] Failed to toggle maximize:', err);
    return false;
  }
}

/**
 * Checks if the window is currently maximized. Always false in web browser.
 */
export async function isWindowMaximized(): Promise<boolean> {
  if (!isTauri()) return false;
  try {
    const win = getCurrentWindow();
    return await win.isMaximized();
  } catch {
    return false;
  }
}

/**
 * Closes the application window. No-ops in web browsers.
 */
export async function closeWindow(): Promise<void> {
  if (!isTauri()) return;
  try {
    const win = getCurrentWindow();
    await win.close();
  } catch (err) {
    console.warn('[DesktopBridge] Failed to close window:', err);
  }
}

/**
 * Toggles fullscreen mode. No-ops in web browsers.
 */
export async function toggleFullscreen(): Promise<boolean> {
  if (!isTauri()) return false;
  try {
    const win = getCurrentWindow();
    const isFull = await win.isFullscreen();
    await win.setFullscreen(!isFull);
    return !isFull;
  } catch (err) {
    console.warn('[DesktopBridge] Failed to toggle fullscreen:', err);
    return false;
  }
}

// ── Native Desktop Notification Bridge & In-Memory Deduplication ──

/**
 * In-memory bounded alert notification deduplication cache.
 */
export class AlertNotificationDeduplicator {
  private notifiedKeys = new Map<string, number>();
  private readonly maxCapacity: number;

  constructor(maxCapacity = 100) {
    this.maxCapacity = maxCapacity;
  }

  public makeKey(alert: Pick<Alert, 'id' | 'status' | 'severity'>): string {
    return `${alert.id}:${alert.status}:${alert.severity}`;
  }

  public shouldNotify(alert: Pick<Alert, 'id' | 'status' | 'severity'>): boolean {
    const key = this.makeKey(alert);
    if (this.notifiedKeys.has(key)) {
      return false;
    }

    if (this.notifiedKeys.size >= this.maxCapacity) {
      const entries = Array.from(this.notifiedKeys.entries());
      entries.sort((a, b) => a[1] - b[1]);
      for (let i = 0; i < Math.min(30, entries.length); i++) {
        this.notifiedKeys.delete(entries[i][0]);
      }
    }

    this.notifiedKeys.set(key, Date.now());
    return true;
  }

  public clear(): void {
    this.notifiedKeys.clear();
  }

  public size(): number {
    return this.notifiedKeys.size;
  }
}

export const alertDeduplicator = new AlertNotificationDeduplicator();

/**
 * Evaluates whether an alert meets the operational severity threshold (CRITICAL or HIGH)
 * and is in active OPEN state.
 */
export function isAlertSeverityEligible(alert: Pick<Alert, 'severity' | 'status'>): boolean {
  if (alert.status && alert.status !== 'OPEN') {
    return false;
  }
  const sev = (alert.severity || '').toUpperCase();
  return sev === 'CRITICAL' || sev === 'HIGH';
}

/**
 * Sanitizes notification message body to prevent accidental secret leakage and ensure clean toast rendering.
 */
export function sanitizeNotificationBody(text: string): string {
  if (!text) return '';
  let clean = text
    .replace(/(bearer\s+[a-zA-Z0-9._-]+)/gi, '[REDACTED]')
    .replace(/(password\s*=\s*\S+)/gi, 'password=[REDACTED]')
    .replace(/(token\s*=\s*\S+)/gi, 'token=[REDACTED]');

  if (clean.length > 200) {
    clean = clean.substring(0, 197) + '...';
  }
  return clean;
}

/**
 * Dispatches a native OS desktop notification if running in Tauri and permission is granted.
 * Safely no-ops in standard web browsers.
 */
export async function sendDesktopNotification(options: {
  title: string;
  body: string;
  id?: string;
}): Promise<boolean> {
  if (!isTauri()) return false;

  try {
    let hasPermission = await isPermissionGranted();
    if (!hasPermission) {
      const permission = await requestPermission();
      hasPermission = permission === 'granted';
    }

    if (hasPermission) {
      const sanitizedBody = sanitizeNotificationBody(options.body);
      await sendNotification({
        title: options.title,
        body: sanitizedBody,
      });
      return true;
    }
  } catch (err) {
    console.warn('[DesktopNotification] Failed to dispatch native notification:', err);
  }
  return false;
}

/**
 * Processes a list of operational alerts and emits native desktop notifications for eligible, unnotified items.
 */
export async function dispatchAlertNotifications(
  alerts: Alert[],
  isOnline = true
): Promise<number> {
  if (!isTauri() || !isOnline || !Array.isArray(alerts)) {
    return 0;
  }

  let notifiedCount = 0;
  for (const alert of alerts) {
    if (isAlertSeverityEligible(alert) && alertDeduplicator.shouldNotify(alert)) {
      const title = `🚨 [${alert.severity}] ${alert.type.replace(/_/g, ' ')}`;
      const body = alert.reason || `Operational alert triggered on ${alert.track_id || alert.sensor_id || 'airspace'}`;
      const sent = await sendDesktopNotification({ title, body, id: alert.id });
      if (sent) {
        notifiedCount++;
      }
    }
  }
  return notifiedCount;
}
