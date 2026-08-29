/**
 * AeroGuard Incident Analytics Workspace Page
 * Stage IM1-G: Incident Analytics, Reporting & Operational Review
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BarChart, BarChartItem } from '../components/analytics/BarChart';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { IncidentExportHistory } from '../components/incidents/IncidentExportHistory';
import { IncidentExportModal } from '../components/incidents/IncidentExportModal';
import { useAuth } from '../context/AuthContext';
import { TimeWindowPreset, useIncidentAnalytics } from '../hooks/useIncidentAnalytics';
import { IncidentSeverity, IncidentStatus } from '../types';

function formatDuration(seconds: number | null | undefined): string {
  if (seconds === null || seconds === undefined) return 'N/A';
  if (seconds < 60) return `${Math.round(seconds)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(1)}m`;
  if (seconds < 86400) return `${(seconds / 3600).toFixed(1)}d`;
  return `${(seconds / 86400).toFixed(1)}d`;
}

export const IncidentAnalyticsPage: React.FC = () => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canExport = hasPermission('incidents.export');
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);
  const [historyRefreshTrigger, setHistoryRefreshTrigger] = useState(0);

  const {
    analytics,
    loading,
    error,
    isStale,
    preset,
    filters,
    refresh,
    setPreset,
    setFilters,
    resetFilters,
  } = useIncidentAnalytics('LAST_7D');

  const [customStart, setCustomStart] = useState<string>('');
  const [customEnd, setCustomEnd] = useState<string>('');

  const handleApplyCustomDates = () => {
    if (customStart && customEnd) {
      setPreset('CUSTOM');
      setFilters({
        start: new Date(customStart).toISOString(),
        end: new Date(customEnd).toISOString(),
      });
    }
  };

  const severityChartData: BarChartItem[] = analytics?.severity_distribution
    ? [
        { label: 'CRITICAL', value: analytics.severity_distribution.CRITICAL?.count || 0 },
        { label: 'HIGH', value: analytics.severity_distribution.HIGH?.count || 0 },
        { label: 'MEDIUM', value: analytics.severity_distribution.MEDIUM?.count || 0 },
        { label: 'LOW', value: analytics.severity_distribution.LOW?.count || 0 },
      ]
    : [];

  const statusChartData: BarChartItem[] = analytics?.status_distribution
    ? [
        { label: 'NEW', value: analytics.status_distribution.NEW?.count || 0 },
        { label: 'ACK', value: analytics.status_distribution.ACKNOWLEDGED?.count || 0 },
        { label: 'TRIAGED', value: analytics.status_distribution.TRIAGED?.count || 0 },
        { label: 'ESCALATED', value: analytics.status_distribution.ESCALATED?.count || 0 },
        { label: 'RESOLVED', value: analytics.status_distribution.RESOLVED?.count || 0 },
        { label: 'CLOSED', value: analytics.status_distribution.CLOSED?.count || 0 },
      ]
    : [];

  const proceduralChartData: BarChartItem[] = analytics?.procedural_actions?.by_category
    ? Object.entries(analytics.procedural_actions.by_category).map(([cat, cnt]) => ({
        label: cat.replace('_', ' '),
        value: cnt,
      }))
    : [];

  const trendChartData: BarChartItem[] = analytics?.time_series
    ? analytics.time_series.map((bucket) => ({
        label: bucket.bucket_start,
        value: bucket.created_count,
      }))
    : [];

  return (
    <div
      style={{
        padding: 'var(--space-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md)',
        flex: 1,
        overflowY: 'auto',
      }}
    >
      {/* Header & Workspace Switcher */}
      <div
        style={{
          display: 'flex',
          alignItems: 'flex-start',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-md)',
          borderBottom: '1px solid var(--border-color)',
          paddingBottom: 'var(--space-sm)',
        }}
      >
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <h1
              style={{
                fontSize: 'var(--text-lg)',
                textTransform: 'uppercase',
                letterSpacing: '0.06em',
                margin: 0,
              }}
            >
              Incident Analytics &amp; Operational Review
            </h1>
            {isStale && (
              <span
                style={{
                  fontSize: '11px',
                  padding: '2px 8px',
                  borderRadius: '4px',
                  background: 'rgba(245, 158, 11, 0.15)',
                  color: 'var(--color-warning)',
                  border: '1px solid var(--color-warning)',
                  fontWeight: 600,
                }}
              >
                ● Data Updated (Stale)
              </span>
            )}
          </div>
          <p className="text-muted text-xs" style={{ margin: '4px 0 0' }}>
            Descriptive historical statistics, lifecycle timing, procedural action tallies, and target correlations.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
          {canExport && (
            <Button
              variant="secondary"
              size="sm"
              onClick={() => setIsExportModalOpen(true)}
            >
              📥 Export Incidents
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={() => navigate('/app/incidents')}>
            📋 Active Incidents Workspace
          </Button>
          <Button variant="primary" size="sm" onClick={refresh} isLoading={loading}>
            🔄 Refresh
          </Button>
        </div>
      </div>

      {/* Time Window Presets & Controls */}
      <Card style={{ padding: 'var(--space-sm)' }}>
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            flexWrap: 'wrap',
            gap: 'var(--space-md)',
          }}
        >
          {/* Presets */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
            {(['LAST_24H', 'LAST_7D', 'LAST_30D', 'CUSTOM'] as TimeWindowPreset[]).map((p) => (
              <Button
                key={p}
                variant={preset === p ? 'primary' : 'ghost'}
                size="sm"
                onClick={() => setPreset(p)}
              >
                {p === 'LAST_24H' ? 'Last 24 Hours' : p === 'LAST_7D' ? 'Last 7 Days' : p === 'LAST_30D' ? 'Last 30 Days' : 'Custom'}
              </Button>
            ))}
          </div>

          {/* Custom Date Selector */}
          {preset === 'CUSTOM' && (
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', flexWrap: 'wrap' }}>
              <input
                type="datetime-local"
                value={customStart}
                onChange={(e) => setCustomStart(e.target.value)}
                style={{
                  background: 'var(--bg-canvas)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '12px',
                }}
              />
              <span className="text-muted text-xs">to</span>
              <input
                type="datetime-local"
                value={customEnd}
                onChange={(e) => setCustomEnd(e.target.value)}
                style={{
                  background: 'var(--bg-canvas)',
                  color: 'var(--text-primary)',
                  border: '1px solid var(--border-color)',
                  borderRadius: '4px',
                  padding: '4px 8px',
                  fontSize: '12px',
                }}
              />
              <Button variant="secondary" size="sm" onClick={handleApplyCustomDates}>
                Apply Range
              </Button>
            </div>
          )}

          {/* Severity & Status Filters */}
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <select
              value={filters.severity || ''}
              onChange={(e) =>
                setFilters({
                  severity: (e.target.value as IncidentSeverity) || undefined,
                })
              }
              aria-label="Filter by Severity"
              style={{
                background: 'var(--bg-canvas)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '12px',
              }}
            >
              <option value="">All Severities</option>
              <option value="CRITICAL">Critical</option>
              <option value="HIGH">High</option>
              <option value="MEDIUM">Medium</option>
              <option value="LOW">Low</option>
            </select>

            <select
              value={filters.status || ''}
              onChange={(e) =>
                setFilters({
                  status: (e.target.value as IncidentStatus) || undefined,
                })
              }
              aria-label="Filter by Status"
              style={{
                background: 'var(--bg-canvas)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border-color)',
                borderRadius: '4px',
                padding: '4px 8px',
                fontSize: '12px',
              }}
            >
              <option value="">All Statuses</option>
              <option value="NEW">NEW</option>
              <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
              <option value="TRIAGED">TRIAGED</option>
              <option value="ESCALATED">ESCALATED</option>
              <option value="RESOLVED">RESOLVED</option>
              <option value="CLOSED">CLOSED</option>
            </select>

            <Button variant="ghost" size="sm" onClick={resetFilters}>
              Reset Filters
            </Button>
          </div>
        </div>
      </Card>

      {/* Main Content States */}
      {loading ? (
        <LoadingState message="Computing incident analytics and SQL aggregations..." />
      ) : error ? (
        <ErrorState message={error} onRetry={refresh} />
      ) : !analytics || analytics.summary.total_incidents === 0 ? (
        <EmptyState
          title="No Incident Records Found"
          description="There are no operational incidents matching the selected time range and filters."
        />
      ) : (
        <>
          {/* Summary KPI Banner */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
              gap: 'var(--space-sm)',
            }}
          >
            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Total Incidents</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px' }}>
                {analytics.summary.total_incidents}
              </div>
            </Card>

            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Active</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', color: '#f59e0b' }}>
                {analytics.summary.active_incidents}
              </div>
            </Card>

            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Acknowledged</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px' }}>
                {analytics.summary.acknowledged_incidents}
              </div>
            </Card>

            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Assigned</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px' }}>
                {analytics.summary.assigned_incidents}
              </div>
            </Card>

            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Triaged</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px' }}>
                {analytics.summary.triaged_incidents}
              </div>
            </Card>

            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Escalated</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', color: '#ef4444' }}>
                {analytics.summary.escalated_incidents}
              </div>
            </Card>

            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Resolved</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', color: '#10b981' }}>
                {analytics.summary.resolved_incidents}
              </div>
            </Card>

            <Card style={{ padding: 'var(--space-sm)' }}>
              <div className="text-muted text-xs uppercase">Closed</div>
              <div style={{ fontSize: '20px', fontWeight: 700, marginTop: '2px', color: '#64748b' }}>
                {analytics.summary.closed_incidents}
              </div>
            </Card>
          </div>

          {/* Lifecycle Timing Grid */}
          <Card style={{ padding: 'var(--space-md)' }}>
            <h2 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 12px' }}>
              ⏱ Operational Lifecycle Workflow Durations
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                gap: 'var(--space-md)',
              }}
            >
              <div>
                <div className="text-muted text-xs uppercase">Acknowledgement Time</div>
                <div style={{ fontSize: '16px', fontWeight: 600, margin: '4px 0 2px' }}>
                  Median: {formatDuration(analytics.timing.median_acknowledgement_seconds)}
                </div>
                <div className="text-muted text-xs">
                  P95: {formatDuration(analytics.timing.p95_acknowledgement_seconds)} ({analytics.timing.sample_counts?.acknowledgement || 0} samples)
                </div>
              </div>

              <div>
                <div className="text-muted text-xs uppercase">Assignment Time</div>
                <div style={{ fontSize: '16px', fontWeight: 600, margin: '4px 0 2px' }}>
                  Median: {formatDuration(analytics.timing.median_assignment_seconds)}
                </div>
                <div className="text-muted text-xs">
                  P95: {formatDuration(analytics.timing.p95_assignment_seconds)} ({analytics.timing.sample_counts?.assignment || 0} samples)
                </div>
              </div>

              <div>
                <div className="text-muted text-xs uppercase">Resolution Time</div>
                <div style={{ fontSize: '16px', fontWeight: 600, margin: '4px 0 2px' }}>
                  Median: {formatDuration(analytics.timing.median_resolution_seconds)}
                </div>
                <div className="text-muted text-xs">
                  P95: {formatDuration(analytics.timing.p95_resolution_seconds)} ({analytics.timing.sample_counts?.resolution || 0} samples)
                </div>
              </div>

              <div>
                <div className="text-muted text-xs uppercase">Closure Time</div>
                <div style={{ fontSize: '16px', fontWeight: 600, margin: '4px 0 2px' }}>
                  Median: {formatDuration(analytics.timing.median_closure_seconds)}
                </div>
                <div className="text-muted text-xs">
                  P95: {formatDuration(analytics.timing.p95_closure_seconds)} ({analytics.timing.sample_counts?.closure || 0} samples)
                </div>
              </div>

              <div>
                <div className="text-muted text-xs uppercase">Total Incident Duration</div>
                <div style={{ fontSize: '16px', fontWeight: 600, margin: '4px 0 2px' }}>
                  Median: {formatDuration(analytics.timing.median_duration_seconds)}
                </div>
                <div className="text-muted text-xs">
                  P95: {formatDuration(analytics.timing.p95_duration_seconds)} ({analytics.timing.sample_counts?.duration || 0} samples)
                </div>
              </div>
            </div>
          </Card>

          {/* Visual Bar Charts Grid */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: 'var(--space-md)',
            }}
          >
            {/* Severity Distribution */}
            <Card style={{ padding: 'var(--space-md)' }}>
              <h2 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 12px' }}>
                Operational Severity Distribution
              </h2>
              <BarChart title="Severity Distribution" data={severityChartData} color="#38bdf8" />
              <table style={{ width: '100%', marginTop: '12px', fontSize: '12px', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '4px 0' }}>Severity</th>
                    <th style={{ padding: '4px 0' }}>Count</th>
                    <th style={{ padding: '4px 0' }}>Percentage</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(analytics.severity_distribution).map(([sev, item]) => (
                    <tr key={sev} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '4px 0', fontWeight: 600 }}>{sev}</td>
                      <td style={{ padding: '4px 0' }}>{item.count}</td>
                      <td style={{ padding: '4px 0' }}>{item.percentage}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>

            {/* Lifecycle Status Distribution */}
            <Card style={{ padding: 'var(--space-md)' }}>
              <h2 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 12px' }}>
                Lifecycle Status Distribution
              </h2>
              <BarChart title="Status Distribution" data={statusChartData} color="#f59e0b" />
              <table style={{ width: '100%', marginTop: '12px', fontSize: '12px', borderCollapse: 'collapse' }}>
                <thead>
                  <tr style={{ borderBottom: '1px solid var(--border-color)', textAlign: 'left' }}>
                    <th style={{ padding: '4px 0' }}>Status</th>
                    <th style={{ padding: '4px 0' }}>Count</th>
                    <th style={{ padding: '4px 0' }}>Percentage</th>
                  </tr>
                </thead>
                <tbody>
                  {Object.entries(analytics.status_distribution).map(([st, item]) => (
                    <tr key={st} style={{ borderBottom: '1px solid rgba(255,255,255,0.05)' }}>
                      <td style={{ padding: '4px 0', fontWeight: 600 }}>{st}</td>
                      <td style={{ padding: '4px 0' }}>{item.count}</td>
                      <td style={{ padding: '4px 0' }}>{item.percentage}%</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </Card>
          </div>

          {/* Incident Chronological Trend & Procedural Actions */}
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))',
              gap: 'var(--space-md)',
            }}
          >
            {/* Time-Series Chronological Trend */}
            <Card style={{ padding: 'var(--space-md)' }}>
              <h2 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 12px' }}>
                Incident Creation Trend ({analytics.bucket_size})
              </h2>
              <BarChart title="Incident Creation Trend" data={trendChartData} color="#10b981" />
            </Card>

            {/* Procedural Actions Breakdown */}
            <Card style={{ padding: 'var(--space-md)' }}>
              <h2 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 12px' }}>
                Logged Procedural Actions ({analytics.procedural_actions.total_actions} total)
              </h2>
              <BarChart title="Procedural Actions" data={proceduralChartData} color="#8b5cf6" />
            </Card>
          </div>

          {/* Correlation Analytics & Top Entities */}
          <Card style={{ padding: 'var(--space-md)' }}>
            <h2 style={{ fontSize: '13px', textTransform: 'uppercase', letterSpacing: '0.05em', margin: '0 0 12px' }}>
              Authoritative Entity Correlation Summary
            </h2>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
                gap: 'var(--space-md)',
              }}
            >
              <div>
                <div className="text-muted text-xs uppercase">Correlation Counts</div>
                <ul style={{ margin: '8px 0 0', paddingLeft: '16px', fontSize: '13px' }}>
                  <li>With Primary Track: <strong>{analytics.correlations.with_primary_track}</strong></li>
                  <li>With Primary Group: <strong>{analytics.correlations.with_primary_group}</strong></li>
                  <li>Uncorrelated / System: <strong>{analytics.correlations.uncorrelated}</strong></li>
                </ul>
              </div>

              <div>
                <div className="text-muted text-xs uppercase">Top Correlated Tracks</div>
                {analytics.correlations.top_tracks.length === 0 ? (
                  <div className="text-muted text-xs" style={{ marginTop: '4px' }}>None</div>
                ) : (
                  <ul style={{ margin: '8px 0 0', paddingLeft: '16px', fontSize: '12px' }}>
                    {analytics.correlations.top_tracks.map((t) => (
                      <li key={t.track_id}>
                        <code>{t.track_id}</code> — <strong>{t.incident_count}</strong> incidents
                      </li>
                    ))}
                  </ul>
                )}
              </div>

              <div>
                <div className="text-muted text-xs uppercase">Top Correlated Swarm Groups</div>
                {analytics.correlations.top_groups.length === 0 ? (
                  <div className="text-muted text-xs" style={{ marginTop: '4px' }}>None</div>
                ) : (
                  <ul style={{ margin: '8px 0 0', paddingLeft: '16px', fontSize: '12px' }}>
                    {analytics.correlations.top_groups.map((g) => (
                      <li key={g.group_id}>
                        <code>{g.group_id}</code> — <strong>{g.incident_count}</strong> incidents
                      </li>
                    ))}
                  </ul>
                )}
              </div>
            </div>
          </Card>

          {/* Incident Export Archival History */}
          {canExport && (
            <IncidentExportHistory onRefreshTrigger={historyRefreshTrigger} />
          )}
        </>
      )}

      {/* Incident Export Modal */}
      <IncidentExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
        onExportSuccess={() => setHistoryRefreshTrigger((prev) => prev + 1)}
      />
    </div>
  );
};
