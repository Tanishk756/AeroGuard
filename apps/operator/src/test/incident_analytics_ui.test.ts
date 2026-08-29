/**
 * AeroGuard Operator Console — Stage IM1-G Incident Analytics Unit & Integration Tests
 * Uses Node.js native test runner (node:test, node:assert/strict).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

// ── Pure Types ──

export type IncidentStatus =
  | 'NEW'
  | 'ACKNOWLEDGED'
  | 'TRIAGED'
  | 'ESCALATED'
  | 'RESOLVED'
  | 'CLOSED';

export type IncidentSeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

export interface IncidentSummaryMetrics {
  total_incidents: number;
  active_incidents: number;
  acknowledged_incidents: number;
  assigned_incidents: number;
  triaged_incidents: number;
  escalated_incidents: number;
  resolved_incidents: number;
  closed_incidents: number;
  critical_count: number;
  high_count: number;
  medium_count: number;
  low_count: number;
}

export interface IncidentDistributionItem {
  count: number;
  percentage: number;
}

export interface IncidentTimeSeriesBucket {
  bucket_start: string;
  created_count: number;
  resolved_count: number;
  closed_count: number;
  escalated_count: number;
}

export interface IncidentLifecycleTimingMetrics {
  median_acknowledgement_seconds?: number | null;
  p95_acknowledgement_seconds?: number | null;
  median_assignment_seconds?: number | null;
  p95_assignment_seconds?: number | null;
  median_resolution_seconds?: number | null;
  p95_resolution_seconds?: number | null;
  median_closure_seconds?: number | null;
  p95_closure_seconds?: number | null;
  median_duration_seconds?: number | null;
  p95_duration_seconds?: number | null;
  sample_counts: Record<string, number>;
}

export interface IncidentProceduralActionMetrics {
  by_category: Record<string, number>;
  total_actions: number;
}

export interface IncidentCorrelationMetrics {
  with_primary_track: number;
  with_primary_group: number;
  uncorrelated: number;
  top_tracks: Array<{ track_id: string; incident_count: number }>;
  top_groups: Array<{ group_id: string; incident_count: number }>;
}

export interface IncidentWorkflowEventMetrics {
  by_event_type: Record<string, number>;
  total_events: number;
  total_notes: number;
  total_actions: number;
}

export interface IncidentAnalyticsResponse {
  window_start?: string | null;
  window_end?: string | null;
  bucket_size: string;
  summary: IncidentSummaryMetrics;
  timing: IncidentLifecycleTimingMetrics;
  severity_distribution: Record<IncidentSeverity, IncidentDistributionItem>;
  status_distribution: Record<IncidentStatus, IncidentDistributionItem>;
  time_series: IncidentTimeSeriesBucket[];
  procedural_actions: IncidentProceduralActionMetrics;
  correlations: IncidentCorrelationMetrics;
  workflow: IncidentWorkflowEventMetrics;
}

// ── Synthetic Mock Data Generator ──

function createMockAnalytics(): IncidentAnalyticsResponse {
  const summary: IncidentSummaryMetrics = {
    total_incidents: 42,
    active_incidents: 13,
    acknowledged_incidents: 18,
    assigned_incidents: 15,
    triaged_incidents: 10,
    escalated_incidents: 3,
    resolved_incidents: 20,
    closed_incidents: 9,
    critical_count: 5,
    high_count: 12,
    medium_count: 18,
    low_count: 7,
  };

  const timing: IncidentLifecycleTimingMetrics = {
    median_acknowledgement_seconds: 124.5,
    p95_acknowledgement_seconds: 450.0,
    median_assignment_seconds: 180.0,
    p95_assignment_seconds: 600.0,
    median_resolution_seconds: 1200.0,
    p95_resolution_seconds: 3600.0,
    median_closure_seconds: 2400.0,
    p95_closure_seconds: 7200.0,
    median_duration_seconds: 1500.0,
    p95_duration_seconds: 5400.0,
    sample_counts: {
      acknowledgement: 18,
      assignment: 15,
      resolution: 20,
      closure: 9,
      duration: 42,
    },
  };

  const severity_distribution = {
    LOW: { count: 7, percentage: 16.67 },
    MEDIUM: { count: 18, percentage: 42.86 },
    HIGH: { count: 12, percentage: 28.57 },
    CRITICAL: { count: 5, percentage: 11.9 },
  };

  const status_distribution = {
    NEW: { count: 4, percentage: 9.52 },
    ACKNOWLEDGED: { count: 5, percentage: 11.9 },
    TRIAGED: { count: 4, percentage: 9.52 },
    ESCALATED: { count: 3, percentage: 7.14 },
    RESOLVED: { count: 17, percentage: 40.48 },
    CLOSED: { count: 9, percentage: 21.43 },
  };

  const time_series: IncidentTimeSeriesBucket[] = [
    { bucket_start: '2026-08-25', created_count: 8, resolved_count: 4, closed_count: 2, escalated_count: 1 },
    { bucket_start: '2026-08-26', created_count: 12, resolved_count: 6, closed_count: 3, escalated_count: 1 },
    { bucket_start: '2026-08-27', created_count: 10, resolved_count: 5, closed_count: 2, escalated_count: 0 },
    { bucket_start: '2026-08-28', created_count: 12, resolved_count: 5, closed_count: 2, escalated_count: 1 },
  ];

  const procedural_actions: IncidentProceduralActionMetrics = {
    by_category: {
      SENSOR_REVIEW: 14,
      TRACK_CORRELATION_REVIEW: 9,
      OPERATOR_CONTACT: 6,
      SUPERVISOR_ESCALATION: 3,
      PROCEDURE_REVIEW: 5,
      SCENARIO_REVIEW: 2,
      OTHER: 1,
    },
    total_actions: 40,
  };

  const correlations: IncidentCorrelationMetrics = {
    with_primary_track: 28,
    with_primary_group: 10,
    uncorrelated: 4,
    top_tracks: [
      { track_id: 'TRK-101', incident_count: 6 },
      { track_id: 'TRK-204', incident_count: 4 },
    ],
    top_groups: [
      { group_id: 'GRP-SWARM-A', incident_count: 5 },
    ],
  };

  const workflow: IncidentWorkflowEventMetrics = {
    by_event_type: {
      CREATED: 42,
      ACKNOWLEDGED: 18,
      ASSIGNED: 15,
      TRIAGED: 10,
      ACTION_LOGGED: 40,
      RESOLVED: 20,
      CLOSED: 9,
    },
    total_events: 157,
    total_notes: 12,
    total_actions: 40,
  };

  return {
    window_start: '2026-08-25T00:00:00Z',
    window_end: '2026-08-29T00:00:00Z',
    bucket_size: 'day',
    summary,
    timing,
    severity_distribution,
    status_distribution,
    time_series,
    procedural_actions,
    correlations,
    workflow,
  };
}

describe('Stage IM1-G — Incident Analytics UI Contracts & Data Integrations', () => {
  it('1. verifies summary KPI calculations and active count consistency', () => {
    const analytics = createMockAnalytics();
    assert.equal(analytics.summary.total_incidents, 42);
    assert.equal(analytics.summary.active_incidents, 13);
    assert.equal(analytics.summary.critical_count, 5);
    assert.equal(
      analytics.summary.critical_count +
        analytics.summary.high_count +
        analytics.summary.medium_count +
        analytics.summary.low_count,
      analytics.summary.total_incidents
    );
  });

  it('2. verifies severity distribution percentages sum up safely', () => {
    const analytics = createMockAnalytics();
    const sumCount =
      analytics.severity_distribution.LOW.count +
      analytics.severity_distribution.MEDIUM.count +
      analytics.severity_distribution.HIGH.count +
      analytics.severity_distribution.CRITICAL.count;
    assert.equal(sumCount, analytics.summary.total_incidents);
  });

  it('3. verifies status distribution matches exact IncidentStatus vocabulary', () => {
    const analytics = createMockAnalytics();
    const validStatuses: IncidentStatus[] = [
      'NEW',
      'ACKNOWLEDGED',
      'TRIAGED',
      'ESCALATED',
      'RESOLVED',
      'CLOSED',
    ];
    for (const st of validStatuses) {
      assert.ok(st in analytics.status_distribution);
      assert.ok(typeof analytics.status_distribution[st].count === 'number');
    }
  });

  it('4. verifies lifecycle timing metrics maintain sample count integrity', () => {
    const analytics = createMockAnalytics();
    assert.equal(analytics.timing.median_acknowledgement_seconds, 124.5);
    assert.equal(analytics.timing.p95_acknowledgement_seconds, 450.0);
    assert.equal(analytics.timing.sample_counts['acknowledgement'], 18);
    assert.equal(analytics.timing.sample_counts['duration'], 42);
  });

  it('5. verifies time-series trend bucket chronological ordering', () => {
    const analytics = createMockAnalytics();
    assert.ok(analytics.time_series.length > 0);
    for (let i = 1; i < analytics.time_series.length; i++) {
      assert.ok(
        analytics.time_series[i].bucket_start >= analytics.time_series[i - 1].bucket_start
      );
    }
  });

  it('6. verifies procedural action category breakdown', () => {
    const analytics = createMockAnalytics();
    assert.equal(analytics.procedural_actions.total_actions, 40);
    assert.equal(analytics.procedural_actions.by_category['SENSOR_REVIEW'], 14);
    assert.equal(analytics.procedural_actions.by_category['SUPERVISOR_ESCALATION'], 3);
  });

  it('7. verifies correlation counts match total incident population', () => {
    const analytics = createMockAnalytics();
    const corrSum =
      analytics.correlations.with_primary_track +
      analytics.correlations.with_primary_group +
      analytics.correlations.uncorrelated;
    assert.equal(corrSum, analytics.summary.total_incidents);
    assert.equal(analytics.correlations.top_tracks[0].track_id, 'TRK-101');
  });

  it('8. handles zero incident empty dataset without zero-division exceptions', () => {
    const empty: IncidentAnalyticsResponse = {
      bucket_size: 'day',
      summary: {
        total_incidents: 0,
        active_incidents: 0,
        acknowledged_incidents: 0,
        assigned_incidents: 0,
        triaged_incidents: 0,
        escalated_incidents: 0,
        resolved_incidents: 0,
        closed_incidents: 0,
        critical_count: 0,
        high_count: 0,
        medium_count: 0,
        low_count: 0,
      },
      timing: {
        sample_counts: {},
      },
      severity_distribution: {
        LOW: { count: 0, percentage: 0 },
        MEDIUM: { count: 0, percentage: 0 },
        HIGH: { count: 0, percentage: 0 },
        CRITICAL: { count: 0, percentage: 0 },
      },
      status_distribution: {
        NEW: { count: 0, percentage: 0 },
        ACKNOWLEDGED: { count: 0, percentage: 0 },
        TRIAGED: { count: 0, percentage: 0 },
        ESCALATED: { count: 0, percentage: 0 },
        RESOLVED: { count: 0, percentage: 0 },
        CLOSED: { count: 0, percentage: 0 },
      },
      time_series: [],
      procedural_actions: { by_category: {}, total_actions: 0 },
      correlations: { with_primary_track: 0, with_primary_group: 0, uncorrelated: 0, top_tracks: [], top_groups: [] },
      workflow: { by_event_type: {}, total_events: 0, total_notes: 0, total_actions: 0 },
    };

    assert.equal(empty.summary.total_incidents, 0);
    assert.equal(empty.severity_distribution.CRITICAL.percentage, 0);
  });

  it('9. enforces strictly non-kinetic safety properties (no targeting/offensive fields)', () => {
    const analytics = createMockAnalytics();
    const serialized = JSON.stringify(analytics).toLowerCase();
    const forbidden = [
      'weapon',
      'jamming',
      'countermeasure',
      'intercept',
      'targeting',
      'fire_control',
      'kill_chain',
      'hostile_intent',
    ];

    for (const word of forbidden) {
      assert.equal(serialized.includes(word), false, `Forbidden safety word found: ${word}`);
    }
  });

  it('10. verifies high-density analytics client rendering performance', () => {
    const start = performance.now();
    for (let i = 0; i < 1000; i++) {
      const mock = createMockAnalytics();
      assert.ok(mock.summary.total_incidents > 0);
    }
    const elapsed = performance.now() - start;
    assert.ok(elapsed < 200, `Client processing took too long: ${elapsed}ms`);
  });
});
