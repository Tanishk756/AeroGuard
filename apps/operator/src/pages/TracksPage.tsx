import React, { useCallback, useEffect, useState } from 'react';
import { getTrackDetail, getTrackHistory, getTracks } from '../api/tracks';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { Track, TrackHistoryPoint } from '../types';

export const TracksPage: React.FC = () => {
  const [tracks, setTracks] = useState<Track[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [selectedTrack, setSelectedTrack] = useState<Track | null>(null);
  const [trackHistory, setTrackHistory] = useState<TrackHistoryPoint[]>([]);
  const [stateFilter, setStateFilter] = useState<string>('');
  const [classificationFilter, setClassificationFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isHistoryLoading, setIsHistoryLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchTracks = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getTracks({
        state: stateFilter || undefined,
        classification: classificationFilter || undefined,
        limit: 50,
      });
      setTracks(res.items);
      setTotal(res.total);
      if (res.items.length > 0 && !selectedTrack) {
        setSelectedTrack(res.items[0]);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query track registry');
    } finally {
      setIsLoading(false);
    }
  }, [stateFilter, classificationFilter, selectedTrack]);

  useEffect(() => {
    fetchTracks();
  }, [fetchTracks]);

  useEffect(() => {
    if (selectedTrack) {
      setIsHistoryLoading(true);
      getTrackHistory(selectedTrack.id)
        .then((res) => setTrackHistory(res.items))
        .catch(() => setTrackHistory([]))
        .finally(() => setIsHistoryLoading(false));
    } else {
      setTrackHistory([]);
    }
  }, [selectedTrack]);

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header & Filter Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
            Track Management & History
          </h1>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Confirmed correlated tracks with append-only kinematic history.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <select
            className="tactical-select font-mono"
            value={stateFilter}
            onChange={(e) => setStateFilter(e.target.value)}
          >
            <option value="">ALL STATES</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="NEW">NEW</option>
            <option value="STALE">STALE</option>
            <option value="LOST">LOST</option>
            <option value="ARCHIVED">ARCHIVED</option>
          </select>

          <Button variant="secondary" size="sm" onClick={fetchTracks} isLoading={isLoading}>
            Refresh
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchTracks} />}

      {/* Main Split Content */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(320px, 1.2fr) minmax(360px, 1fr)', gap: 'var(--space-md)', flex: 1 }}>
        {/* Track List Table */}
        <Card
          title="Track Directory"
          badge={<span className="font-mono text-xs text-muted">TOTAL: {total}</span>}
          bodyStyle={{ padding: 0 }}
        >
          {isLoading && tracks.length === 0 ? (
            <LoadingState message="Loading tracks..." />
          ) : tracks.length === 0 ? (
            <EmptyState title="No Tracks Found" description="No tracks match the selected filters." />
          ) : (
            <div className="tactical-table-wrapper" style={{ maxHeight: '600px' }}>
              <table className="tactical-table">
                <thead>
                  <tr>
                    <th>Track ID</th>
                    <th>State</th>
                    <th>Class</th>
                    <th>Conf</th>
                    <th>Sources</th>
                    <th>Last Seen</th>
                  </tr>
                </thead>
                <tbody>
                  {tracks.map((t) => {
                    const isSelected = selectedTrack?.id === t.id;
                    return (
                      <tr
                        key={t.id}
                        onClick={() => setSelectedTrack(t)}
                        style={{
                          cursor: 'pointer',
                          backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                        }}
                      >
                        <td className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {t.id}
                        </td>
                        <td>
                          <StatusBadge status={t.state} />
                        </td>
                        <td className="uppercase-tracking text-xs">{t.classification}</td>
                        <td className="font-mono text-xs">{Math.round(t.confidence * 100)}%</td>
                        <td className="font-mono text-xs">{t.source_count}</td>
                        <td className="font-mono text-xs text-muted">{t.last_seen_at.substring(11, 19)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Selected Track Details & Append-Only History */}
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {selectedTrack ? (
            <>
              <Card title={`Track Details: ${selectedTrack.id}`}>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
                  <div className="kv-row">
                    <span className="kv-key">Status</span>
                    <StatusBadge status={selectedTrack.state} />
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Classification</span>
                    <span className="kv-value uppercase-tracking">{selectedTrack.classification}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Confidence</span>
                    <span className="kv-value">{Math.round(selectedTrack.confidence * 100)}%</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Sensor Count</span>
                    <span className="kv-value">{selectedTrack.source_count}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Latitude</span>
                    <span className="kv-value">{selectedTrack.latitude.toFixed(6)}°</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Longitude</span>
                    <span className="kv-value">{selectedTrack.longitude.toFixed(6)}°</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Altitude</span>
                    <span className="kv-value">{selectedTrack.altitude != null ? `${selectedTrack.altitude.toFixed(1)} m` : 'N/A'}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Velocity</span>
                    <span className="kv-value">{selectedTrack.velocity != null ? `${selectedTrack.velocity.toFixed(1)} m/s` : 'N/A'}</span>
                  </div>
                </div>
              </Card>

              <Card
                title="Append-Only Trajectory History"
                badge={<span className="font-mono text-xs text-muted">POINTS: {trackHistory.length}</span>}
                bodyStyle={{ padding: 0 }}
              >
                {isHistoryLoading ? (
                  <LoadingState message="Fetching trajectory points..." />
                ) : trackHistory.length === 0 ? (
                  <EmptyState title="No History Points" description="No trajectory history points recorded for this track." />
                ) : (
                  <div className="tactical-table-wrapper" style={{ maxHeight: '300px' }}>
                    <table className="tactical-table">
                      <thead>
                        <tr>
                          <th>Seq</th>
                          <th>Time (UTC)</th>
                          <th>Lat / Lon</th>
                          <th>Alt</th>
                          <th>Vel</th>
                          <th>State</th>
                        </tr>
                      </thead>
                      <tbody>
                        {trackHistory.map((pt) => (
                          <tr key={pt.id}>
                            <td className="font-mono text-xs">{pt.sequence}</td>
                            <td className="font-mono text-xs text-muted">{pt.timestamp.substring(11, 19)}</td>
                            <td className="font-mono text-xs">
                              {pt.latitude.toFixed(4)}°, {pt.longitude.toFixed(4)}°
                            </td>
                            <td className="font-mono text-xs">{pt.altitude != null ? `${pt.altitude.toFixed(0)}m` : '-'}</td>
                            <td className="font-mono text-xs">{pt.velocity != null ? `${pt.velocity.toFixed(1)}m/s` : '-'}</td>
                            <td><StatusBadge status={pt.state} /></td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                )}
              </Card>
            </>
          ) : (
            <Card title="Track Inspection">
              <EmptyState title="No Track Selected" description="Select a track from the directory to inspect details." />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
