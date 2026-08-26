import { useCallback, useEffect, useRef, useState } from 'react';
import { getAlerts } from '../api/alerts';
import { getGeofences } from '../api/geofences';
import { getTimeline } from '../api/history';
import { getSensors } from '../api/sensors';
import { getThreats } from '../api/threats';
import { getTracks } from '../api/tracks';
import { useAuth } from '../context/AuthContext';
import { Alert, Geofence, Sensor, ThreatAssessment, TimelineItem, Track } from '../types';

export interface OperationalDataState {
  tracks: Track[];
  sensors: Sensor[];
  geofences: Geofence[];
  alerts: Alert[];
  threats: ThreatAssessment[];
  timeline: TimelineItem[];
  lastUpdated: Date | null;
  isLoading: boolean;
  isRefreshing: boolean;
  isStale: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

export interface UseOperationalDataOptions {
  autoRefreshIntervalMs?: number; // Default: 15000ms (15 seconds) - conservative, non-aggressive
  enabled?: boolean;
}

export function useOperationalData(options: UseOperationalDataOptions = {}): OperationalDataState {
  const { autoRefreshIntervalMs = 15000, enabled = true } = options;
  const { hasPermission } = useAuth();

  const [tracks, setTracks] = useState<Track[]>([]);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [threats, setThreats] = useState<ThreatAssessment[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);

  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [isStale, setIsStale] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const abortControllerRef = useRef<AbortController | null>(null);
  const isMountedRef = useRef<boolean>(true);

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, []);

  const fetchOperationalData = useCallback(async () => {
    if (!enabled) return;

    // Abort previous in-flight request to prevent race conditions or request storms
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    if (lastUpdated) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const promises: Promise<unknown>[] = [];

      // 1. Tracks (tracks.read)
      if (hasPermission('tracks.read')) {
        promises.push(
          getTracks({ limit: 100 }).then((res) => {
            if (isMountedRef.current && !controller.signal.aborted) {
              setTracks(res.items || []);
            }
          })
        );
      }

      // 2. Sensors (sensors.read)
      if (hasPermission('sensors.read')) {
        promises.push(
          getSensors({ limit: 100 }).then((res) => {
            if (isMountedRef.current && !controller.signal.aborted) {
              setSensors(res.items || []);
            }
          })
        );
      }

      // 3. Geofences (scenarios.read)
      if (hasPermission('scenarios.read')) {
        promises.push(
          getGeofences({ limit: 50 }).then((res) => {
            if (isMountedRef.current && !controller.signal.aborted) {
              setGeofences(res.items || []);
            }
          })
        );
      }

      // 4. Alerts (alerts.read)
      if (hasPermission('alerts.read')) {
        promises.push(
          getAlerts({ limit: 50 }).then((res) => {
            if (isMountedRef.current && !controller.signal.aborted) {
              setAlerts(res.items || []);
            }
          })
        );
      }

      // 5. Threats (threats.read)
      if (hasPermission('threats.read')) {
        promises.push(
          getThreats({ limit: 50 }).then((res) => {
            if (isMountedRef.current && !controller.signal.aborted) {
              setThreats(res.items || []);
            }
          })
        );
      }

      // 6. Timeline (operational read)
      promises.push(
        getTimeline({ limit: 50 }).then((res) => {
          if (isMountedRef.current && !controller.signal.aborted) {
            setTimeline(res.items || []);
          }
        })
      );

      const results = await Promise.allSettled(promises);
      if (!isMountedRef.current || controller.signal.aborted) return;

      const hasRejections = results.some((r) => r.status === 'rejected');
      if (hasRejections) {
        setIsStale(true);
        // Stale-while-refresh: keep previous data, flag stale warning
        const rejectedReason = results.find((r) => r.status === 'rejected') as PromiseRejectedResult;
        const msg = rejectedReason?.reason instanceof Error ? rejectedReason.reason.message : 'Partial refresh failure';
        setError(msg);
      } else {
        setIsStale(false);
        setLastUpdated(new Date());
        setError(null);
      }
    } catch (err: unknown) {
      if (!isMountedRef.current || controller.signal.aborted) return;
      setIsStale(true);
      const msg = err instanceof Error ? err.message : 'Operational state query failed';
      setError(msg);
    } finally {
      if (isMountedRef.current && !controller.signal.aborted) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [enabled, hasPermission, lastUpdated]);

  useEffect(() => {
    fetchOperationalData();
  }, [fetchOperationalData]);

  // Restrained background auto-refresh
  useEffect(() => {
    if (!enabled || autoRefreshIntervalMs <= 0) return;

    const interval = setInterval(() => {
      fetchOperationalData();
    }, autoRefreshIntervalMs);

    return () => clearInterval(interval);
  }, [enabled, autoRefreshIntervalMs, fetchOperationalData]);

  return {
    tracks,
    sensors,
    geofences,
    alerts,
    threats,
    timeline,
    lastUpdated,
    isLoading,
    isRefreshing,
    isStale,
    error,
    refresh: fetchOperationalData,
  };
}
