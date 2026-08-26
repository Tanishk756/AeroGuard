import React from 'react';
import { ThreatAssessment } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';

interface ThreatPanelProps {
  threats: ThreatAssessment[];
  isLoading?: boolean;
  error?: string | null;
  onRefresh?: () => void;
}

export const ThreatPanel: React.FC<ThreatPanelProps> = ({
  threats,
  isLoading = false,
  error,
  onRefresh,
}) => {
  return (
    <Card
      title="Threat Assessment Triage"
      badge={
        <span className="font-mono text-xs text-muted">
          EVALUATED: {threats.length}
        </span>
      }
      actions={
        onRefresh && (
          <Button variant="ghost" size="sm" onClick={onRefresh} isLoading={isLoading}>
            Refresh
          </Button>
        )
      }
      style={{ height: '100%' }}
      bodyStyle={{ padding: 0 }}
    >
      {isLoading && threats.length === 0 ? (
        <LoadingState message="Loading threat assessments..." />
      ) : error ? (
        <div style={{ padding: 'var(--space-md)' }}>
          <ErrorState message={error} onRetry={onRefresh} />
        </div>
      ) : threats.length === 0 ? (
        <EmptyState title="No Active Threats" description="Zero elevated threat postures assessed among active operational tracks." />
      ) : (
        <div className="tactical-table-wrapper" style={{ maxHeight: '280px' }}>
          <table className="tactical-table">
            <thead>
              <tr>
                <th>Level</th>
                <th>Track ID</th>
                <th>Operational Priority Score</th>
                <th>Key Evaluation Factors</th>
                <th>Assessed At</th>
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
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <div
                        style={{
                          width: '60px',
                          height: '6px',
                          backgroundColor: 'var(--bg-canvas)',
                          borderRadius: '3px',
                          overflow: 'hidden',
                        }}
                      >
                        <div
                          style={{
                            width: `${Math.min(100, Math.max(0, th.score))}%`,
                            height: '100%',
                            backgroundColor:
                              th.score >= 75
                                ? 'var(--status-critical)'
                                : th.score >= 50
                                ? 'var(--status-warning)'
                                : 'var(--status-info)',
                          }}
                        />
                      </div>
                      <span className="font-mono text-xs" style={{ fontWeight: 600 }}>
                        {th.score.toFixed(1)}
                      </span>
                    </div>
                  </td>
                  <td className="font-mono text-xs text-muted" style={{ maxWidth: '200px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
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
  );
};
