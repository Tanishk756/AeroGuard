import React, { useCallback, useEffect, useState } from 'react';
import { getAlerts } from '../api/alerts';
import { getTimeline } from '../api/history';
import { getSensors } from '../api/sensors';
import { getThreats } from '../api/threats';
import { getTracks } from '../api/tracks';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { AlertPanel } from '../components/workspace/AlertPanel';
import { MapWorkspace } from '../components/workspace/MapWorkspace';
import { ThreatPanel } from '../components/workspace/ThreatPanel';
import { TimelinePanel } from '../components/workspace/TimelinePanel';
import { TrackPanel } from '../components/workspace/TrackPanel';
import { useAuth } from '../context/AuthContext';
import { Alert, Sensor, ThreatAssessment, TimelineItem, Track } from '../types';

export const OverviewPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const [tracks, setTracks] = useState<Track[]>([]);
  const [alerts, setAlerts] = useState<Alert[]>([]);
  const [threats, setThreats] = useState<ThreatAssessment[]>([]);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [timeline, setTimeline] = useState<TimelineItem[]>([]);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchOverviewData = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const promises: Promise<void>[] = [];

      if (hasPermission('tracks.read')) {
        promises.push(
          getTracks({ limit: 50 }).then((res) => setTracks(res.items)).catch(() => setTracks([]))
        );
      }

      if (hasPermission('alerts.read')) {
        promises.push(
          getAlerts({ limit: 20 }).then((res) => setAlerts(res.items)).catch(() => setAlerts([]))
        );
      }

      if (hasPermission('threats.read')) {
        promises.push(
          getThreats({ limit: 20 }).then((res) => setThreats(res.items)).catch(() => setThreats([]))
        );
      }

      if (hasPermission('sensors.read')) {
        promises.push(
          getSensors({ limit: 50 }).then((res) => setSensors(res.items)).catch(() => setSensors([]))
        );
      }

      // Timeline can be queried if user has any operational read permission
      promises.push(
        getTimeline({ limit: 20 }).then((res) => setTimeline(res.items)).catch(() => setTimeline([]))
      );

      await Promise.allSettled(promises);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : 'Failed to query operational overview';
      setError(msg);
    } finally {
      setIsLoading(false);
    }
  }, [hasPermission]);

  useEffect(() => {
    fetchOverviewData();
  }, [fetchOverviewData]);

  const activeTracksCount = tracks.filter((t) => t.state === 'ACTIVE' || t.state === 'NEW').length;
  const openAlertsCount = alerts.filter((a) => a.status === 'OPEN').length;
  const elevatedThreatsCount = threats.filter((th) => th.level === 'HIGH' || th.level === 'CRITICAL').length;
  const onlineSensorsCount = sensors.filter((s) => s.status === 'ACTIVE').length;

  return (
    <div
      style={{
        padding: 'var(--space-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md)',
        flex: 1,
      }}
    >
      {/* Top Telemetry KPI Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
          gap: 'var(--space-sm)',
        }}
      >
        <Card style={{ padding: '0' }} bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted">Active Tracks</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span className="font-mono" style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--color-accent)' }}>
              {activeTracksCount}
            </span>
            <span className="font-mono text-xs text-muted">TOTAL: {tracks.length}</span>
          </div>
        </Card>

        <Card style={{ padding: '0' }} bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted">Open Alerts</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span
              className="font-mono"
              style={{
                fontSize: 'var(--text-2xl)',
                fontWeight: 700,
                color: openAlertsCount > 0 ? 'var(--status-critical)' : 'var(--status-success)',
              }}
            >
              {openAlertsCount}
            </span>
            <span className="font-mono text-xs text-muted">TOTAL: {alerts.length}</span>
          </div>
        </Card>

        <Card style={{ padding: '0' }} bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted">Elevated Threats</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span
              className="font-mono"
              style={{
                fontSize: 'var(--text-2xl)',
                fontWeight: 700,
                color: elevatedThreatsCount > 0 ? 'var(--status-warning)' : 'var(--text-secondary)',
              }}
            >
              {elevatedThreatsCount}
            </span>
            <span className="font-mono text-xs text-muted">TRIAGED: {threats.length}</span>
          </div>
        </Card>

        <Card style={{ padding: '0' }} bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted">Online Sensors</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span className="font-mono" style={{ fontSize: 'var(--text-2xl)', fontWeight: 700, color: 'var(--status-success)' }}>
              {onlineSensorsCount}
            </span>
            <span className="font-mono text-xs text-muted">CONFIGURED: {sensors.length}</span>
          </div>
        </Card>
      </div>

      {/* Primary Workspace: Map */}
      <div style={{ flex: '0 0 auto', minHeight: '340px' }}>
        <MapWorkspace
          tracks={tracks}
          selectedTrackId={selectedTrackId}
          onSelectTrack={setSelectedTrackId}
        />
      </div>

      {/* Operational Panels Grid */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(400px, 1fr))',
          gap: 'var(--space-md)',
          flex: 1,
        }}
      >
        <TrackPanel
          tracks={tracks}
          selectedTrackId={selectedTrackId}
          onSelectTrack={setSelectedTrackId}
          isLoading={isLoading}
          error={error}
          onRefresh={fetchOverviewData}
        />

        <ThreatPanel
          threats={threats}
          isLoading={isLoading}
          error={error}
          onRefresh={fetchOverviewData}
        />

        <AlertPanel
          alerts={alerts}
          isLoading={isLoading}
          error={error}
          onRefresh={fetchOverviewData}
        />

        <TimelinePanel
          timeline={timeline}
          isLoading={isLoading}
          error={error}
          onRefresh={fetchOverviewData}
        />
      </div>
    </div>
  );
};
