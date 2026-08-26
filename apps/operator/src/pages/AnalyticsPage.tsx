import React, { useEffect, useRef } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { BarChart } from '../components/analytics/BarChart';
import { TimeWindowFilter } from '../components/analytics/TimeWindowFilter';
import { useAnalytics } from '../hooks/useAnalytics';

type AnalyticsView = 'dashboard' | 'tracks' | 'alerts' | 'threats' | 'detections';

const VALID_VIEWS: AnalyticsView[] = ['dashboard', 'tracks', 'alerts', 'threats', 'detections'];

function parseView(raw: string | null): AnalyticsView {
  if (raw && VALID_VIEWS.includes(raw as AnalyticsView)) return raw as AnalyticsView;
  return 'dashboard';
}

/** Parse YYYY-MM-DD, return ISO string or undefined. Rejects malformed values. */
function parseDateParam(raw: string | null): string | undefined {
  if (!raw) return undefined;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return undefined;
  const d = new Date(raw);
  if (isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

export const AnalyticsPage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const view = parseView(searchParams.get('view'));
  const fromParam = searchParams.get('from') ?? '';
  const toParam = searchParams.get('to') ?? '';

  const { summary, loading, error, fetchAll, setWindow } = useAnalytics();

  // Track whether we have done the initial fetch so we don't double-fetch.
  const initialised = useRef(false);

  useEffect(() => {
    const start = parseDateParam(fromParam) ?? (fromParam || undefined);
    const end = parseDateParam(toParam) ?? (toParam || undefined);
    fetchAll({ windowStart: start, windowEnd: end });
    initialised.current = true;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []); // intentionally runs once on mount; refresh is manual

  const handleWindowChange = (start: string, end: string) => {
    setWindow(start || undefined, end || undefined);
    fetchAll({ windowStart: start || undefined, windowEnd: end || undefined });
  };

  const handleRefresh = () => {
    const start = parseDateParam(fromParam) ?? (fromParam || undefined);
    const end = parseDateParam(toParam) ?? (toParam || undefined);
    fetchAll({ windowStart: start, windowEnd: end });
  };

  const setView = (v: AnalyticsView) => {
    const next = new URLSearchParams(searchParams);
    if (v === 'dashboard') next.delete('view');
    else next.set('view', v);
    setSearchParams(next);
  };

  const tabs: { key: AnalyticsView; label: string }[] = [
    { key: 'dashboard', label: 'Dashboard' },
    { key: 'detections', label: 'Detections' },
    { key: 'tracks', label: 'Tracks' },
    { key: 'alerts', label: 'Alerts' },
    { key: 'threats', label: 'Threats' },
  ];

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
            Advanced Analytics &amp; Reporting
          </h1>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Descriptive SQL aggregations across detections, tracks, alerts, and threat assessments.
          </p>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
          <TimeWindowFilter
            initialStart={fromParam}
            initialEnd={toParam}
            onChange={handleWindowChange}
          />
          <Button variant="secondary" size="sm" onClick={handleRefresh} isLoading={loading}>
            Refresh
          </Button>
        </div>
      </div>

      {/* Tab Navigation */}
      <div style={{ display: 'flex', gap: '2px', borderBottom: '1px solid var(--border-subtle)' }}>
        {tabs.map((tab) => (
          <button
            key={tab.key}
            onClick={() => setView(tab.key)}
            style={{
              padding: '6px 14px',
              fontSize: 'var(--text-xs)',
              textTransform: 'uppercase',
              letterSpacing: '0.06em',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              borderBottom: view === tab.key ? '2px solid var(--color-accent)' : '2px solid transparent',
              color: view === tab.key ? 'var(--color-accent)' : 'var(--text-muted)',
              fontWeight: view === tab.key ? 600 : 400,
              transition: 'all var(--transition-fast)',
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {error && <ErrorState message={error} onRetry={handleRefresh} />}

      {loading && !summary && <LoadingState message="Computing operational metric aggregations..." />}

      {!loading && !error && !summary && (
        <EmptyState title="No Analytics Available" description="Analytics query returned zero data." />
      )}

      {summary && (
        <>
          {/* ── DASHBOARD VIEW ── */}
          {view === 'dashboard' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              {/* KPI Cards */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-sm)' }}>
                <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                  <div className="uppercase-tracking text-muted">Total Detections</div>
                  <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--color-accent)', marginTop: '4px' }}>
                    {summary.detections.total_detections.toLocaleString()}
                  </div>
                </Card>
                <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                  <div className="uppercase-tracking text-muted">Total Tracks</div>
                  <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--text-primary)', marginTop: '4px' }}>
                    {summary.tracks.total_tracks.toLocaleString()}
                  </div>
                  <div className="font-mono text-xs text-muted" style={{ marginTop: '2px' }}>
                    Avg Conf: {Math.round(summary.tracks.average_confidence * 100)}%
                  </div>
                </Card>
                <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                  <div className="uppercase-tracking text-muted">Total Alerts</div>
                  <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--status-warning)', marginTop: '4px' }}>
                    {summary.alerts.total_alerts.toLocaleString()}
                  </div>
                  <div className="font-mono text-xs text-muted" style={{ marginTop: '2px' }}>
                    Avg Res: {summary.alerts.average_resolution_seconds.toFixed(1)}s
                  </div>
                </Card>
                <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                  <div className="uppercase-tracking text-muted">Threat Assessments</div>
                  <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--status-critical)', marginTop: '4px' }}>
                    {summary.threats.total_assessments.toLocaleString()}
                  </div>
                  <div className="font-mono text-xs text-muted" style={{ marginTop: '2px' }}>
                    Avg Score: {summary.threats.average_score.toFixed(1)} (Max: {summary.threats.max_score.toFixed(1)})
                  </div>
                </Card>
              </div>

              {/* Overview Charts */}
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 'var(--space-md)' }}>
                <Card title="Detections by Source Modality">
                  <BarChart
                    title="Detections by Source Modality"
                    data={Object.entries(summary.detections.detections_by_source_type).map(([label, value]) => ({ label, value }))}
                    color="var(--color-accent)"
                  />
                </Card>
                <Card title="Tracks by Lifecycle State">
                  <BarChart
                    title="Tracks by Lifecycle State"
                    data={Object.entries(summary.tracks.tracks_by_state).map(([label, value]) => ({ label, value }))}
                    color="var(--status-success)"
                  />
                </Card>
                <Card title="Alerts by Severity">
                  <BarChart
                    title="Alerts by Severity"
                    data={Object.entries(summary.alerts.alerts_by_severity).map(([label, value]) => ({ label, value }))}
                    color="var(--status-warning)"
                  />
                </Card>
                <Card title="Threat Assessments by Level">
                  <BarChart
                    title="Threat Assessments by Level"
                    data={Object.entries(summary.threats.threats_by_level).map(([label, value]) => ({ label, value }))}
                    color="var(--status-critical)"
                  />
                </Card>
              </div>
            </div>
          )}

          {/* ── DETECTIONS VIEW ── */}
          {view === 'detections' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <Card title="Detections by Sensor">
                <BarChart
                  title="Detections by Sensor"
                  data={Object.entries(summary.detections.detections_by_sensor).map(([label, value]) => ({ label, value }))}
                />
              </Card>
              <Card title="Detections by Source Modality">
                <BarChart
                  title="Detections by Source Modality"
                  data={Object.entries(summary.detections.detections_by_source_type).map(([label, value]) => ({ label, value }))}
                />
              </Card>
              <Card title="Detections by Classification">
                <BarChart
                  title="Detections by Classification"
                  data={Object.entries(summary.detections.detections_by_classification).map(([label, value]) => ({ label, value }))}
                />
              </Card>
            </div>
          )}

          {/* ── TRACKS VIEW ── */}
          {view === 'tracks' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <Card title="Tracks by State">
                <BarChart
                  title="Tracks by State"
                  data={Object.entries(summary.tracks.tracks_by_state).map(([label, value]) => ({ label, value }))}
                  color="var(--status-success)"
                />
              </Card>
              <Card title="Tracks by Classification">
                <BarChart
                  title="Tracks by Classification"
                  data={Object.entries(summary.tracks.tracks_by_classification).map(([label, value]) => ({ label, value }))}
                  color="var(--color-accent)"
                />
              </Card>
              <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                <div className="uppercase-tracking text-muted">Average Confidence</div>
                <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--color-accent)' }}>
                  {Math.round(summary.tracks.average_confidence * 100)}%
                </div>
              </Card>
              <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                <div className="uppercase-tracking text-muted">Average Track Duration</div>
                <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  {summary.tracks.average_duration_seconds.toFixed(1)}s
                </div>
              </Card>
            </div>
          )}

          {/* ── ALERTS VIEW ── */}
          {view === 'alerts' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <Card title="Alerts by Severity">
                <BarChart
                  title="Alerts by Severity"
                  data={Object.entries(summary.alerts.alerts_by_severity).map(([label, value]) => ({ label, value }))}
                  color="var(--status-warning)"
                />
              </Card>
              <Card title="Alerts by Status">
                <BarChart
                  title="Alerts by Status"
                  data={Object.entries(summary.alerts.alerts_by_status).map(([label, value]) => ({ label, value }))}
                  color="var(--color-accent)"
                />
              </Card>
              <Card title="Alerts by Type">
                <BarChart
                  title="Alerts by Type"
                  data={Object.entries(summary.alerts.alerts_by_type).map(([label, value]) => ({ label, value }))}
                  color="var(--status-info)"
                />
              </Card>
              <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                <div className="uppercase-tracking text-muted">Average Resolution Time</div>
                <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--text-primary)' }}>
                  {summary.alerts.average_resolution_seconds.toFixed(1)}s
                </div>
              </Card>
            </div>
          )}

          {/* ── THREATS VIEW ── */}
          {view === 'threats' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
              <Card title="Threats by Level">
                <BarChart
                  title="Threats by Level"
                  data={Object.entries(summary.threats.threats_by_level).map(([label, value]) => ({ label, value }))}
                  color="var(--status-critical)"
                />
              </Card>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-sm)' }}>
                <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                  <div className="uppercase-tracking text-muted">Average Score</div>
                  <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--status-warning)' }}>
                    {summary.threats.average_score.toFixed(2)}
                  </div>
                </Card>
                <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
                  <div className="uppercase-tracking text-muted">Maximum Score</div>
                  <div className="font-mono text-2xl" style={{ fontWeight: 700, color: 'var(--status-critical)' }}>
                    {summary.threats.max_score.toFixed(2)}
                  </div>
                </Card>
              </div>
            </div>
          )}
        </>
      )}
    </div>
  );
};
