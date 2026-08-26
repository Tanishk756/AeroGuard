import React, { useCallback, useEffect, useState } from 'react';
import { getThreats } from '../api/threats';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { ThreatAssessment } from '../types';

export const ThreatsPage: React.FC = () => {
  const [threats, setThreats] = useState<ThreatAssessment[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [levelFilter, setLevelFilter] = useState<string>('');
  const [minScore, setMinScore] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchThreats = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getThreats({
        level: levelFilter || undefined,
        min_score: minScore ? Number(minScore) : undefined,
        limit: 50,
      });
      setThreats(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query threat assessments');
    } finally {
      setIsLoading(false);
    }
  }, [levelFilter, minScore]);

  useEffect(() => {
    fetchThreats();
  }, [fetchThreats]);

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header & Filter Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
            Operational Threat Assessment Triage
          </h1>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Deterministic operational priority scoring based on speed, altitude, heading, proximity, and source diversity.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <select
            className="tactical-select font-mono"
            value={levelFilter}
            onChange={(e) => setLevelFilter(e.target.value)}
          >
            <option value="">ALL THREAT LEVELS</option>
            <option value="CRITICAL">CRITICAL (≥ 80)</option>
            <option value="HIGH">HIGH (60 - 79)</option>
            <option value="MEDIUM">MEDIUM (40 - 59)</option>
            <option value="LOW">LOW (20 - 39)</option>
            <option value="NONE">NONE (&lt; 20)</option>
          </select>

          <Button variant="secondary" size="sm" onClick={fetchThreats} isLoading={isLoading}>
            Refresh
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchThreats} />}

      {/* Threat Assessments Table */}
      <Card
        title="Evaluated Operational Threat Postures"
        badge={<span className="font-mono text-xs text-muted">TOTAL: {total}</span>}
        bodyStyle={{ padding: 0 }}
      >
        {isLoading && threats.length === 0 ? (
          <LoadingState message="Loading threat assessments..." />
        ) : threats.length === 0 ? (
          <EmptyState title="No Threat Assessments" description="No operational threats match the filter criteria." />
        ) : (
          <div className="tactical-table-wrapper">
            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Threat Level</th>
                  <th>Track Ref</th>
                  <th>Operational Priority Score (0-100)</th>
                  <th>Contributing Factors</th>
                  <th>Last Evaluated (UTC)</th>
                </tr>
              </thead>
              <tbody>
                {threats.map((th) => (
                  <tr key={th.id}>
                    <td>
                      <StatusBadge status={th.level} />
                    </td>
                    <td className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                      {th.track_id}
                    </td>
                    <td>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                        <div
                          style={{
                            width: '100px',
                            height: '8px',
                            backgroundColor: 'var(--bg-canvas)',
                            borderRadius: '4px',
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              width: `${Math.min(100, Math.max(0, th.score))}%`,
                              height: '100%',
                              backgroundColor:
                                th.score >= 80
                                  ? 'var(--status-critical)'
                                  : th.score >= 60
                                  ? 'var(--status-warning)'
                                  : th.score >= 40
                                  ? '#eab308'
                                  : 'var(--status-info)',
                            }}
                          />
                        </div>
                        <span className="font-mono text-sm" style={{ fontWeight: 600 }}>
                          {th.score.toFixed(1)}
                        </span>
                      </div>
                    </td>
                    <td className="font-mono text-xs text-muted" style={{ maxWidth: '320px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {th.factors ? Object.entries(th.factors).map(([k, v]) => `${k}:${v}`).join(', ') : 'None'}
                    </td>
                    <td className="font-mono text-xs text-muted">
                      {th.created_at.substring(11, 19)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
