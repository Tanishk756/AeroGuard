import React, { useCallback, useEffect, useState } from 'react';
import { getAnalyticsSummary } from '../api/analytics';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { AnalyticsSummaryResponse } from '../types';

export const AnalyticsPage: React.FC = () => {
  const [summary, setSummary] = useState<AnalyticsSummaryResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchAnalytics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const data = await getAnalyticsSummary();
      setSummary(data);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query analytics summary');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchAnalytics();
  }, [fetchAnalytics]);

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
            Descriptive Operational Analytics (F6 Backend)
          </h1>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Descriptive SQL aggregations across detections, tracks, alerts, and threat assessments.
          </p>
        </div>

        <Button variant="secondary" size="sm" onClick={fetchAnalytics} isLoading={isLoading}>
          Refresh Analytics
        </Button>
      </div>

      {error && <ErrorState message={error} onRetry={fetchAnalytics} />}

      {isLoading && !summary ? (
        <LoadingState message="Computing operational metric aggregations..." />
      ) : !summary ? (
        <EmptyState title="No Analytics Available" description="Analytics query returned zero data." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {/* Summary Metric Cards */}
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

          {/* Breakdown Distributions */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 'var(--space-md)' }}>
            {/* Detection Modalities */}
            <Card title="Detections by Source Modality">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
                {Object.entries(summary.detections.detections_by_source_type).length === 0 ? (
                  <p className="text-muted text-xs">No modality records.</p>
                ) : (
                  Object.entries(summary.detections.detections_by_source_type).map(([modality, count]) => {
                    const pct = summary.detections.total_detections > 0
                      ? Math.round((count / summary.detections.total_detections) * 100)
                      : 0;
                    return (
                      <div key={modality} style={{ marginBottom: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', marginBottom: '2px' }}>
                          <span className="font-mono uppercase-tracking">{modality}</span>
                          <span className="font-mono text-muted">{count} ({pct}%)</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--bg-canvas)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div style={{ width: `${pct}%`, height: '100%', backgroundColor: 'var(--color-accent)' }} />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </Card>

            {/* Tracks by State */}
            <Card title="Tracks by Lifecycle State">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
                {Object.entries(summary.tracks.tracks_by_state).length === 0 ? (
                  <p className="text-muted text-xs">No track lifecycle records.</p>
                ) : (
                  Object.entries(summary.tracks.tracks_by_state).map(([st, count]) => {
                    const pct = summary.tracks.total_tracks > 0
                      ? Math.round((count / summary.tracks.total_tracks) * 100)
                      : 0;
                    return (
                      <div key={st} style={{ marginBottom: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', marginBottom: '2px' }}>
                          <span className="font-mono uppercase-tracking">{st}</span>
                          <span className="font-mono text-muted">{count} ({pct}%)</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--bg-canvas)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${pct}%`,
                              height: '100%',
                              backgroundColor:
                                st === 'ACTIVE'
                                  ? 'var(--status-success)'
                                  : st === 'LOST' || st === 'ARCHIVED'
                                  ? 'var(--status-critical)'
                                  : 'var(--status-warning)',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </Card>

            {/* Alerts by Severity */}
            <Card title="Alerts by Severity">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
                {Object.entries(summary.alerts.alerts_by_severity).length === 0 ? (
                  <p className="text-muted text-xs">No alert severity records.</p>
                ) : (
                  Object.entries(summary.alerts.alerts_by_severity).map(([sev, count]) => {
                    const pct = summary.alerts.total_alerts > 0
                      ? Math.round((count / summary.alerts.total_alerts) * 100)
                      : 0;
                    return (
                      <div key={sev} style={{ marginBottom: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', marginBottom: '2px' }}>
                          <span className="font-mono uppercase-tracking">{sev}</span>
                          <span className="font-mono text-muted">{count} ({pct}%)</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--bg-canvas)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${pct}%`,
                              height: '100%',
                              backgroundColor:
                                sev === 'CRITICAL' || sev === 'HIGH'
                                  ? 'var(--status-critical)'
                                  : sev === 'MEDIUM'
                                  ? 'var(--status-warning)'
                                  : 'var(--status-info)',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </Card>

            {/* Threats by Level */}
            <Card title="Threat Assessments by Level">
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
                {Object.entries(summary.threats.threats_by_level).length === 0 ? (
                  <p className="text-muted text-xs">No threat level records.</p>
                ) : (
                  Object.entries(summary.threats.threats_by_level).map(([lvl, count]) => {
                    const pct = summary.threats.total_assessments > 0
                      ? Math.round((count / summary.threats.total_assessments) * 100)
                      : 0;
                    return (
                      <div key={lvl} style={{ marginBottom: '6px' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: 'var(--text-xs)', marginBottom: '2px' }}>
                          <span className="font-mono uppercase-tracking">{lvl}</span>
                          <span className="font-mono text-muted">{count} ({pct}%)</span>
                        </div>
                        <div style={{ width: '100%', height: '6px', backgroundColor: 'var(--bg-canvas)', borderRadius: '3px', overflow: 'hidden' }}>
                          <div
                            style={{
                              width: `${pct}%`,
                              height: '100%',
                              backgroundColor:
                                lvl === 'CRITICAL' || lvl === 'HIGH'
                                  ? 'var(--status-critical)'
                                  : lvl === 'MEDIUM'
                                  ? 'var(--status-warning)'
                                  : 'var(--status-info)',
                            }}
                          />
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            </Card>
          </div>
        </div>
      )}
    </div>
  );
};
