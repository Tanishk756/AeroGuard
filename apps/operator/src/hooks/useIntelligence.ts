/**
 * AeroGuard Hook for Multi-Track Defensive Intelligence State & Realtime Streaming
 * Stage AI3-F: High-Density Telemetry Optimization, Animation-Frame Coalescing & Stale Event Protection
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import { getMultiTrackIntelligenceSummary } from '../api/intelligence';
import { useAuth } from '../context/AuthContext';
import {
  BehaviorClassification,
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
  const lastEventSequenceRef = useRef<number>(0);

  // In-memory accumulation buffer for high-density animation-frame coalescing
  const pendingSummaryRef = useRef<MultiTrackIntelligenceSummary | null>(null);
  const pendingPrioritiesRef = useRef<Map<string, ThreatPriorityAssessment>>(new Map());
  const pendingBehaviorsRef = useRef<Map<string, BehaviorClassification>>(new Map());
  const pendingGroupsRef = useRef<Map<string, TrackGroup>>(new Map());
  const rafIdRef = useRef<number | null>(null);

  // Flush pending coalesced telemetry updates into React state at next animation frame
  const flushPendingUpdates = useCallback(() => {
    if (!isMountedRef.current) {
      rafIdRef.current = null;
      return;
    }
    rafIdRef.current = null;

    setSummary((prev) => {
      let nextSummary: MultiTrackIntelligenceSummary;

      if (pendingSummaryRef.current) {
        nextSummary = pendingSummaryRef.current;
        pendingSummaryRef.current = null;
      } else if (prev) {
        nextSummary = { ...prev };
      } else {
        // No baseline summary yet
        return null;
      }

      // Apply coalesced granular priority updates
      if (pendingPrioritiesRef.current.size > 0) {
        const prioMap = new Map(nextSummary.priorities.map((p) => [p.track_id, p]));
        for (const [tid, prio] of pendingPrioritiesRef.current) {
          prioMap.set(tid, prio);
        }
        nextSummary.priorities = Array.from(prioMap.values());
        pendingPrioritiesRef.current.clear();
      }

      // Apply coalesced granular behavior updates
      if (pendingBehaviorsRef.current.size > 0) {
        const behMap = new Map(nextSummary.behaviors.map((b) => [b.track_id, b]));
        for (const [tid, beh] of pendingBehaviorsRef.current) {
          behMap.set(tid, beh);
        }
        nextSummary.behaviors = Array.from(behMap.values());
        pendingBehaviorsRef.current.clear();
      }

      // Apply coalesced granular group updates
      if (pendingGroupsRef.current.size > 0) {
        const grpMap = new Map(nextSummary.groups.map((g) => [g.group_id, g]));
        for (const [gid, grp] of pendingGroupsRef.current) {
          grpMap.set(gid, grp);
        }
        nextSummary.groups = Array.from(grpMap.values());
        pendingGroupsRef.current.clear();
      }

      return nextSummary;
    });

    setLastUpdated(new Date());
  }, []);

  const scheduleFlush = useCallback(() => {
    if (rafIdRef.current === null) {
      if (typeof window !== 'undefined' && typeof window.requestAnimationFrame === 'function') {
        rafIdRef.current = window.requestAnimationFrame(flushPendingUpdates);
      } else {
        rafIdRef.current = (setTimeout(flushPendingUpdates, 16) as unknown) as number;
      }
    }
  }, [flushPendingUpdates]);

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
      if (rafIdRef.current !== null) {
        if (typeof window !== 'undefined' && typeof window.cancelAnimationFrame === 'function') {
          window.cancelAnimationFrame(rafIdRef.current);
        } else {
          clearTimeout(rafIdRef.current);
        }
        rafIdRef.current = null;
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

  // Realtime WebSocket event handling with coalescing, monotonic sequence checks & stale protection
  const handleWebSocketMessage = useCallback((envelope: RealtimeEventEnvelope) => {
    if (!isMountedRef.current) return;

    // Monotonic sequence verification: reject stale / out-of-order events
    if (typeof envelope.sequence === 'number' && envelope.sequence > 0) {
      if (envelope.sequence <= lastEventSequenceRef.current) {
        return; // Stale or duplicate sequence
      }
      lastEventSequenceRef.current = envelope.sequence;
    }

    const payload = envelope.payload as Record<string, unknown>;
    if (!payload) return;

    // Timestamp check if available
    const timeStr = (payload.evaluated_at || payload.updated_at || envelope.timestamp) as string | undefined;
    if (timeStr) {
      const eventTime = new Date(timeStr).getTime();
      if (!isNaN(eventTime) && eventTime > 0) {
        if (eventTime < lastEventTimestampRef.current && !envelope.sequence) {
          return; // Stale timestamp when sequence is absent
        }
        if (eventTime > lastEventTimestampRef.current) {
          lastEventTimestampRef.current = eventTime;
        }
      }
    }

    if (envelope.event_type === 'ai.summary') {
      const summaryPayload = payload as unknown as Partial<MultiTrackIntelligenceSummary>;
      if (Array.isArray(summaryPayload.groups) && Array.isArray(summaryPayload.priorities)) {
        pendingSummaryRef.current = summaryPayload as MultiTrackIntelligenceSummary;
        scheduleFlush();
      }
    } else if (envelope.event_type === 'ai.priority' || envelope.event_type === 'ai.priority.updated') {
      const prioPayload = payload as unknown as ThreatPriorityAssessment;
      if (prioPayload && prioPayload.track_id) {
        pendingPrioritiesRef.current.set(prioPayload.track_id, prioPayload);
        scheduleFlush();
      }
    } else if (envelope.event_type === 'ai.behavior' || envelope.event_type === 'ai.behavior.updated') {
      const behPayload = payload as unknown as BehaviorClassification;
      if (behPayload && behPayload.track_id) {
        pendingBehaviorsRef.current.set(behPayload.track_id, behPayload);
        scheduleFlush();
      }
    } else if (envelope.event_type === 'ai.group' || envelope.event_type === 'ai.group.updated') {
      const grpPayload = payload as unknown as TrackGroup;
      if (grpPayload && grpPayload.group_id) {
        pendingGroupsRef.current.set(grpPayload.group_id, grpPayload);
        scheduleFlush();
      }
    }
  }, [scheduleFlush]);

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
