/**
 * AeroGuard Incident Management State & Realtime Hook
 * Stage IM1-E: Operator Incident Workspace
 */

import { useCallback, useEffect, useRef, useState } from 'react';
import {
  acknowledgeIncident as apiAcknowledge,
  addIncidentNote as apiAddNote,
  assignIncident as apiAssign,
  closeIncident as apiClose,
  createIncident as apiCreate,
  deEscalateIncident as apiDeEscalate,
  escalateIncident as apiEscalate,
  getIncident as apiGetIncident,
  getIncidents as apiGetIncidents,
  getIncidentTimeline as apiGetTimeline,
  logDefensiveAction as apiLogAction,
  resolveIncident as apiResolve,
  triageIncident as apiTriage,
} from '../api/incidents';
import { useAuth } from '../context/AuthContext';
import {
  AcknowledgeIncidentRequest,
  AddIncidentNoteRequest,
  AssignIncidentRequest,
  CloseIncidentRequest,
  CreateIncidentRequest,
  DeEscalateIncidentRequest,
  EscalateIncidentRequest,
  Incident,
  IncidentEvent,
  IncidentEventType,
  IncidentFilterParams,
  IncidentRealtimePayload,
  IncidentSeverity,
  IncidentStatus,
  LogDefensiveActionRequest,
  RealtimeEventEnvelope,
  ResolveIncidentRequest,
  TriageIncidentRequest,
} from '../types';
import { useWebSocketStream } from './useWebSocketStream';

export interface UseIncidentsOptions {
  initialFilters?: IncidentFilterParams;
  autoRefreshIntervalMs?: number;
  enableStreaming?: boolean;
}

export interface UseIncidentsState {
  incidents: Incident[];
  total: number;
  selectedIncidentId: string | null;
  selectedIncident: Incident | null;
  timeline: IncidentEvent[];
  isLoading: boolean;
  isDetailLoading: boolean;
  isTimelineLoading: boolean;
  isMutating: boolean;
  error: string | null;
  filters: IncidentFilterParams;
  setFilters: (filters: Partial<IncidentFilterParams>) => void;
  selectIncident: (id: string | null) => void;
  refreshList: () => Promise<void>;
  refreshDetail: (id?: string) => Promise<void>;
  createIncident: (data: CreateIncidentRequest) => Promise<Incident>;
  acknowledgeIncident: (id: string, data?: AcknowledgeIncidentRequest) => Promise<Incident>;
  assignIncident: (id: string, data: AssignIncidentRequest) => Promise<Incident>;
  triageIncident: (id: string, data: TriageIncidentRequest) => Promise<Incident>;
  escalateIncident: (id: string, data: EscalateIncidentRequest) => Promise<Incident>;
  deEscalateIncident: (id: string, data: DeEscalateIncidentRequest) => Promise<Incident>;
  resolveIncident: (id: string, data: ResolveIncidentRequest) => Promise<Incident>;
  closeIncident: (id: string, data?: CloseIncidentRequest) => Promise<Incident>;
  addNote: (id: string, data: AddIncidentNoteRequest) => Promise<IncidentEvent>;
  logDefensiveAction: (id: string, data: LogDefensiveActionRequest) => Promise<IncidentEvent>;
}

export function useIncidents(options: UseIncidentsOptions = {}): UseIncidentsState {
  const { initialFilters = {}, enableStreaming = true } = options;
  const { hasPermission, user } = useAuth();
  const canReadIncidents = hasPermission('incidents.read');

  const [incidents, setIncidents] = useState<Incident[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [selectedIncidentId, setSelectedIncidentId] = useState<string | null>(null);
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [timeline, setTimeline] = useState<IncidentEvent[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [isDetailLoading, setIsDetailLoading] = useState<boolean>(false);
  const [isTimelineLoading, setIsTimelineLoading] = useState<boolean>(false);
  const [isMutating, setIsMutating] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFiltersState] = useState<IncidentFilterParams>(initialFilters);

  const isMountedRef = useRef<boolean>(true);
  const selectedIncidentIdRef = useRef<string | null>(selectedIncidentId);
  selectedIncidentIdRef.current = selectedIncidentId;
  const lastEventSequenceRef = useRef<number>(0);

  // In-memory queues for raf batching
  const pendingCreatedRef = useRef<IncidentRealtimePayload[]>([]);
  const pendingUpdatesRef = useRef<Map<string, IncidentRealtimePayload>>(new Map());
  const pendingTimelineRef = useRef<IncidentEvent[]>([]);
  const rafIdRef = useRef<number | null>(null);

  // Fetch list of incidents
  const fetchIncidents = useCallback(async () => {
    if (!canReadIncidents) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    setError(null);
    try {
      const res = await apiGetIncidents(filters);
      if (isMountedRef.current) {
        setIncidents(res.items);
        setTotal(res.total);
        // If there's a selected incident, make sure it remains synchronized or select first if none selected
        if (!selectedIncidentIdRef.current && res.items.length > 0) {
          setSelectedIncidentId(res.items[0].id);
        }
      }
    } catch (err: unknown) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to query incidents');
      }
    } finally {
      if (isMountedRef.current) {
        setIsLoading(false);
      }
    }
  }, [canReadIncidents, filters]);

  // Fetch single incident details & timeline
  const fetchDetail = useCallback(async (targetId?: string) => {
    const id = targetId || selectedIncidentIdRef.current;
    if (!id || !canReadIncidents) {
      setSelectedIncident(null);
      setTimeline([]);
      return;
    }

    setIsDetailLoading(true);
    setIsTimelineLoading(true);
    try {
      const [inc, events] = await Promise.all([
        apiGetIncident(id),
        apiGetTimeline(id),
      ]);
      if (isMountedRef.current) {
        setSelectedIncident(inc);
        setTimeline(events);
      }
    } catch (err: unknown) {
      if (isMountedRef.current) {
        setError(err instanceof Error ? err.message : 'Failed to fetch incident details');
      }
    } finally {
      if (isMountedRef.current) {
        setIsDetailLoading(false);
        setIsTimelineLoading(false);
      }
    }
  }, [canReadIncidents]);

  useEffect(() => {
    isMountedRef.current = true;
    fetchIncidents();
    return () => {
      isMountedRef.current = false;
      if (rafIdRef.current !== null) {
        if (typeof cancelAnimationFrame === 'function') {
          cancelAnimationFrame(rafIdRef.current);
        } else {
          clearTimeout(rafIdRef.current);
        }
      }
    };
  }, [fetchIncidents]);

  useEffect(() => {
    if (selectedIncidentId) {
      fetchDetail(selectedIncidentId);
    } else {
      setSelectedIncident(null);
      setTimeline([]);
    }
  }, [selectedIncidentId, fetchDetail]);

  const setFilters = useCallback((newFilters: Partial<IncidentFilterParams>) => {
    setFiltersState((prev) => ({ ...prev, ...newFilters }));
  }, []);

  const selectIncident = useCallback((id: string | null) => {
    setSelectedIncidentId(id);
  }, []);

  // Flush pending realtime events to React state
  const flushRealtimeUpdates = useCallback(() => {
    if (!isMountedRef.current) {
      rafIdRef.current = null;
      return;
    }
    rafIdRef.current = null;

    const createdList = [...pendingCreatedRef.current];
    pendingCreatedRef.current = [];

    const updatesMap = new Map(pendingUpdatesRef.current);
    pendingUpdatesRef.current.clear();

    const newTimelineEvents = [...pendingTimelineRef.current];
    pendingTimelineRef.current = [];

    // 1. Process Created Incidents
    if (createdList.length > 0) {
      setIncidents((prev) => {
        const existingIds = new Set(prev.map((i) => i.id));
        const newItems: Incident[] = [];

        for (const p of createdList) {
          if (!existingIds.has(p.incident_id)) {
            newItems.push({
              id: p.incident_id,
              incident_number: p.incident_number,
              title: p.title,
              status: p.status as IncidentStatus,
              severity: p.severity as IncidentSeverity,
              source: p.source as any,
              primary_track_id: p.primary_track_id,
              primary_group_id: p.primary_group_id,
              originating_alert_id: p.originating_alert_id,
              originating_intelligence_event_id: p.originating_intelligence_event_id,
              assigned_to: p.assigned_to,
              created_by: p.actor_user_id,
              created_at: p.timestamp,
              updated_at: p.timestamp,
            });
            existingIds.add(p.incident_id);
          }
        }
        if (newItems.length === 0) return prev;
        return [...newItems, ...prev];
      });
      setTotal((prev) => prev + createdList.length);
    }

    // 2. Process Status/Field Updates in incidents list
    if (updatesMap.size > 0) {
      setIncidents((prev) =>
        prev.map((inc) => {
          const update = updatesMap.get(inc.id);
          if (!update) return inc;
          return {
            ...inc,
            status: (update.status as IncidentStatus) || inc.status,
            severity: (update.severity as IncidentSeverity) || inc.severity,
            assigned_to: update.assigned_to !== undefined ? update.assigned_to : inc.assigned_to,
            updated_at: update.timestamp || inc.updated_at,
          };
        })
      );

      // Update selected incident if it's currently focused
      const curSelectedId = selectedIncidentIdRef.current;
      if (curSelectedId && updatesMap.has(curSelectedId)) {
        const update = updatesMap.get(curSelectedId)!;
        setSelectedIncident((prev) => {
          if (!prev || prev.id !== curSelectedId) return prev;
          return {
            ...prev,
            status: (update.status as IncidentStatus) || prev.status,
            severity: (update.severity as IncidentSeverity) || prev.severity,
            assigned_to: update.assigned_to !== undefined ? update.assigned_to : prev.assigned_to,
            updated_at: update.timestamp || prev.updated_at,
          };
        });
      }
    }

    // 3. Process Timeline Appends for selected incident
    if (newTimelineEvents.length > 0) {
      const curSelectedId = selectedIncidentIdRef.current;
      const relevantEvents = newTimelineEvents.filter((e) => e.incident_id === curSelectedId);
      if (relevantEvents.length > 0) {
        setTimeline((prev) => {
          const existingEventIds = new Set(prev.map((e) => e.id));
          const toAdd = relevantEvents.filter((e) => !existingEventIds.has(e.id));
          if (toAdd.length === 0) return prev;
          const merged = [...prev, ...toAdd];
          merged.sort((a, b) => a.sequence - b.sequence);
          return merged;
        });
      }
    }
  }, []);

  const scheduleFlush = useCallback(() => {
    if (rafIdRef.current !== null) return;
    if (typeof requestAnimationFrame === 'function') {
      rafIdRef.current = requestAnimationFrame(flushRealtimeUpdates);
    } else {
      rafIdRef.current = setTimeout(flushRealtimeUpdates, 16) as unknown as number;
    }
  }, [flushRealtimeUpdates]);

  // Handle incoming WebSocket operational telemetry
  const handleWebSocketMessage = useCallback(
    (envelope: RealtimeEventEnvelope) => {
      if (!envelope || !envelope.event_type || !envelope.event_type.startsWith('incident.')) {
        return;
      }

      // Monotonic sequence verification
      if (envelope.sequence && envelope.sequence <= lastEventSequenceRef.current) {
        return; // Stale or duplicate sequence
      }
      if (envelope.sequence) {
        lastEventSequenceRef.current = envelope.sequence;
      }

      const payload = envelope.payload as unknown as IncidentRealtimePayload;
      if (!payload || !payload.incident_id) return;

      const evtType = envelope.event_type;

      if (evtType === 'incident.created') {
        pendingCreatedRef.current.push(payload);
      } else {
        pendingUpdatesRef.current.set(payload.incident_id, payload);
      }

      // Build corresponding timeline event
      if (payload.incident_event_id && payload.incident_event_sequence) {
        const timelineEvt: IncidentEvent = {
          id: payload.incident_event_id,
          incident_id: payload.incident_id,
          sequence: payload.incident_event_sequence,
          timestamp: payload.timestamp,
          event_type: (payload.incident_event_type as IncidentEventType) || 'STATUS_CHANGED',
          actor_user_id: payload.actor_user_id,
          previous_status: payload.previous_status as IncidentStatus | null,
          new_status: payload.status as IncidentStatus | null,
          message: payload.message,
          category: payload.category as any,
          metadata: {},
          created_at: payload.timestamp,
        };
        pendingTimelineRef.current.push(timelineEvt);
      }

      scheduleFlush();
    },
    [scheduleFlush]
  );

  useWebSocketStream({
    channel: 'operational',
    enabled: enableStreaming && !!user && canReadIncidents,
    onMessage: handleWebSocketMessage,
  });

  // Action mutation handlers
  const createIncident = useCallback(async (data: CreateIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const created = await apiCreate(data);
      setIncidents((prev) => [created, ...prev.filter((i) => i.id !== created.id)]);
      setSelectedIncidentId(created.id);
      setSelectedIncident(created);
      return created;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to create incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, []);

  const acknowledgeIncident = useCallback(async (id: string, data?: AcknowledgeIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await apiAcknowledge(id, data);
      setIncidents((prev) => prev.map((i) => (i.id === id ? updated : i)));
      if (selectedIncidentIdRef.current === id) {
        setSelectedIncident(updated);
        await fetchDetail(id);
      }
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to acknowledge incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [fetchDetail]);

  const assignIncident = useCallback(async (id: string, data: AssignIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await apiAssign(id, data);
      setIncidents((prev) => prev.map((i) => (i.id === id ? updated : i)));
      if (selectedIncidentIdRef.current === id) {
        setSelectedIncident(updated);
        await fetchDetail(id);
      }
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to assign incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [fetchDetail]);

  const triageIncident = useCallback(async (id: string, data: TriageIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await apiTriage(id, data);
      setIncidents((prev) => prev.map((i) => (i.id === id ? updated : i)));
      if (selectedIncidentIdRef.current === id) {
        setSelectedIncident(updated);
        await fetchDetail(id);
      }
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to triage incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [fetchDetail]);

  const escalateIncident = useCallback(async (id: string, data: EscalateIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await apiEscalate(id, data);
      setIncidents((prev) => prev.map((i) => (i.id === id ? updated : i)));
      if (selectedIncidentIdRef.current === id) {
        setSelectedIncident(updated);
        await fetchDetail(id);
      }
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to escalate incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [fetchDetail]);

  const deEscalateIncident = useCallback(async (id: string, data: DeEscalateIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await apiDeEscalate(id, data);
      setIncidents((prev) => prev.map((i) => (i.id === id ? updated : i)));
      if (selectedIncidentIdRef.current === id) {
        setSelectedIncident(updated);
        await fetchDetail(id);
      }
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to de-escalate incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [fetchDetail]);

  const resolveIncident = useCallback(async (id: string, data: ResolveIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await apiResolve(id, data);
      setIncidents((prev) => prev.map((i) => (i.id === id ? updated : i)));
      if (selectedIncidentIdRef.current === id) {
        setSelectedIncident(updated);
        await fetchDetail(id);
      }
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to resolve incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [fetchDetail]);

  const closeIncident = useCallback(async (id: string, data?: CloseIncidentRequest): Promise<Incident> => {
    setIsMutating(true);
    setError(null);
    try {
      const updated = await apiClose(id, data);
      setIncidents((prev) => prev.map((i) => (i.id === id ? updated : i)));
      if (selectedIncidentIdRef.current === id) {
        setSelectedIncident(updated);
        await fetchDetail(id);
      }
      return updated;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to close incident';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, [fetchDetail]);

  const addNote = useCallback(async (id: string, data: AddIncidentNoteRequest): Promise<IncidentEvent> => {
    setIsMutating(true);
    setError(null);
    try {
      const event = await apiAddNote(id, data);
      if (selectedIncidentIdRef.current === id) {
        setTimeline((prev) => [...prev, event]);
      }
      return event;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to add note';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, []);

  const logDefensiveAction = useCallback(async (id: string, data: LogDefensiveActionRequest): Promise<IncidentEvent> => {
    setIsMutating(true);
    setError(null);
    try {
      const event = await apiLogAction(id, data);
      if (selectedIncidentIdRef.current === id) {
        setTimeline((prev) => [...prev, event]);
      }
      return event;
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to log defensive action';
      setError(msg);
      throw err;
    } finally {
      setIsMutating(false);
    }
  }, []);

  return {
    incidents,
    total,
    selectedIncidentId,
    selectedIncident,
    timeline,
    isLoading,
    isDetailLoading,
    isTimelineLoading,
    isMutating,
    error,
    filters,
    setFilters,
    selectIncident,
    refreshList: fetchIncidents,
    refreshDetail: fetchDetail,
    createIncident,
    acknowledgeIncident,
    assignIncident,
    triageIncident,
    escalateIncident,
    deEscalateIncident,
    resolveIncident,
    closeIncident,
    addNote,
    logDefensiveAction,
  };
}
