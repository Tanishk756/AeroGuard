import React, { useCallback, useEffect, useState } from 'react';
import { getHistoricalAlerts, getHistoricalDetections, getHistoricalThreats, getTimeline } from '../api/history';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { HistoricalAlertItem, HistoricalDetectionItem, HistoricalThreatItem, TimelineItem } from '../types';

type HistoryTab = 'detections' | 'alerts' | 'threats' | 'timeline';

export const HistoryPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<HistoryTab>('detections');
  const [startTime, setStartTime] = useState<string>('');
  const [endTime, setEndTime] = useState<string>('');

  const [detections, setDetections] = useState<HistoricalDetectionItem[]>([]);
  const [alerts, setAlerts] = useState<HistoricalAlertItem[]>([]);
  const [threats, setThreats] = useState<HistoricalThreatItem[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [total, setTotal] = useState<number>(0);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchHistoricalData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const params = {
        start_time: startTime || undefined,
        end_time: endTime || undefined,
        limit: 50,
      };

      if (activeTab === 'detections') {
        const res = await getHistoricalDetections(params);
        setDetections(res.items);
        setTotal(res.total);
      } else if (activeTab === 'alerts') {
        const res = await getHistoricalAlerts(params);
        setAlerts(res.items);
        setTotal(res.total);
      } else if (activeTab === 'threats') {
        const res = await getHistoricalThreats(params);
        setThreats(res.items);
        setTotal(res.total);
      } else if (activeTab === 'timeline') {
        const res = await getTimeline(params);
        setTimeline(res.items);
        setTotal(res.total);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Historical query error');
    } finally {
      setIsLoading(false);
    }
  }, [activeTab, startTime, endTime]);

  useEffect(() => {
    fetchHistoricalData();
  }, [fetchHistoricalData]);

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header & Bounded Date Time Filters */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
            Historical Telemetry & Logs
          </h1>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Bounded historical queries over immutable operational tables (Max 30-day window).
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <Button variant="secondary" size="sm" onClick={fetchHistoricalData} isLoading={isLoading}>
            Query Window
          </Button>
        </div>
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-medium)', paddingBottom: '2px' }}>
        <button
          className="tactical-btn"
          onClick={() => setActiveTab('detections')}
          style={{
            backgroundColor: activeTab === 'detections' ? 'var(--bg-surface-active)' : 'transparent',
            color: activeTab === 'detections' ? 'var(--color-accent)' : 'var(--text-secondary)',
            borderColor: activeTab === 'detections' ? 'var(--color-accent)' : 'transparent',
            padding: '6px 12px',
            fontSize: 'var(--text-xs)',
          }}
        >
          Detections
        </button>
        <button
          className="tactical-btn"
          onClick={() => setActiveTab('alerts')}
          style={{
            backgroundColor: activeTab === 'alerts' ? 'var(--bg-surface-active)' : 'transparent',
            color: activeTab === 'alerts' ? 'var(--color-accent)' : 'var(--text-secondary)',
            borderColor: activeTab === 'alerts' ? 'var(--color-accent)' : 'transparent',
            padding: '6px 12px',
            fontSize: 'var(--text-xs)',
          }}
        >
          Alerts
        </button>
        <button
          className="tactical-btn"
          onClick={() => setActiveTab('threats')}
          style={{
            backgroundColor: activeTab === 'threats' ? 'var(--bg-surface-active)' : 'transparent',
            color: activeTab === 'threats' ? 'var(--color-accent)' : 'var(--text-secondary)',
            borderColor: activeTab === 'threats' ? 'var(--color-accent)' : 'transparent',
            padding: '6px 12px',
            fontSize: 'var(--text-xs)',
          }}
        >
          Threat Assessments
        </button>
        <button
          className="tactical-btn"
          onClick={() => setActiveTab('timeline')}
          style={{
            backgroundColor: activeTab === 'timeline' ? 'var(--bg-surface-active)' : 'transparent',
            color: activeTab === 'timeline' ? 'var(--color-accent)' : 'var(--text-secondary)',
            borderColor: activeTab === 'timeline' ? 'var(--color-accent)' : 'transparent',
            padding: '6px 12px',
            fontSize: 'var(--text-xs)',
          }}
        >
          Unified Timeline
        </button>
      </div>

      {error && <ErrorState message={error} onRetry={fetchHistoricalData} />}

      {/* Tab Content */}
      <Card
        title={`Historical ${activeTab.toUpperCase()}`}
        badge={<span className="font-mono text-xs text-muted">RECORDS: {total}</span>}
        bodyStyle={{ padding: 0 }}
      >
        {isLoading ? (
          <LoadingState message="Executing bounded historical SQL query..." />
        ) : activeTab === 'detections' ? (
          detections.length === 0 ? (
            <EmptyState title="No Detections Recorded" description="Zero detection records exist for the queried time window." />
          ) : (
            <div className="tactical-table-wrapper">
              <table className="tactical-table">
                <thead>
                  <tr>
                    <th>Det ID</th>
                    <th>Sensor ID</th>
                    <th>Modality</th>
                    <th>Coordinates</th>
                    <th>Alt</th>
                    <th>Confidence</th>
                    <th>Track Ref</th>
                    <th>Timestamp (UTC)</th>
                  </tr>
                </thead>
                <tbody>
                  {detections.map((d) => (
                    <tr key={d.id}>
                      <td className="font-mono" style={{ fontWeight: 600 }}>{d.id}</td>
                      <td className="font-mono text-xs text-muted">{d.sensor_id}</td>
                      <td className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>{d.source_type}</td>
                      <td className="font-mono text-xs">{d.latitude.toFixed(4)}°, {d.longitude.toFixed(4)}°</td>
                      <td className="font-mono text-xs">{d.altitude != null ? `${d.altitude.toFixed(0)}m` : '-'}</td>
                      <td className="font-mono text-xs">{Math.round(d.confidence * 100)}%</td>
                      <td className="font-mono text-xs text-muted">{d.track_id || 'Unassociated'}</td>
                      <td className="font-mono text-xs text-muted">{d.timestamp.substring(0, 19).replace('T', ' ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : activeTab === 'alerts' ? (
          alerts.length === 0 ? (
            <EmptyState title="No Historical Alerts" description="No alerts recorded in this historical range." />
          ) : (
            <div className="tactical-table-wrapper">
              <table className="tactical-table">
                <thead>
                  <tr>
                    <th>Severity</th>
                    <th>Status</th>
                    <th>Type</th>
                    <th>Reason</th>
                    <th>Track</th>
                    <th>Generated (UTC)</th>
                  </tr>
                </thead>
                <tbody>
                  {alerts.map((a) => (
                    <tr key={a.id}>
                      <td><StatusBadge status={a.severity} /></td>
                      <td><StatusBadge status={a.status} /></td>
                      <td className="font-mono text-xs">{a.type}</td>
                      <td>{a.reason}</td>
                      <td className="font-mono text-xs text-muted">{a.track_id || 'N/A'}</td>
                      <td className="font-mono text-xs text-muted">{a.created_at.substring(0, 19).replace('T', ' ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : activeTab === 'threats' ? (
          threats.length === 0 ? (
            <EmptyState title="No Historical Threats" description="No threat assessment records exist in this historical range." />
          ) : (
            <div className="tactical-table-wrapper">
              <table className="tactical-table">
                <thead>
                  <tr>
                    <th>Level</th>
                    <th>Track ID</th>
                    <th>Priority Score</th>
                    <th>Evaluated At (UTC)</th>
                  </tr>
                </thead>
                <tbody>
                  {threats.map((th) => (
                    <tr key={th.id}>
                      <td><StatusBadge status={th.level} /></td>
                      <td className="font-mono">{th.track_id}</td>
                      <td className="font-mono text-sm" style={{ fontWeight: 600 }}>{th.score.toFixed(1)}</td>
                      <td className="font-mono text-xs text-muted">{th.created_at.substring(0, 19).replace('T', ' ')}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        ) : (
          timeline.length === 0 ? (
            <EmptyState title="No Timeline Events" description="No normalized timeline events recorded in this range." />
          ) : (
            <div className="tactical-table-wrapper">
              <table className="tactical-table">
                <thead>
                  <tr>
                    <th>Timestamp (UTC)</th>
                    <th>Event Type</th>
                    <th>Entity / Track</th>
                    <th>Summary</th>
                  </tr>
                </thead>
                <tbody>
                  {timeline.map((item, idx) => (
                    <tr key={`${item.timestamp}-${item.entity_id}-${idx}`}>
                      <td className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>{item.timestamp.substring(0, 19).replace('T', ' ')}</td>
                      <td className="font-mono text-xs">{item.event_type}</td>
                      <td className="font-mono text-xs text-muted">{item.track_id || item.entity_id}</td>
                      <td>{item.summary}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        )}
      </Card>
    </div>
  );
};
