import React, { useState } from 'react';
import { queryReplaySnapshot, stepReplay } from '../api/replay';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { ReplayRequest, ReplaySnapshot } from '../types';

export const ReplayPage: React.FC = () => {
  const [startTime, setStartTime] = useState<string>('2026-08-26T00:00:00Z');
  const [endTime, setEndTime] = useState<string>('2026-08-26T23:59:59Z');
  const [stepInterval, setStepInterval] = useState<number>(5.0);

  const [snapshot, setSnapshot] = useState<ReplaySnapshot | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const getActiveRequest = (): ReplayRequest => ({
    start_time: startTime,
    end_time: endTime,
    step_interval_seconds: stepInterval,
    filters: {},
  });

  const handleQueryInitialSnapshot = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const snap = await queryReplaySnapshot(getActiveRequest());
      setSnapshot(snap);
      setCurrentStep(0);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Replay query failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStepForward = async () => {
    if (!snapshot) return;
    setIsLoading(true);
    setError(null);
    try {
      const snap = await stepReplay({
        request: getActiveRequest(),
        current_step: currentStep,
        steps_to_advance: 1,
      });
      setSnapshot(snap);
      setCurrentStep(snap.step_index);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Replay step failed');
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
          Deterministic Historical Replay (F6 API Backend)
        </h1>
        <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
          Stateless virtual clock state reconstruction at discrete timestamp T. Zero simulation writes or DB mutation.
        </p>
      </div>

      {error && <ErrorState message={error} />}

      {/* Control Panel */}
      <Card title="Replay Configuration & Controls">
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-md)', alignItems: 'flex-end' }}>
          <div>
            <label className="uppercase-tracking" style={{ display: 'block', marginBottom: '4px' }}>Start Time (UTC)</label>
            <input
              type="text"
              className="tactical-input font-mono"
              value={startTime}
              onChange={(e) => setStartTime(e.target.value)}
              placeholder="YYYY-MM-DDTHH:MM:SSZ"
            />
          </div>

          <div>
            <label className="uppercase-tracking" style={{ display: 'block', marginBottom: '4px' }}>End Time (UTC)</label>
            <input
              type="text"
              className="tactical-input font-mono"
              value={endTime}
              onChange={(e) => setEndTime(e.target.value)}
              placeholder="YYYY-MM-DDTHH:MM:SSZ"
            />
          </div>

          <div>
            <label className="uppercase-tracking" style={{ display: 'block', marginBottom: '4px' }}>Step Interval (s)</label>
            <input
              type="number"
              className="tactical-input font-mono"
              value={stepInterval}
              onChange={(e) => setStepInterval(Number(e.target.value))}
              min={0.1}
              step={1}
            />
          </div>

          <div style={{ display: 'flex', gap: 'var(--space-sm)' }}>
            <Button variant="primary" size="sm" onClick={handleQueryInitialSnapshot} isLoading={isLoading}>
              Initialize Replay
            </Button>
            <Button variant="secondary" size="sm" onClick={handleStepForward} disabled={!snapshot || snapshot.is_complete} isLoading={isLoading}>
              Step +1 Δt
            </Button>
          </div>
        </div>
      </Card>

      {/* Replay State View */}
      {isLoading && !snapshot ? (
        <LoadingState message="Reconstructing historical operational state..." />
      ) : snapshot ? (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {/* Virtual Clock Status Bar */}
          <div
            style={{
              padding: 'var(--space-sm) var(--space-md)',
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--border-medium)',
              borderRadius: 'var(--radius-sm)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 'var(--space-md)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
              <span className="font-mono text-sm">
                VIRTUAL TIMESTAMP: <strong style={{ color: 'var(--color-accent)' }}>{snapshot.replay_timestamp}</strong>
              </span>
              <span className="font-mono text-xs text-muted">
                STEP: {snapshot.step_index}
              </span>
            </div>

            <div>
              <StatusBadge status={snapshot.is_complete ? 'RESOLVED' : 'ACTIVE'} label={snapshot.is_complete ? 'COMPLETED' : 'STEPPING'} />
            </div>
          </div>

          {/* Reconstructed State Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
            <Card
              title="Active Tracks at Timestamp T"
              badge={<span className="font-mono text-xs text-muted">TRACKS: {snapshot.active_tracks.length}</span>}
              bodyStyle={{ padding: 0 }}
            >
              {snapshot.active_tracks.length === 0 ? (
                <EmptyState title="No Active Tracks" description="No tracks were active at this virtual timestamp." />
              ) : (
                <div className="tactical-table-wrapper" style={{ maxHeight: '250px' }}>
                  <table className="tactical-table">
                    <thead>
                      <tr>
                        <th>Track ID</th>
                        <th>State</th>
                        <th>Classification</th>
                        <th>Coordinates</th>
                        <th>Conf</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshot.active_tracks.map((t) => (
                        <tr key={t.track_id}>
                          <td className="font-mono" style={{ fontWeight: 600 }}>{t.track_id}</td>
                          <td><StatusBadge status={t.state} /></td>
                          <td className="uppercase-tracking text-xs">{t.classification}</td>
                          <td className="font-mono text-xs">{t.latitude.toFixed(4)}°, {t.longitude.toFixed(4)}°</td>
                          <td className="font-mono text-xs">{Math.round(t.confidence * 100)}%</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>

            <Card
              title="Active Alerts & Threats at Timestamp T"
              badge={
                <span className="font-mono text-xs text-muted">
                  ALERTS: {snapshot.active_alerts.length} • THREATS: {snapshot.active_threats.length}
                </span>
              }
              bodyStyle={{ padding: 0 }}
            >
              {snapshot.active_alerts.length === 0 && snapshot.active_threats.length === 0 ? (
                <EmptyState title="No Active Alerts / Threats" description="Zero open alerts or threat assessments at this timestamp." />
              ) : (
                <div className="tactical-table-wrapper" style={{ maxHeight: '250px' }}>
                  <table className="tactical-table">
                    <thead>
                      <tr>
                        <th>Severity / Level</th>
                        <th>Type / Track</th>
                        <th>Reason / Score</th>
                      </tr>
                    </thead>
                    <tbody>
                      {snapshot.active_alerts.map((a) => (
                        <tr key={a.id}>
                          <td><StatusBadge status={a.severity} /></td>
                          <td className="font-mono text-xs">{a.type}</td>
                          <td>{a.reason}</td>
                        </tr>
                      ))}
                      {snapshot.active_threats.map((th) => (
                        <tr key={th.id}>
                          <td><StatusBadge status={th.level} /></td>
                          <td className="font-mono text-xs">{th.track_id}</td>
                          <td className="font-mono text-xs">Score: {th.score.toFixed(1)}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              )}
            </Card>
          </div>
        </div>
      ) : (
        <Card>
          <EmptyState
            title="Replay Session Uninitialized"
            description="Configure a valid historical time window and initialize the replay engine to reconstruct past operational awareness."
          />
        </Card>
      )}
    </div>
  );
};
