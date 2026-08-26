import React, { createContext, useCallback, useContext, useEffect, useState } from 'react';
import { getHealth, getSystemInfo } from '../api/system';
import { SystemHealthResponse, SystemInfoResponse } from '../types';
import { useAuth } from './AuthContext';

interface SystemContextValue {
  isHealthy: boolean;
  isDbHealthy: boolean;
  systemInfo: SystemInfoResponse | null;
  isLoading: boolean;
  error: string | null;
  lastChecked: Date | null;
  refreshHealth: () => Promise<void>;
}

const SystemContext = createContext<SystemContextValue | undefined>(undefined);

export const SystemProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { hasPermission, user } = useAuth();
  const [isHealthy, setIsHealthy] = useState<boolean>(false);
  const [isDbHealthy, setIsDbHealthy] = useState<boolean>(false);
  const [systemInfo, setSystemInfo] = useState<SystemInfoResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);

  const checkSystem = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const health: SystemHealthResponse = await getHealth();
      setIsHealthy(health.status === 'ok');
      setIsDbHealthy(health.database === 'ok');
      setLastChecked(new Date());

      // Only attempt to fetch system info if authenticated user possesses 'system.read' permission
      if (hasPermission('system.read')) {
        try {
          const info = await getSystemInfo();
          setSystemInfo(info);
        } catch {
          // If system info fails despite permission, preserve null without breaking health
          setSystemInfo(null);
        }
      } else {
        setSystemInfo(null);
      }
    } catch (err: unknown) {
      setIsHealthy(false);
      setIsDbHealthy(false);
      const message = err instanceof Error ? err.message : 'Backend unreachable';
      setError(message);
    } finally {
      setIsLoading(false);
    }
  }, [hasPermission]);

  useEffect(() => {
    checkSystem();
  }, [checkSystem, user]);

  const value: SystemContextValue = {
    isHealthy,
    isDbHealthy,
    systemInfo,
    isLoading,
    error,
    lastChecked,
    refreshHealth: checkSystem,
  };

  return <SystemContext.Provider value={value}>{children}</SystemContext.Provider>;
};

export const useSystem = (): SystemContextValue => {
  const context = useContext(SystemContext);
  if (!context) {
    throw new Error('useSystem must be used within a SystemProvider');
  }
  return context;
};
