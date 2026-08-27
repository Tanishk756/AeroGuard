import React from 'react';
import { MultiTrackIntelligenceSummary } from '../../types';

interface IntelligenceSummaryProps {
  summary: MultiTrackIntelligenceSummary | null;
  isLoading?: boolean;
}

export const IntelligenceSummary: React.FC<IntelligenceSummaryProps> = ({
  summary,
  isLoading = false,
}) => {
  if (isLoading && !summary) {
    return (
      <div
        className="card-tactical"
        style={{ padding: 'var(--space-md, 12px)', display: 'flex', gap: 'var(--space-md, 12px)' }}
      >
        <span className="text-muted font-mono text-xs">Loading defensive intelligence metrics...</span>
      </div>
    );
  }

  const groupsCount = summary?.groups?.length ?? 0;
  const formationsCount = summary?.formations?.length ?? 0;
  const behaviorsCount = summary?.behaviors?.length ?? 0;
  const priorities = summary?.priorities ?? [];
  const prioritiesCount = priorities.length;

  let highestPriority = 0;
  let elevatedCount = 0; // HIGH or CRITICAL (score >= 60)

  for (const p of priorities) {
    if (p.priority_score > highestPriority) {
      highestPriority = p.priority_score;
    }
    if (p.priority_level === 'HIGH' || p.priority_level === 'CRITICAL' || p.priority_score >= 60) {
      elevatedCount++;
    }
  }

  const evalDate = summary?.evaluated_at ? new Date(summary.evaluated_at) : null;
  const timeStr = evalDate ? evalDate.toLocaleTimeString() : 'N/A';

  return (
    <div
      role="region"
      aria-label="Defensive Intelligence Situational Awareness Summary"
      style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))',
        gap: 'var(--space-sm, 8px)',
        width: '100%',
      }}
    >
      {/* 1. Active Groups */}
      <div
        style={{
          padding: '10px 12px',
          backgroundColor: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border-subtle, #334155)',
          borderRadius: 'var(--radius-md, 6px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
        }}
      >
        <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
          Active Groups
        </span>
        <span className="font-mono text-lg" style={{ fontWeight: 700, color: groupsCount > 0 ? '#c084fc' : 'var(--text-primary, #f8fafc)' }}>
          {groupsCount}
        </span>
      </div>

      {/* 2. Coordinated Formations */}
      <div
        style={{
          padding: '10px 12px',
          backgroundColor: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border-subtle, #334155)',
          borderRadius: 'var(--radius-md, 6px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
        }}
      >
        <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
          Formations
        </span>
        <span className="font-mono text-lg" style={{ fontWeight: 700, color: formationsCount > 0 ? '#38bdf8' : 'var(--text-primary, #f8fafc)' }}>
          {formationsCount}
        </span>
      </div>

      {/* 3. Highest Priority Score */}
      <div
        style={{
          padding: '10px 12px',
          backgroundColor: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border-subtle, #334155)',
          borderRadius: 'var(--radius-md, 6px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
        }}
      >
        <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
          Max Priority
        </span>
        <span
          className="font-mono text-lg"
          style={{
            fontWeight: 700,
            color:
              highestPriority >= 80
                ? '#ef4444'
                : highestPriority >= 60
                ? '#fb923c'
                : highestPriority >= 30
                ? '#facc15'
                : '#4ade80',
          }}
        >
          {highestPriority.toFixed(1)}
        </span>
      </div>

      {/* 4. Elevated Attention Tracks */}
      <div
        style={{
          padding: '10px 12px',
          backgroundColor: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border-subtle, #334155)',
          borderRadius: 'var(--radius-md, 6px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
        }}
      >
        <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
          High / Critical
        </span>
        <span
          className="font-mono text-lg"
          style={{
            fontWeight: 700,
            color: elevatedCount > 0 ? '#ef4444' : 'var(--text-muted, #94a3b8)',
          }}
        >
          {elevatedCount}
        </span>
      </div>

      {/* 5. Total Assessed Tracks */}
      <div
        style={{
          padding: '10px 12px',
          backgroundColor: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border-subtle, #334155)',
          borderRadius: 'var(--radius-md, 6px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
        }}
      >
        <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
          Assessed Tracks
        </span>
        <span className="font-mono text-lg" style={{ fontWeight: 700, color: 'var(--text-primary, #f8fafc)' }}>
          {prioritiesCount}
        </span>
      </div>

      {/* 6. Evaluation Timestamp */}
      <div
        style={{
          padding: '10px 12px',
          backgroundColor: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border-subtle, #334155)',
          borderRadius: 'var(--radius-md, 6px)',
          display: 'flex',
          flexDirection: 'column',
          gap: '2px',
        }}
      >
        <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
          Evaluated
        </span>
        <span className="font-mono text-sm" style={{ fontWeight: 600, color: 'var(--text-secondary, #cbd5e1)', marginTop: '2px' }}>
          {timeStr}
        </span>
      </div>
    </div>
  );
};
