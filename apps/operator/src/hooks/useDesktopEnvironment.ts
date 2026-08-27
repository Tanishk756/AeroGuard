import { useEffect, useState, useCallback } from 'react';
import { getCurrentWindow } from '@tauri-apps/api/window';
import {
  isTauri,
  isWindowMaximized,
  minimizeWindow,
  maximizeWindow,
  unmaximizeWindow,
  toggleMaximizeWindow,
  closeWindow,
  toggleFullscreen,
} from '../api/desktop';
import { getHealth } from '../api/system';

export interface DesktopEnvironmentState {
  isDesktop: boolean;
  isMaximized: boolean;
  isOnline: boolean;
  minimize: () => Promise<void>;
  maximize: () => Promise<void>;
  unmaximize: () => Promise<void>;
  toggleMaximize: () => Promise<void>;
  close: () => Promise<void>;
  toggleFullscreen: () => Promise<void>;
  checkHealth: () => Promise<void>;
}

export function useDesktopEnvironment(): DesktopEnvironmentState {
  const [isDesktop] = useState<boolean>(() => isTauri());
  const [isMaximized, setIsMaximized] = useState<boolean>(false);
  const [isOnline, setIsOnline] = useState<boolean>(true);

  const checkHealth = useCallback(async () => {
    try {
      const res = await getHealth();
      setIsOnline(res.status === 'healthy' || res.status === 'degraded');
    } catch {
      setIsOnline(false);
    }
  }, []);

  const handleToggleMaximize = useCallback(async () => {
    if (!isDesktop) return;
    const nextMaximized = await toggleMaximizeWindow();
    setIsMaximized(nextMaximized);
  }, [isDesktop]);

  const handleMinimize = useCallback(async () => {
    await minimizeWindow();
  }, []);

  const handleMaximize = useCallback(async () => {
    await maximizeWindow();
    setIsMaximized(true);
  }, []);

  const handleUnmaximize = useCallback(async () => {
    await unmaximizeWindow();
    setIsMaximized(false);
  }, []);

  const handleClose = useCallback(async () => {
    await closeWindow();
  }, []);

  const handleToggleFullscreen = useCallback(async () => {
    await toggleFullscreen();
  }, []);

  useEffect(() => {
    // Initial health check
    checkHealth();
    const healthInterval = setInterval(checkHealth, 15000);

    let unlistenResize: (() => void) | undefined;

    if (isDesktop) {
      // Sync initial maximized state
      isWindowMaximized().then(setIsMaximized).catch(() => setIsMaximized(false));

      try {
        const win = getCurrentWindow();
        win.onResized(() => {
          isWindowMaximized().then(setIsMaximized).catch(() => {});
        }).then((unlisten) => {
          unlistenResize = unlisten;
        }).catch(() => {});
      } catch (err) {
        console.warn('[useDesktopEnvironment] Failed to register resize listener:', err);
      }
    }

    return () => {
      clearInterval(healthInterval);
      if (unlistenResize) {
        unlistenResize();
      }
    };
  }, [isDesktop, checkHealth]);

  return {
    isDesktop,
    isMaximized,
    isOnline,
    minimize: handleMinimize,
    maximize: handleMaximize,
    unmaximize: handleUnmaximize,
    toggleMaximize: handleToggleMaximize,
    close: handleClose,
    toggleFullscreen: handleToggleFullscreen,
    checkHealth,
  };
}
