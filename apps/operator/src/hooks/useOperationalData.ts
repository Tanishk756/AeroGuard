import { useCallback, useEffect, useRef, useState } from 'react';
import { getAlerts } from '../api/alerts';
import { dispatchAlertNotifications } from '../api/desktop';
import { getGeofences } from '../api/geofences';
import { getTimeline } from '../api/history';
import { getSensors } from '../api/sensors';
import { getThreats } from '../api/threats';
import { getTracks } from '../api/tracks';
import { useAuth } from '../context/AuthContext';
import {
  Alert,
  Geofence,
  OperationalConnectionMode,
  RealtimeEventEnvelope,
  Sensor,
  StreamStatus,
  ThreatAssessment,
  TimelineItem,
  Track,
} from '../types';
import { useWebSocketStream } from './useWebSocketStream';

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
  connectionMode: OperationalConnectionMode;
  streamStatus: StreamStatus;
  latencyMs: number | null;
  refresh: () => Promise<void>;
}

export interface UseOperationalDataOptions {
  autoRefreshIntervalMs?: number; // Default: 15000ms fallback interval
  enabled?: boolean;
  enableStreaming?: boolean;
}

export function useOperationalData(options: UseOperationalDataOptions = {}): OperationalDataState {
  const {
    autoRefreshIntervalMs = 15000,
    enabled = true,
    enableStreaming = true,
  } = options;

  const { hasPermission, user } = useAuth();

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
  const pendingTracksRef = useRef<Map<string, Track>>(new Map());
  const rafIdRef = useRef<number | null>(null);

  const flushPendingTracks = useCallback(() => {
    if (!isMountedRef.current || pendingTracksRef.current.size === 0) {
      rafIdRef.current = null;
      return;
    }

    const updates = Array.from(pendingTracksRef.current.values());
    pendingTracksRef.current.clear();
    rafIdRef.current = null;

    setTracks((prev) => {
      const updateMap = new Map(updates.map((t) => [t.id, t]));
      const updatedList = prev.map((t) => {
        const up = updateMap.get(t.id);
        if (up) {
          updateMap.delete(t.id);
          return { ...t, ...up };
        }
        return t;
      });
      if (updateMap.size > 0) {
        return [...updateMap.values(), ...updatedList];
      }
      return updatedList;
    });
    setLastUpdated(new Date());
  }, []);

  const queueTrackUpdate = useCallback(
    (track: Track) => {
      pendingTracksRef.current.set(track.id, track);
      if (rafIdRef.current === null) {
        if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
          rafIdRef.current = window.requestAnimationFrame(flushPendingTracks);
        } else {
          rafIdRef.current = (setTimeout(flushPendingTracks, 16) as unknown) as number;
        }
      }
    },
    [flushPendingTracks]
  );

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
      if (rafIdRef.current !== null) {
        if (typeof window !== 'undefined' && typeof window.cancelAnimationFrame === 'function') {
          window.cancelAnimationFrame(rafIdRef.current);
        } else {
          clearTimeout(rafIdRef.current);
        }
        rafIdRef.current = null;
      }
    };
  }, []);

  const fetchOperationalData = useCallback(async () => {
    if (!enabled) return;

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
              const items = res.items || [];
              setAlerts(items);
              dispatchAlertNotifications(items).catch(() => {});
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

  // Handle incoming realtime operational WebSocket events
  const handleWebSocketMessage = useCallback(
    (envelope: RealtimeEventEnvelope) => {
      if (!isMountedRef.current) return;

      // Realtime Desktop Notifications for critical alerts / threats
      dispatchAlertNotifications([]).catch(() => {});

      switch (envelope.event_type) {
        case 'track.created':
        case 'track.updated': {
          const trackData = envelope.payload as unknown as Track;
          if (trackData && trackData.id) {
            queueTrackUpdate(trackData);
          }
          break;
        }
        case 'track.dropped': {
          const payload = envelope.payload as { id?: string };
          if (payload && payload.id) {
            pendingTracksRef.current.delete(payload.id);
            setTracks((prev) => prev.filter((t) => t.id !== payload.id));
            setLastUpdated(new Date());
          }
          break;
        }
        case 'alert.created': {
          const alertData = envelope.payload as unknown as Alert;
          if (alertData && alertData.id) {
            setAlerts((prev) => {
              const exists = prev.some((a) => a.id === alertData.id);
              if (exists) return prev;
              return [alertData, ...prev];
            });
            dispatchAlertNotifications([alertData]).catch(() => {});
            setLastUpdated(new Date());
          }
          break;
        }
        case 'alert.updated': {
          const alertData = envelope.payload as unknown as Alert;
          if (alertData && alertData.id) {
            setAlerts((prev) => {
              const idx = prev.findIndex((a) => a.id === alertData.id);
              if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = { ...updated[idx], ...alertData };
                return updated;
              }
              return [alertData, ...prev];
            });
            setLastUpdated(new Date());
          }
          break;
        }
        case 'threat.updated': {
          const threatData = envelope.payload as unknown as ThreatAssessment;
          if (threatData && threatData.id) {
            setThreats((prev) => {
              const idx = prev.findIndex((th) => th.id === threatData.id || th.track_id === threatData.track_id);
              if (idx >= 0) {
                const updated = [...prev];
                updated[idx] = { ...updated[idx], ...threatData };
                return updated;
              }
              return [threatData, ...prev];
            });
            setLastUpdated(new Date());
          }
          break;
        }
        default:
          break;
      }
    },
    [queueTrackUpdate]
  );

  const handleSequenceGap = useCallback(() => {
    // Reconcile full state via REST upon sequence gap
    fetchOperationalData();
  }, [fetchOperationalData]);

  const stream = useWebSocketStream({
    channel: 'operational',
    enabled: enabled && enableStreaming && !!user,
    onMessage: handleWebSocketMessage,
    onSequenceGap: handleSequenceGap,
  });

  // Reconcile state when stream transitions to CONNECTED
  const prevStreamStatusRef = useRef<StreamStatus>(stream.status);
  useEffect(() => {
    if (prevStreamStatusRef.current !== 'CONNECTED' && stream.status === 'CONNECTED') {
      fetchOperationalData();
    }
    prevStreamStatusRef.current = stream.status;
  }, [stream.status, fetchOperationalData]);

  // Initial fetch on mount
  useEffect(() => {
    fetchOperationalData();
  }, [fetchOperationalData]);

  // Compute operational connection mode
  const connectionMode: OperationalConnectionMode =
    stream.status === 'CONNECTED'
      ? 'STREAMING'
      : stream.status === 'CONNECTING'
      ? 'CONNECTING'
      : stream.status === 'RECONNECTING'
      ? 'RECONNECTING'
      : 'POLLING';

  // Adaptive background polling: fast (15s) when in POLLING mode, relaxed (60s) when STREAMING
  useEffect(() => {
    if (!enabled) return;

    const intervalMs = connectionMode === 'STREAMING' ? 60000 : autoRefreshIntervalMs;
    if (intervalMs <= 0) return;

    const interval = setInterval(() => {
      fetchOperationalData();
    }, intervalMs);

    return () => clearInterval(interval);
  }, [enabled, connectionMode, autoRefreshIntervalMs, fetchOperationalData]);

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
    connectionMode,
    streamStatus: stream.status,
    latencyMs: stream.latencyMs,
    refresh: fetchOperationalData,
  };
}
