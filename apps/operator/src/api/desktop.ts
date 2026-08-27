/**
 * AeroGuard Desktop API Bridge (Tauri 2)
 *
 * Provides strongly-typed, safely fallbacked desktop window and environment abstractions.
 * All functions gracefully no-op or return safe defaults in standard web browsers.
 */
import { getCurrentWindow } from '@tauri-apps/api/window';

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
