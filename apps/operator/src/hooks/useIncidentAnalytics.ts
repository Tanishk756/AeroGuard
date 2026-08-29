/**
 * AeroGuard Incident Analytics Hook
 * Stage IM1-G: Incident Analytics, Reporting & Operational Review
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getIncidentAnalytics } from '../api/incidents';
import {
  IncidentAnalyticsFilterParams,
  IncidentAnalyticsResponse,
  IncidentSeverity,
  IncidentStatus,
} from '../types';
import { useWebSocketStream } from './useWebSocketStream';

export type TimeWindowPreset = 'LAST_24H' | 'LAST_7D' | 'LAST_30D' | 'CUSTOM';

function calculatePresetDates(preset: TimeWindowPreset): { start?: string; end?: string } {
  if (preset === 'CUSTOM') return {};

  const now = new Date();
  const end = now.toISOString();
  let start: string;

  if (preset === 'LAST_24H') {
    const d = new Date(now.getTime() - 24 * 60 * 60 * 1000);
    start = d.toISOString();
  } else if (preset === 'LAST_7D') {
    const d = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
    start = d.toISOString();
  } else {
    // LAST_30D
    const d = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
    start = d.toISOString();
  }

  return { start, end };
}

export function useIncidentAnalytics(initialPreset: TimeWindowPreset = 'LAST_7D') {
  const [preset, setPresetState] = useState<TimeWindowPreset>(initialPreset);
  const [filterParams, setFilterParams] = useState<IncidentAnalyticsFilterParams>(() => ({
    ...calculatePresetDates(initialPreset),
    bucket_size: initialPreset === 'LAST_24H' ? 'hour' : 'day',
  }));

  const [analytics, setAnalytics] = useState<IncidentAnalyticsResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isStale, setIsStale] = useState<boolean>(false);

  const activeParamsRef = useRef(filterParams);
  activeParamsRef.current = filterParams;

  const fetchAnalytics = useCallback(async (paramsOverride?: IncidentAnalyticsFilterParams) => {
    setLoading(true);
    setError(null);
    try {
      const p = paramsOverride || activeParamsRef.current;
      const res = await getIncidentAnalytics(p);
      setAnalytics(res);
      setIsStale(false);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to fetch incident analytics';
      setError(msg);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics(filterParams);
  }, [fetchAnalytics, filterParams]);

  // Handle live WebSocket telemetry invalidation (mark stale without auto re-query spam)
  const debounceRef = useRef<NodeJS.Timeout | null>(null);

  useWebSocketStream({
    channel: 'operational',
    onMessage: (msg) => {
      if (typeof msg.event_type === 'string' && msg.event_type.startsWith('incident.')) {
        setIsStale(true);
        if (debounceRef.current) clearTimeout(debounceRef.current);
        debounceRef.current = setTimeout(() => {
          fetchAnalytics(activeParamsRef.current);
        }, 1500);
      }
    },
  });

  useEffect(() => {
    return () => {
      if (debounceRef.current) clearTimeout(debounceRef.current);
    };
  }, []);

  const setPreset = useCallback((newPreset: TimeWindowPreset) => {
    setPresetState(newPreset);
    if (newPreset !== 'CUSTOM') {
      const dates = calculatePresetDates(newPreset);
      const bSize: 'hour' | 'day' | 'week' = newPreset === 'LAST_24H' ? 'hour' : 'day';
      setFilterParams((prev) => ({
        ...prev,
        start: dates.start,
        end: dates.end,
        bucket_size: bSize,
      }));
    }
  }, []);

  const setFilters = useCallback((updates: Partial<IncidentAnalyticsFilterParams>) => {
    setFilterParams((prev) => ({
      ...prev,
      ...updates,
    }));
  }, []);

  const resetFilters = useCallback(() => {
    setPresetState('LAST_7D');
    setFilterParams({
      ...calculatePresetDates('LAST_7D'),
      bucket_size: 'day',
    });
  }, []);

  return {
    analytics,
    loading,
    error,
    isStale,
    preset,
    filters: filterParams,
    refresh: () => fetchAnalytics(),
    setPreset,
    setFilters,
    resetFilters,
  };
}
