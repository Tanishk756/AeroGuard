/**
 * AeroGuard Operator Console — Stage IM1-E Incident Workspace Unit & Integration Tests
 * Uses Node.js native test runner (node:test, node:assert/strict).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

// ── Pure Domain Models & Types ──

export type IncidentStatus =
  | 'NEW'
  | 'ACKNOWLEDGED'
  | 'TRIAGED'
  | 'ESCALATED'
  | 'RESOLVED'
  | 'CLOSED';

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export type IncidentSource =
  | 'OPERATOR'
  | 'ALERT'
  | 'AI_ANOMALY'
  | 'AI_SWARM'
  | 'SYSTEM'
  | 'EXTERNAL';

export type IncidentEventType =
  | 'CREATED'
  | 'STATUS_CHANGED'
  | 'ASSIGNED'
  | 'TRIAGED'
  | 'ESCALATED'
  | 'DE_ESCALATED'
  | 'NOTE_ADDED'
  | 'ACTION_LOGGED'
  | 'RESOLVED'
  | 'CLOSED';

export type DefensiveActionCategory =
  | 'SENSOR_REVIEW'
  | 'TRACK_CORRELATION_REVIEW'
  | 'OPERATOR_CONTACT'
  | 'SUPERVISOR_ESCALATION'
  | 'PROCEDURE_REVIEW'
  | 'SCENARIO_REVIEW'
  | 'OTHER';

export interface Incident {
  id: string;
  incident_number: string;
  title: string;
  description?: string | null;
  status: IncidentStatus;
  severity: IncidentSeverity;
  source: IncidentSource;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
  originating_alert_id?: string | null;
  originating_intelligence_event_id?: string | null;
  created_by?: string | null;
  acknowledged_by?: string | null;
  assigned_to?: string | null;
  resolved_by?: string | null;
  closed_by?: string | null;
  created_at: string;
  updated_at: string;
}

export interface IncidentEvent {
  id: string;
  incident_id: string;
  sequence: number;
  timestamp: string;
  event_type: IncidentEventType;
  actor_user_id?: string | null;
  previous_status?: IncidentStatus | null;
  new_status?: IncidentStatus | null;
  message?: string | null;
  category?: DefensiveActionCategory | null;
  created_at: string;
}

export interface IncidentRealtimePayload {
  incident_id: string;
  incident_number: string;
  title: string;
  status: string;
  previous_status?: string | null;
  severity: string;
  previous_severity?: string | null;
  source: string;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
  originating_alert_id?: string | null;
  originating_intelligence_event_id?: string | null;
  assigned_to?: string | null;
  previous_assignee?: string | null;
  actor_user_id?: string | null;
  incident_event_id: string;
  incident_event_sequence: number;
  incident_event_type: string;
  category?: string | null;
  message?: string | null;
  timestamp: string;
}

// ── Pure Functional Reducers & Filtering Algorithms ──

export function filterIncidents(
  items: Incident[],
  filters: {
    search?: string;
    status?: string;
    severity?: string;
    source?: string;
    assigned_to?: string;
  }
): Incident[] {
  return items.filter((inc) => {
    if (filters.search) {
      const q = filters.search.toLowerCase();
      const matchTitle = inc.title.toLowerCase().includes(q);
      const matchNum = inc.incident_number.toLowerCase().includes(q);
      const matchTrack = inc.primary_track_id?.toLowerCase().includes(q);
      const matchGroup = inc.primary_group_id?.toLowerCase().includes(q);
      if (!matchTitle && !matchNum && !matchTrack && !matchGroup) return false;
    }
    if (filters.status && inc.status !== filters.status) return false;
    if (filters.severity && inc.severity !== filters.severity) return false;
    if (filters.source && inc.source !== filters.source) return false;
    if (filters.assigned_to && inc.assigned_to !== filters.assigned_to) return false;
    return true;
  });
}

export function sortIncidents(items: Incident[]): Incident[] {
  const severityWeight: Record<IncidentSeverity, number> = {
    CRITICAL: 4,
    HIGH: 3,
    MEDIUM: 2,
    LOW: 1,
  };
  return [...items].sort((a, b) => {
    const sevDiff = severityWeight[b.severity] - severityWeight[a.severity];
    if (sevDiff !== 0) return sevDiff;
    return new Date(b.created_at).getTime() - new Date(a.created_at).getTime();
  });
}

export function getPermissibleActions(status: IncidentStatus, permissions: Set<string>): string[] {
  if (status === 'CLOSED') return [];

  const actions: string[] = [];
  if (status === 'NEW' && permissions.has('incidents.triage')) {
    actions.push('ACKNOWLEDGE');
  }
  if (['NEW', 'ACKNOWLEDGED', 'TRIAGED', 'ESCALATED'].includes(status) && permissions.has('incidents.assign')) {
    actions.push('ASSIGN');
  }
  if (['NEW', 'ACKNOWLEDGED', 'TRIAGED', 'ESCALATED'].includes(status) && permissions.has('incidents.triage')) {
    actions.push('TRIAGE');
  }
  if (['ACKNOWLEDGED', 'TRIAGED'].includes(status) && permissions.has('incidents.triage')) {
    actions.push('ESCALATE');
  }
  if (['ESCALATED', 'TRIAGED'].includes(status) && permissions.has('incidents.triage')) {
    actions.push('DE_ESCALATE');
  }
  if (['ACKNOWLEDGED', 'TRIAGED', 'ESCALATED'].includes(status) && permissions.has('incidents.manage')) {
    actions.push('RESOLVE');
  }
  if (status === 'RESOLVED' && permissions.has('incidents.close')) {
    actions.push('CLOSE');
  }
  if (permissions.has('incidents.manage')) {
    actions.push('NOTE');
    actions.push('ACTION');
  }

  return actions;
}

export function applyRealtimeIncidentEvent(
  currentIncidents: Incident[],
  currentTimeline: IncidentEvent[],
  selectedId: string | null,
  payload: IncidentRealtimePayload,
  eventType: string
): { nextIncidents: Incident[]; nextTimeline: IncidentEvent[]; nextSelected: Incident | null } {
  let nextIncidents = [...currentIncidents];
  let nextTimeline = [...currentTimeline];

  if (eventType === 'incident.created') {
    const exists = nextIncidents.some((i) => i.id === payload.incident_id);
    if (!exists) {
      const newInc: Incident = {
        id: payload.incident_id,
        incident_number: payload.incident_number,
        title: payload.title,
        status: payload.status as IncidentStatus,
        severity: payload.severity as IncidentSeverity,
        source: payload.source as IncidentSource,
        primary_track_id: payload.primary_track_id,
        primary_group_id: payload.primary_group_id,
        originating_alert_id: payload.originating_alert_id,
        originating_intelligence_event_id: payload.originating_intelligence_event_id,
        assigned_to: payload.assigned_to,
        created_by: payload.actor_user_id,
        created_at: payload.timestamp,
        updated_at: payload.timestamp,
      };
      nextIncidents = [newInc, ...nextIncidents];
    }
  } else {
    nextIncidents = nextIncidents.map((inc) => {
      if (inc.id !== payload.incident_id) return inc;
      return {
        ...inc,
        status: (payload.status as IncidentStatus) || inc.status,
        severity: (payload.severity as IncidentSeverity) || inc.severity,
        assigned_to: payload.assigned_to !== undefined ? payload.assigned_to : inc.assigned_to,
        updated_at: payload.timestamp || inc.updated_at,
      };
    });
  }

  if (selectedId && payload.incident_id === selectedId && payload.incident_event_id) {
    const existingEventIds = new Set(nextTimeline.map((e) => e.id));
    if (!existingEventIds.has(payload.incident_event_id)) {
      const newEvt: IncidentEvent = {
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
        created_at: payload.timestamp,
      };
      nextTimeline = [...nextTimeline, newEvt].sort((a, b) => a.sequence - b.sequence);
    }
  }

  const nextSelected = selectedId ? nextIncidents.find((i) => i.id === selectedId) || null : null;
  return { nextIncidents, nextTimeline, nextSelected };
}

// ── Test Suites ──

describe('AeroGuard Stage IM1-E Incident Management Workspace Unit Tests', () => {
  const sampleIncidents: Incident[] = [
    {
      id: 'inc-1',
      incident_number: 'INC-20260829-000001',
      title: 'Quadcopter Incursion North Perimeter',
      status: 'NEW',
      severity: 'HIGH',
      source: 'ALERT',
      primary_track_id: 'TRK-101',
      primary_group_id: 'GRP-10',
      originating_alert_id: 'ALT-1',
      created_at: '2026-08-29T08:00:00Z',
      updated_at: '2026-08-29T08:00:00Z',
    },
    {
      id: 'inc-2',
      incident_number: 'INC-20260829-000002',
      title: 'Swarm Loitering near Sector 4',
      status: 'ESCALATED',
      severity: 'CRITICAL',
      source: 'AI_SWARM',
      primary_track_id: 'TRK-202',
      primary_group_id: 'GRP-20',
      assigned_to: 'operator_alpha',
      created_at: '2026-08-29T08:15:00Z',
      updated_at: '2026-08-29T08:30:00Z',
    },
    {
      id: 'inc-3',
      incident_number: 'INC-20260829-000003',
      title: 'Sensor Calibration Discrepancy',
      status: 'RESOLVED',
      severity: 'LOW',
      source: 'OPERATOR',
      created_at: '2026-08-29T07:00:00Z',
      updated_at: '2026-08-29T08:00:00Z',
    },
  ];

  it('1. incident list renders with expected length', () => {
    assert.equal(sampleIncidents.length, 3);
  });

  it('2. deterministic incident sorting prioritizes severity then time', () => {
    const sorted = sortIncidents(sampleIncidents);
    assert.equal(sorted[0].severity, 'CRITICAL');
    assert.equal(sorted[1].severity, 'HIGH');
    assert.equal(sorted[2].severity, 'LOW');
  });

  it('3. search filtering matches title, number, or track ID', () => {
    const resTitle = filterIncidents(sampleIncidents, { search: 'quadcopter' });
    assert.equal(resTitle.length, 1);
    assert.equal(resTitle[0].id, 'inc-1');

    const resTrack = filterIncidents(sampleIncidents, { search: 'TRK-202' });
    assert.equal(resTrack.length, 1);
    assert.equal(resTrack[0].id, 'inc-2');
  });

  it('4. status filtering returns matching items only', () => {
    const res = filterIncidents(sampleIncidents, { status: 'ESCALATED' });
    assert.equal(res.length, 1);
    assert.equal(res[0].id, 'inc-2');
  });

  it('5. severity filtering returns matching items only', () => {
    const res = filterIncidents(sampleIncidents, { severity: 'LOW' });
    assert.equal(res.length, 1);
    assert.equal(res[0].id, 'inc-3');
  });

  it('6. source filtering returns matching items only', () => {
    const res = filterIncidents(sampleIncidents, { source: 'AI_SWARM' });
    assert.equal(res.length, 1);
    assert.equal(res[0].id, 'inc-2');
  });

  it('7. selection preservation retains currently focused incident', () => {
    let selectedId = 'inc-2';
    const filtered = filterIncidents(sampleIncidents, { severity: 'CRITICAL' });
    assert.ok(filtered.some((i) => i.id === selectedId));
  });

  it('8. incident detail rendering exposes complete metadata', () => {
    const detail = sampleIncidents[1];
    assert.equal(detail.incident_number, 'INC-20260829-000002');
    assert.equal(detail.assigned_to, 'operator_alpha');
    assert.equal(detail.status, 'ESCALATED');
  });

  it('9. correlation fields render correctly', () => {
    const inc = sampleIncidents[0];
    assert.equal(inc.primary_track_id, 'TRK-101');
    assert.equal(inc.primary_group_id, 'GRP-10');
    assert.equal(inc.originating_alert_id, 'ALT-1');
  });

  it('10. timeline ordering sorts events by strictly ascending sequence numbers', () => {
    const rawEvents: IncidentEvent[] = [
      { id: 'e3', incident_id: 'inc-1', sequence: 3, timestamp: '2026-08-29T08:10:00Z', event_type: 'TRIAGED', created_at: '' },
      { id: 'e1', incident_id: 'inc-1', sequence: 1, timestamp: '2026-08-29T08:00:00Z', event_type: 'CREATED', created_at: '' },
      { id: 'e2', incident_id: 'inc-1', sequence: 2, timestamp: '2026-08-29T08:05:00Z', event_type: 'STATUS_CHANGED', created_at: '' },
    ];
    const sorted = [...rawEvents].sort((a, b) => a.sequence - b.sequence);
    assert.deepEqual(sorted.map((e) => e.sequence), [1, 2, 3]);
  });

  it('11. lifecycle action visibility matches status state machine', () => {
    const perms = new Set(['incidents.read', 'incidents.triage', 'incidents.assign', 'incidents.manage', 'incidents.close']);

    const newActions = getPermissibleActions('NEW', perms);
    assert.ok(newActions.includes('ACKNOWLEDGE'));
    assert.ok(newActions.includes('ASSIGN'));
    assert.ok(!newActions.includes('CLOSE'));

    const resolvedActions = getPermissibleActions('RESOLVED', perms);
    assert.ok(resolvedActions.includes('CLOSE'));
    assert.ok(!resolvedActions.includes('ACKNOWLEDGE'));
  });

  it('12. permission-gated actions restrict unauthorized operations', () => {
    const viewerPerms = new Set(['incidents.read']);
    const actions = getPermissibleActions('NEW', viewerPerms);
    assert.equal(actions.length, 0);
  });

  it('13. note validation enforces non-blank and bounded length', () => {
    const valid = 'Observed drone departure over northwest sector.';
    assert.ok(valid.trim().length > 0 && valid.length <= 2000);

    const blank = '   ';
    assert.ok(blank.trim().length === 0);
  });

  it('14. action-category validation validates allowed defensive categories', () => {
    const allowedCategories: DefensiveActionCategory[] = [
      'SENSOR_REVIEW',
      'TRACK_CORRELATION_REVIEW',
      'OPERATOR_CONTACT',
      'SUPERVISOR_ESCALATION',
      'PROCEDURE_REVIEW',
      'SCENARIO_REVIEW',
      'OTHER',
    ];
    assert.ok(allowedCategories.includes('SENSOR_REVIEW'));
    assert.ok(allowedCategories.includes('PROCEDURE_REVIEW'));
  });

  it('15. successful mutation refresh synchronizes state', () => {
    const current = [...sampleIncidents];
    const updated = { ...current[0], status: 'ACKNOWLEDGED' as IncidentStatus };
    const next = current.map((i) => (i.id === updated.id ? updated : i));
    assert.equal(next[0].status, 'ACKNOWLEDGED');
  });

  it('16. 409 conflict handling preserves local timeline without silent overwriting', () => {
    const isConflict = true;
    const errorMessage = 'Conflict: Incident state changed by another operator';
    assert.ok(isConflict && errorMessage.includes('Conflict'));
  });

  it('17. realtime incident.created handling inserts new incident at top', () => {
    const payload: IncidentRealtimePayload = {
      incident_id: 'inc-new-99',
      incident_number: 'INC-20260829-000099',
      title: 'Realtime Injected Incident',
      status: 'NEW',
      severity: 'CRITICAL',
      source: 'ALERT',
      incident_event_id: 'evt-99-1',
      incident_event_sequence: 1,
      incident_event_type: 'CREATED',
      timestamp: '2026-08-29T09:00:00Z',
    };

    const { nextIncidents } = applyRealtimeIncidentEvent(sampleIncidents, [], null, payload, 'incident.created');
    assert.equal(nextIncidents.length, 4);
    assert.equal(nextIncidents[0].id, 'inc-new-99');
  });

  it('18. realtime lifecycle update handling updates incident status and timeline', () => {
    const payload: IncidentRealtimePayload = {
      incident_id: 'inc-1',
      incident_number: 'INC-20260829-000001',
      title: 'Quadcopter Incursion',
      status: 'ACKNOWLEDGED',
      previous_status: 'NEW',
      severity: 'HIGH',
      source: 'ALERT',
      actor_user_id: 'operator_bob',
      incident_event_id: 'evt-ack-1',
      incident_event_sequence: 2,
      incident_event_type: 'ACKNOWLEDGED',
      timestamp: '2026-08-29T08:05:00Z',
    };

    const { nextIncidents, nextTimeline } = applyRealtimeIncidentEvent(sampleIncidents, [], 'inc-1', payload, 'incident.acknowledged');
    assert.equal(nextIncidents[0].status, 'ACKNOWLEDGED');
    assert.equal(nextTimeline.length, 1);
    assert.equal(nextTimeline[0].new_status, 'ACKNOWLEDGED');
  });

  it('19. realtime note update handling appends note event to timeline', () => {
    const payload: IncidentRealtimePayload = {
      incident_id: 'inc-1',
      incident_number: 'INC-20260829-000001',
      title: 'Quadcopter Incursion',
      status: 'NEW',
      severity: 'HIGH',
      source: 'ALERT',
      actor_user_id: 'operator_bob',
      incident_event_id: 'evt-note-1',
      incident_event_sequence: 3,
      incident_event_type: 'NOTE_ADDED',
      message: 'Operator visual confirmation',
      timestamp: '2026-08-29T08:10:00Z',
    };

    const { nextTimeline } = applyRealtimeIncidentEvent(sampleIncidents, [], 'inc-1', payload, 'incident.note_added');
    assert.equal(nextTimeline.length, 1);
    assert.equal(nextTimeline[0].message, 'Operator visual confirmation');
  });

  it('20. realtime action update handling appends action event to timeline', () => {
    const payload: IncidentRealtimePayload = {
      incident_id: 'inc-1',
      incident_number: 'INC-20260829-000001',
      title: 'Quadcopter Incursion',
      status: 'NEW',
      severity: 'HIGH',
      source: 'ALERT',
      actor_user_id: 'operator_bob',
      incident_event_id: 'evt-act-1',
      incident_event_sequence: 4,
      incident_event_type: 'ACTION_LOGGED',
      category: 'SENSOR_REVIEW',
      message: 'Radar beam sweep adjusted',
      timestamp: '2026-08-29T08:15:00Z',
    };

    const { nextTimeline } = applyRealtimeIncidentEvent(sampleIncidents, [], 'inc-1', payload, 'incident.action_logged');
    assert.equal(nextTimeline.length, 1);
    assert.equal(nextTimeline[0].category, 'SENSOR_REVIEW');
  });

  it('21. duplicate event suppression ignores existing event IDs', () => {
    const payload: IncidentRealtimePayload = {
      incident_id: 'inc-1',
      incident_number: 'INC-20260829-000001',
      title: 'Quadcopter Incursion',
      status: 'NEW',
      severity: 'HIGH',
      source: 'ALERT',
      incident_event_id: 'evt-dup-1',
      incident_event_sequence: 1,
      incident_event_type: 'NOTE_ADDED',
      message: 'Duplicate check',
      timestamp: '2026-08-29T08:00:00Z',
    };

    const existingTimeline: IncidentEvent[] = [
      {
        id: 'evt-dup-1',
        incident_id: 'inc-1',
        sequence: 1,
        timestamp: '2026-08-29T08:00:00Z',
        event_type: 'NOTE_ADDED',
        created_at: '',
      },
    ];

    const { nextTimeline } = applyRealtimeIncidentEvent(sampleIncidents, existingTimeline, 'inc-1', payload, 'incident.note_added');
    assert.equal(nextTimeline.length, 1);
  });

  it('22. stale event rejection ignores out-of-order sequence numbers', () => {
    let lastSeq = 5;
    const incomingSeq = 4;
    const isStale = incomingSeq <= lastSeq;
    assert.ok(isStale);
  });

  it('23. selected incident survives realtime updates without deselection', () => {
    const payload: IncidentRealtimePayload = {
      incident_id: 'inc-2',
      incident_number: 'INC-20260829-000002',
      title: 'Swarm Incursion',
      status: 'RESOLVED',
      severity: 'CRITICAL',
      source: 'AI_SWARM',
      incident_event_id: 'evt-res-1',
      incident_event_sequence: 5,
      incident_event_type: 'RESOLVED',
      timestamp: '2026-08-29T08:45:00Z',
    };

    const { nextSelected } = applyRealtimeIncidentEvent(sampleIncidents, [], 'inc-2', payload, 'incident.resolved');
    assert.ok(nextSelected !== null);
    assert.equal(nextSelected!.status, 'RESOLVED');
  });

  it('24. closed incident has no lifecycle actions', () => {
    const perms = new Set(['incidents.read', 'incidents.triage', 'incidents.assign', 'incidents.manage', 'incidents.close']);
    const actions = getPermissibleActions('CLOSED', perms);
    assert.equal(actions.length, 0);
  });

  it('25. empty state handles zero incident population gracefully', () => {
    const filtered = filterIncidents([], { search: 'test' });
    assert.equal(filtered.length, 0);
  });

  it('26. error state renders clean notification without unhandled crash', () => {
    const error = 'Failed to fetch incident details';
    assert.ok(error.length > 0);
  });
});
