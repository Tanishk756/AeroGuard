import React, { useMemo, useState } from 'react';
import {
  BehaviorClassification,
  ThreatPriorityAssessment,
} from '../../types';
import { BehaviorBadge } from './BehaviorBadge';

interface PriorityListProps {
  priorities: ThreatPriorityAssessment[];
  behaviors?: BehaviorClassification[];
  selectedTrackId?: string | null;
  onSelectTrack?: (trackId: string) => void;
}

const PRIORITY_LEVEL_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  LOW: { bg: 'rgba(34, 197, 94, 0.12)', border: 'rgba(34, 197, 94, 0.35)', text: '#4ade80' },
  MEDIUM: { bg: 'rgba(234, 179, 8, 0.15)', border: 'rgba(234, 179, 8, 0.4)', text: '#facc15' },
  HIGH: { bg: 'rgba(251, 146, 60, 0.18)', border: 'rgba(251, 146, 60, 0.45)', text: '#fb923c' },
  CRITICAL: { bg: 'rgba(239, 68, 68, 0.22)', border: 'rgba(239, 68, 68, 0.5)', text: '#f87171' },
};

const PRIORITY_ORDER: Record<string, number> = {
  CRITICAL: 3,
  HIGH: 2,
  MEDIUM: 1,
  LOW: 0,
};

export const PriorityList: React.FC<PriorityListProps> = ({
  priorities,
  behaviors = [],
  selectedTrackId,
  onSelectTrack,
}) => {
  const [filterLevel, setFilterLevel] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');

  const behaviorMap = useMemo(() => {
    const map = new Map<string, BehaviorClassification>();
    for (const b of behaviors) {
      map.set(b.track_id, b);
    }
    return map;
  }, [behaviors]);

  const filteredSortedPriorities = useMemo(() => {
    return priorities
      .filter((p) => {
        if (filterLevel !== 'ALL') {
          const reqRank = PRIORITY_ORDER[filterLevel] ?? 0;
          const currRank = PRIORITY_ORDER[p.priority_level] ?? 0;
          if (currRank < reqRank) return false;
        }
        if (searchQuery.trim()) {
          const q = searchQuery.toLowerCase();
          const matchId = p.track_id.toLowerCase().includes(q);
          const matchGroup = p.group_id?.toLowerCase().includes(q) ?? false;
          const matchReason = p.reason?.toLowerCase().includes(q) ?? false;
          if (!matchId && !matchGroup && !matchReason) return false;
        }
        return true;
      })
      .sort((a, b) => b.priority_score - a.priority_score);
  }, [priorities, filterLevel, searchQuery]);

  return (
    <div
      role="region"
      aria-label="Defensive Threat Priority Rankings"
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '8px',
        width: '100%',
      }}
    >
      {/* Search & Filter Header */}
      <div style={{ display: 'flex', gap: '8px', alignItems: 'center' }}>
        <input
          type="search"
          placeholder="Filter by track or group ID..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          aria-label="Filter priority list"
          className="input-search font-mono text-xs"
          style={{
            flex: 1,
            padding: '4px 8px',
            backgroundColor: 'var(--bg-canvas, #0f172a)',
            border: '1px solid var(--border-subtle, #334155)',
            borderRadius: 'var(--radius-sm, 4px)',
            color: 'var(--text-primary, #f8fafc)',
          }}
        />
        <select
          value={filterLevel}
          onChange={(e) => setFilterLevel(e.target.value)}
          aria-label="Filter by minimum priority level"
          className="font-mono text-xs"
          style={{
            padding: '4px 8px',
            backgroundColor: 'var(--bg-canvas, #0f172a)',
            border: '1px solid var(--border-subtle, #334155)',
            borderRadius: 'var(--radius-sm, 4px)',
            color: 'var(--text-primary, #f8fafc)',
          }}
        >
          <option value="ALL">All Levels</option>
          <option value="LOW">≥ LOW</option>
          <option value="MEDIUM">≥ MEDIUM</option>
          <option value="HIGH">≥ HIGH</option>
          <option value="CRITICAL">≥ CRITICAL</option>
        </select>
      </div>

      {/* Priority Items List */}
      <div
        style={{
          display: 'flex',
          flexDirection: 'column',
          gap: '4px',
          maxHeight: '400px',
          overflowY: 'auto',
        }}
      >
        {filteredSortedPriorities.length === 0 ? (
          <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted, #94a3b8)', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
            No priority assessments matching criteria.
          </div>
        ) : (
          filteredSortedPriorities.map((p) => {
            const isSelected = p.track_id === selectedTrackId;
            const style = PRIORITY_LEVEL_COLORS[p.priority_level] || PRIORITY_LEVEL_COLORS.LOW;
            const b = behaviorMap.get(p.track_id);

            return (
              <div
                key={p.track_id}
                onClick={() => onSelectTrack?.(p.track_id)}
                role="button"
                tabIndex={0}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelectTrack?.(p.track_id);
                  }
                }}
                aria-label={`Track ${p.track_id}, Priority ${p.priority_score.toFixed(1)} ${p.priority_level}`}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '8px 10px',
                  backgroundColor: isSelected ? 'rgba(56, 189, 248, 0.12)' : 'var(--bg-surface, #1e293b)',
                  border: isSelected ? '1px solid #38bdf8' : '1px solid var(--border-subtle, #334155)',
                  borderRadius: 'var(--radius-sm, 4px)',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease',
                }}
              >
                <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span className="font-mono text-xs" style={{ fontWeight: 700, color: isSelected ? '#38bdf8' : 'var(--text-primary, #f8fafc)' }}>
                      {p.track_id}
                    </span>
                    {p.group_id && (
                      <span
                        className="font-mono text-xs"
                        style={{
                          fontSize: '9.5px',
                          color: '#c084fc',
                          backgroundColor: 'rgba(192, 132, 252, 0.1)',
                          padding: '1px 4px',
                          borderRadius: '2px',
                        }}
                      >
                        {p.group_id}
                      </span>
                    )}
                  </div>
                  {b && (
                    <div style={{ marginTop: '2px' }}>
                      <BehaviorBadge state={b.state} confidence={b.confidence} />
                    </div>
                  )}
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <div className="font-mono text-sm" style={{ fontWeight: 700, color: style.text }}>
                      {p.priority_score.toFixed(1)}
                    </div>
                    <span
                      style={{
                        display: 'inline-block',
                        fontSize: '9px',
                        fontWeight: 700,
                        padding: '1px 4px',
                        borderRadius: '2px',
                        backgroundColor: style.bg,
                        border: `1px solid ${style.border}`,
                        color: style.text,
                        fontFamily: 'var(--font-mono, monospace)',
                      }}
                    >
                      {p.priority_level}
                    </span>
                  </div>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
