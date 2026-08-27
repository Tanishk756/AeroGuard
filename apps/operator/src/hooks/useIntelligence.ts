/**
 * AeroGuard Hook for Multi-Track Defensive Intelligence State & Realtime Streaming
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getMultiTrackIntelligenceSummary } from '../api/intelligence';
import { useAuth } from '../context/AuthContext';
import {
  MultiTrackIntelligenceSummary,
  RealtimeEventEnvelope,
  TrackGroup,
  ThreatPriorityAssessment,
} from '../types';
import { useWebSocketStream } from './useWebSocketStream';

export interface UseIntelligenceOptions {
  autoRefreshIntervalMs?: number;
  enabled?: boolean;
  enableStreaming?: boolean;
  trackId?: string;
  groupId?: string;
  minPriorityLevel?: string;
  minPriorityScore?: number;
}

export interface IntelligenceState {
  summary: MultiTrackIntelligenceSummary | null;
  groups: TrackGroup[];
  priorities: ThreatPriorityAssessment[];
  selectedTrackId: string | null;
  selectedGroupId: string | null;
  isLoading: boolean;
  isRefreshing: boolean;
  error: string | null;
  lastUpdated: Date | null;
  setSelectedTrackId: (id: string | null) => void;
  setSelectedGroupId: (id: string | null) => void;
  refresh: () => Promise<void>;
}

export function useIntelligence(options: UseIntelligenceOptions = {}): IntelligenceState {
  const {
    autoRefreshIntervalMs = 15000,
    enabled = true,
    enableStreaming = true,
    trackId,
    groupId,
    minPriorityLevel,
    minPriorityScore,
  } = options;

  const { hasPermission, user } = useAuth();

  const [summary, setSummary] = useState<MultiTrackIntelligenceSummary | null>(null);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(trackId || null);
  const [selectedGroupId, setSelectedGroupId] = useState<string | null>(groupId || null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isRefreshing, setIsRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);

  const isMountedRef = useRef<boolean>(true);
  const abortControllerRef = useRef<AbortController | null>(null);
  const lastEventTimestampRef = useRef<number>(0);

  const fetchIntelligence = useCallback(async () => {
    if (!enabled || !hasPermission('tracks.read')) {
      setIsLoading(false);
      return;
    }

    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    const controller = new AbortController();
    abortControllerRef.current = controller;

    if (summary !== null) {
      setIsRefreshing(true);
    } else {
      setIsLoading(true);
    }
    setError(null);

    try {
      const data = await getMultiTrackIntelligenceSummary({
        track_id: trackId,
        group_id: groupId,
        min_priority_level: minPriorityLevel,
        min_priority_score: minPriorityScore,
      });

      if (isMountedRef.current && !controller.signal.aborted) {
        setSummary(data);
        const evalDate = new Date(data.evaluated_at);
        setLastUpdated(evalDate);
        lastEventTimestampRef.current = evalDate.getTime();
      }
    } catch (err: unknown) {
      if (controller.signal.aborted) return;
      const msg = err instanceof Error ? err.message : 'Failed to fetch defensive intelligence';
      setError(msg);
    } finally {
      if (isMountedRef.current && !controller.signal.aborted) {
        setIsLoading(false);
        setIsRefreshing(false);
      }
    }
  }, [enabled, hasPermission, trackId, groupId, minPriorityLevel, minPriorityScore, summary]);

  // Initial and param change fetch
  useEffect(() => {
    isMountedRef.current = true;
    fetchIntelligence();

    return () => {
      isMountedRef.current = false;
      if (abortControllerRef.current) {
        abortControllerRef.current.abort();
      }
    };
  }, [fetchIntelligence]);

  // Periodic polling fallback
  useEffect(() => {
    if (!enabled || autoRefreshIntervalMs <= 0) return;

    const intervalId = setInterval(() => {
      fetchIntelligence();
    }, autoRefreshIntervalMs);

    return () => clearInterval(intervalId);
  }, [enabled, autoRefreshIntervalMs, fetchIntelligence]);

  // Realtime WebSocket event handling
  const handleWebSocketMessage = useCallback((envelope: RealtimeEventEnvelope) => {
    if (!isMountedRef.current) return;

    if (envelope.event_type === 'ai.summary') {
      const payload = envelope.payload as unknown as Partial<MultiTrackIntelligenceSummary>;
      if (!payload || !payload.evaluated_at) return;

      const eventTime = new Date(payload.evaluated_at).getTime();
      // Stale event protection: reject events older than our newest state
      if (eventTime < lastEventTimestampRef.current) {
        return;
      }

      // Check if multi-track summary payload
      if (Array.isArray(payload.groups) && Array.isArray(payload.priorities)) {
        lastEventTimestampRef.current = eventTime;
        setSummary(payload as MultiTrackIntelligenceSummary);
        setLastUpdated(new Date(eventTime));
      }
    }
  }, []);

  useWebSocketStream({
    channel: 'operational',
    enabled: enabled && enableStreaming && !!user,
    onMessage: handleWebSocketMessage,
  });

  return {
    summary,
    groups: summary?.groups || [],
    priorities: summary?.priorities || [],
    selectedTrackId,
    selectedGroupId,
    isLoading,
    isRefreshing,
    error,
    lastUpdated,
    setSelectedTrackId,
    setSelectedGroupId,
    refresh: fetchIntelligence,
  };
}
