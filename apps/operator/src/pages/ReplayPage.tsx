import React, { useEffect, useMemo, useState } from 'react';
import { getGeofences } from '../api/geofences';
import { compareReplayHistories, queryReplaySnapshot, stepReplay } from '../api/replay';
import { getSensors } from '../api/sensors';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { TacticalMap } from '../components/map/TacticalMap';
import { Geofence, ReplayComparisonReport, ReplayRequest, ReplaySnapshot, Sensor, Track } from '../types';

export const ReplayPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'replay' | 'compare'>('replay');
  const [startTime, setStartTime] = useState<string>('2026-08-26T00:00:00Z');
  const [endTime, setEndTime] = useState<string>('2026-08-26T23:59:59Z');
  const [stepInterval, setStepInterval] = useState<number>(5.0);

  const [snapshot, setSnapshot] = useState<ReplaySnapshot | null>(null);
  const [currentStep, setCurrentStep] = useState<number>(0);
  const [selectedTrackId, setSelectedTrackId] = useState<string | null>(null);
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [geofences, setGeofences] = useState<Geofence[]>([]);

  // Comparison mode state
  const [compareStartTime2, setCompareStartTime2] = useState<string>('2026-08-26T00:00:00Z');
  const [compareEndTime2, setCompareEndTime2] = useState<string>('2026-08-26T23:59:59Z');
  const [compareReport, setCompareReport] = useState<ReplayComparisonReport | null>(null);
  const [isComparing, setIsComparing] = useState<boolean>(false);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  // Load sensors and geofences for spatial context
  useEffect(() => {
    getSensors().then((res) => setSensors(res.items || [])).catch(() => setSensors([]));
    getGeofences().then((res) => setGeofences(res.items || [])).catch(() => setGeofences([]));
  }, []);

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
      setSelectedTrackId(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Replay query failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleStep = async (steps: number) => {
    if (!snapshot) return;
    setIsLoading(true);
    setError(null);
    try {
      const snap = await stepReplay({
        request: getActiveRequest(),
        current_step: currentStep,
        steps_to_advance: steps,
      });
      setSnapshot(snap);
      setCurrentStep(snap.step_index);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Replay step failed');
    } finally {
      setIsLoading(false);
    }
  };

  const handleCompare = async () => {
    setIsComparing(true);
    setError(null);
    try {
      const report = await compareReplayHistories({
        request_1: {
          start_time: startTime,
          end_time: endTime,
          step_interval_seconds: stepInterval,
        },
        request_2: {
          start_time: compareStartTime2,
          end_time: compareEndTime2,
          step_interval_seconds: stepInterval,
        },
      });
      setCompareReport(report);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Historical comparison failed');
    } finally {
      setIsComparing(false);
    }
  };

  // Map ReplayTrackState[] into Track[] for TacticalMap presentation
  const replayTracks = useMemo<Track[]>(() => {
    if (!snapshot) return [];
    const ts = snapshot.replay_time || snapshot.replay_timestamp || new Date().toISOString();
    return snapshot.active_tracks.map((t) => ({
      id: t.track_id,
      state: t.state,
      latitude: t.latitude,
      longitude: t.longitude,
      altitude: t.altitude ?? undefined,
      velocity: t.velocity ?? undefined,
      heading: t.heading ?? undefined,
      confidence: t.confidence,
      classification: t.classification,
      source_count: t.source_count,
      last_seen_at: ts,
      first_seen_at: ts,
      created_at: ts,
      updated_at: ts,
    }));
  }, [snapshot]);

  const selectedTrack = replayTracks.find((t) => t.id === selectedTrackId);

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--status-info)', borderRadius: '1px' }} />
            <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
              Deterministic Historical Replay (F6 Engine)
            </h1>
          </div>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Stateless virtual clock state reconstruction and scenario comparison. Replay mode is strictly read-only and does not mutate live operational memory.
          </p>
        </div>

        {/* View Mode Tabs */}
        <div style={{ display: 'flex', gap: '4px' }}>
          <Button
            variant={activeTab === 'replay' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('replay')}
            style={{ padding: '4px 10px', fontSize: '11px' }}
          >
            Replay Map View
          </Button>
          <Button
            variant={activeTab === 'compare' ? 'primary' : 'ghost'}
            size="sm"
            onClick={() => setActiveTab('compare')}
            style={{ padding: '4px 10px', fontSize: '11px' }}
          >
            Historical Run Comparison
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} />}

      {activeTab === 'replay' ? (
        <>
          {/* Replay Controls Card */}
          <Card title="Virtual Clock & Stepping Controls">
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-md)', alignItems: 'flex-end' }}>
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
                <label className="uppercase-tracking" style={{ display: 'block', marginBottom: '4px' }}>Step Δt (seconds)</label>
                <input
                  type="number"
                  className="tactical-input font-mono"
                  value={stepInterval}
                  onChange={(e) => setStepInterval(Number(e.target.value))}
                  min={0.1}
                  step={1}
                />
              </div>

              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)' }}>
                <Button variant="primary" size="sm" onClick={handleQueryInitialSnapshot} isLoading={isLoading}>
                  ▶ Initialize Replay
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleStep(1)}
                  disabled={!snapshot || snapshot.is_complete || isLoading}
                  isLoading={isLoading}
                >
                  Step +1 Δt
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  onClick={() => handleStep(5)}
                  disabled={!snapshot || snapshot.is_complete || isLoading}
                  isLoading={isLoading}
                >
                  Step +5 Δt
                </Button>
              </div>
            </div>
          </Card>

          {/* Virtual Clock Status Bar */}
          {snapshot && (
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
                  REPLAY VIRTUAL CLOCK: <strong style={{ color: 'var(--color-accent)' }}>{snapshot.replay_time || snapshot.replay_timestamp}</strong>
                </span>
                <span className="font-mono text-xs text-muted">
                  STEP INDEX: {snapshot.step_index}
                </span>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flexWrap: 'wrap' }}>
                <span className="font-mono text-xs text-muted">TRACKS: {snapshot.active_tracks.length}</span>
                <span className="font-mono text-xs text-muted">
                  GROUPS: {snapshot.intelligence?.groups?.length ?? snapshot.group_hulls?.length ?? 0}
                </span>
                <span className="font-mono text-xs text-muted">
                  FORMATIONS: {snapshot.intelligence?.formations?.length ?? 0}
                </span>
                <StatusBadge
                  status={snapshot.is_complete ? 'RESOLVED' : 'ACTIVE'}
                  label={snapshot.is_complete ? 'REPLAY COMPLETED' : 'REPLAY ACTIVE'}
                />
              </div>
            </div>
          )}

          {/* Replay Spatial Map + Inspector Split */}
          {isLoading && !snapshot ? (
            <LoadingState message="Reconstructing historical operational state from backend..." />
          ) : snapshot ? (
            <div style={{ display: 'grid', gridTemplateColumns: 'minmax(400px, 2fr) minmax(320px, 1fr)', gap: 'var(--space-md)', minHeight: '440px' }}>
              {/* Tactical Map Viewport for Replay */}
              <div style={{ height: '100%', minHeight: '440px' }}>
                <TacticalMap
                  tracks={replayTracks}
                  multiTrackIntelligence={snapshot.intelligence || null}
                  sensors={sensors}
                  geofences={geofences}
                  selectedTrackId={selectedTrackId}
                  onSelectTrack={setSelectedTrackId}
                  onClearSelection={() => setSelectedTrackId(null)}
                />
              </div>

              {/* Reconstructed State Inspector */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', overflowY: 'auto', maxHeight: '540px' }}>
                {selectedTrack ? (
                  <Card title={`Replay Track: ${selectedTrack.id}`}>
                    <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
                      <div className="kv-row">
                        <span className="kv-key">State</span>
                        <StatusBadge status={selectedTrack.state} />
                      </div>
                      <div className="kv-row">
                        <span className="kv-key">Classification</span>
                        <span className="kv-value uppercase-tracking">{selectedTrack.classification}</span>
                      </div>
                      <div className="kv-row">
                        <span className="kv-key">Confidence</span>
                        <span className="kv-value font-mono">{Math.round(selectedTrack.confidence * 100)}%</span>
                      </div>
                      <div className="kv-row">
                        <span className="kv-key">Sensors</span>
                        <span className="kv-value font-mono">{selectedTrack.source_count}</span>
                      </div>
                      <div className="kv-row">
                        <span className="kv-key">Coordinates</span>
                        <span className="kv-value font-mono text-xs">
                          {selectedTrack.latitude.toFixed(4)}°, {selectedTrack.longitude.toFixed(4)}°
                        </span>
                      </div>
                      <div className="kv-row">
                        <span className="kv-key">Velocity</span>
                        <span className="kv-value font-mono text-xs">
                          {selectedTrack.velocity != null ? `${selectedTrack.velocity.toFixed(1)} m/s` : 'N/A'}
                        </span>
                      </div>

                      {/* AI Intelligence Overlays for Track */}
                      {(() => {
                        const beh = snapshot.intelligence?.behaviors?.find((b) => b.track_id === selectedTrack.id);
                        const pri = snapshot.intelligence?.priorities?.find((p) => p.track_id === selectedTrack.id);
                        const grp = (snapshot.intelligence?.groups || snapshot.group_hulls || []).find((g) =>
                          g.member_track_ids.includes(selectedTrack.id)
                        );
                        return (
                          <>
                            {grp && (
                              <div className="kv-row" style={{ gridColumn: 'span 2' }}>
                                <span className="kv-key">Swarm Group</span>
                                <span className="kv-value font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                                  {grp.group_id} ({grp.member_count} tracks)
                                </span>
                              </div>
                            )}
                            {beh && (
                              <div className="kv-row" style={{ gridColumn: 'span 2' }}>
                                <span className="kv-key">AI Behavior</span>
                                <span className="kv-value font-mono text-xs">
                                  {beh.state} ({Math.round(beh.confidence * 100)}%)
                                </span>
                              </div>
                            )}
                            {pri && (
                              <div className="kv-row" style={{ gridColumn: 'span 2' }}>
                                <span className="kv-key">AI Priority</span>
                                <span className="kv-value font-mono text-xs" style={{ fontWeight: 700, color: pri.priority_level === 'CRITICAL' ? 'var(--status-critical)' : 'var(--color-accent)' }}>
                                  {pri.priority_score.toFixed(1)} ({pri.priority_level})
                                </span>
                              </div>
                            )}
                          </>
                        );
                      })()}
                    </div>
                  </Card>
                ) : (
                  <Card title="Track Inspection">
                    <EmptyState title="No Track Selected" description="Click any track marker on the replay map or table to inspect historical kinematics." />
                  </Card>
                )}

                {/* Historical Swarm Groups at Timestamp T */}
                <Card
                  title="Historical Swarm Groups (T)"
                  badge={
                    <span className="font-mono text-xs text-muted">
                      {(snapshot.intelligence?.groups || snapshot.group_hulls || []).length}
                    </span>
                  }
                >
                  {(snapshot.intelligence?.groups || snapshot.group_hulls || []).length === 0 ? (
                    <p className="font-mono text-xs text-muted">Zero swarm groups detected at this virtual timestamp.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                      {(snapshot.intelligence?.groups || snapshot.group_hulls || []).map((grp) => {
                        const fmt = snapshot.intelligence?.formations?.find((f) => f.group_id === grp.group_id);
                        return (
                          <div
                            key={grp.group_id}
                            style={{
                              padding: '6px 8px',
                              backgroundColor: 'var(--bg-canvas)',
                              border: '1px solid var(--border-subtle)',
                              borderRadius: 'var(--radius-sm)',
                              display: 'flex',
                              flexDirection: 'column',
                              gap: '2px',
                              fontSize: '11px',
                            }}
                          >
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                              <span className="font-mono" style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
                                {grp.group_id}
                              </span>
                              <span className="font-mono text-xs text-muted">
                                {grp.member_count} tracks • {Math.round(grp.radius_meters)}m
                              </span>
                            </div>
                            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', color: 'var(--text-muted)' }}>
                              <span>State: {grp.behavioral_state}</span>
                              {fmt && (
                                <span className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                                  Sync: {(fmt.synchronization_index * 100).toFixed(0)}%
                                </span>
                              )}
                            </div>
                            <div className="font-mono text-xs text-muted" style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              [{grp.member_track_ids.join(', ')}]
                            </div>
                          </div>
                        );
                      })}
                    </div>
                  )}
                </Card>

                {/* Active Alerts at Timestamp T */}
                <Card title="Active Alerts at Timestamp T" badge={<span className="font-mono text-xs text-muted">{snapshot.active_alerts.length}</span>}>
                  {snapshot.active_alerts.length === 0 ? (
                    <p className="font-mono text-xs text-muted">Zero alerts active at this virtual timestamp.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {snapshot.active_alerts.map((a) => (
                        <div
                          key={a.id}
                          style={{
                            padding: '4px 6px',
                            backgroundColor: 'var(--bg-canvas)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: '11px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <StatusBadge status={a.severity} />
                            <span className="font-mono">{a.type}</span>
                          </div>
                          <span className="text-muted font-mono text-xs">{a.track_id || '-'}</span>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>

                {/* Active Threats at Timestamp T */}
                <Card title="Threat Triage at Timestamp T" badge={<span className="font-mono text-xs text-muted">{snapshot.active_threats.length}</span>}>
                  {snapshot.active_threats.length === 0 ? (
                    <p className="font-mono text-xs text-muted">Zero elevated threats active at this virtual timestamp.</p>
                  ) : (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {snapshot.active_threats.map((th) => (
                        <div
                          key={th.id}
                          style={{
                            padding: '4px 6px',
                            backgroundColor: 'var(--bg-canvas)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                            fontSize: '11px',
                          }}
                        >
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <StatusBadge status={th.level} />
                            <span className="font-mono text-xs">TRK: {th.track_id}</span>
                          </div>
                          <span className="font-mono text-xs" style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
                            {th.score.toFixed(1)}
                          </span>
                        </div>
                      ))}
                    </div>
                  )}
                </Card>
              </div>
            </div>
          ) : (
            <Card>
              <EmptyState
                title="Replay Session Uninitialized"
                description="Configure a historical start/end time window above and click 'Initialize Replay' to reconstruct past situational awareness on the tactical map."
              />
            </Card>
          )}
        </>
      ) : (
        /* Comparison Mode */
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          <Card title="Compare Two Historical Scenario / Replay Runs">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-md)' }}>
              {/* Run 1 Config */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', padding: 'var(--space-sm)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
                <div className="font-mono text-xs uppercase-tracking" style={{ fontWeight: 700, color: 'var(--color-accent)' }}>
                  RUN 1 SPECIFICATION
                </div>
                <div>
                  <label className="text-muted text-xs">Start Time (UTC)</label>
                  <input type="text" className="tactical-input font-mono" value={startTime} onChange={(e) => setStartTime(e.target.value)} />
                </div>
                <div>
                  <label className="text-muted text-xs">End Time (UTC)</label>
                  <input type="text" className="tactical-input font-mono" value={endTime} onChange={(e) => setEndTime(e.target.value)} />
                </div>
              </div>

              {/* Run 2 Config */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)', padding: 'var(--space-sm)', border: '1px solid var(--border-subtle)', borderRadius: 'var(--radius-sm)' }}>
                <div className="font-mono text-xs uppercase-tracking" style={{ fontWeight: 700, color: 'var(--color-accent)' }}>
                  RUN 2 SPECIFICATION
                </div>
                <div>
                  <label className="text-muted text-xs">Start Time (UTC)</label>
                  <input type="text" className="tactical-input font-mono" value={compareStartTime2} onChange={(e) => setCompareStartTime2(e.target.value)} />
                </div>
                <div>
                  <label className="text-muted text-xs">End Time (UTC)</label>
                  <input type="text" className="tactical-input font-mono" value={compareEndTime2} onChange={(e) => setCompareEndTime2(e.target.value)} />
                </div>
              </div>
            </div>

            <div style={{ marginTop: 'var(--space-md)', display: 'flex', justifyContent: 'flex-end' }}>
              <Button variant="primary" size="sm" onClick={handleCompare} isLoading={isComparing}>
                Execute Deterministic Comparison
              </Button>
            </div>
          </Card>

          {/* Comparison Report Display */}
          {compareReport && (
            <Card
              title="Deterministic Comparison Report"
              badge={<StatusBadge status={compareReport.identical ? 'ACTIVE' : 'WARNING'} label={compareReport.identical ? 'IDENTICAL RUNS' : 'VARIANCE DETECTED'} />}
            >
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: 'var(--space-sm)' }}>
                <div className="kv-row">
                  <span className="kv-key">Tracks Match</span>
                  <StatusBadge status={compareReport.total_tracks_match ? 'ACTIVE' : 'WARNING'} label={compareReport.total_tracks_match ? 'MATCH' : 'DIVERGED'} />
                </div>
                <div className="kv-row">
                  <span className="kv-key">Alerts Match</span>
                  <StatusBadge status={compareReport.total_alerts_match ? 'ACTIVE' : 'WARNING'} label={compareReport.total_alerts_match ? 'MATCH' : 'DIVERGED'} />
                </div>
                <div className="kv-row">
                  <span className="kv-key">Threats Match</span>
                  <StatusBadge status={compareReport.total_threats_match ? 'ACTIVE' : 'WARNING'} label={compareReport.total_threats_match ? 'MATCH' : 'DIVERGED'} />
                </div>
                <div className="kv-row">
                  <span className="kv-key">Detections (R1 / R2)</span>
                  <span className="kv-value font-mono">{compareReport.detections_count_1} / {compareReport.detections_count_2}</span>
                </div>
              </div>
            </Card>
          )}
        </div>
      )}
    </div>
  );
};
