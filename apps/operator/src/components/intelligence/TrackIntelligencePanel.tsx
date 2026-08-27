import React from 'react';
import {
  BehaviorClassification,
  CoordinatedFormation,
  DefensiveIntelligenceSummary,
  ThreatPriorityAssessment,
  TrackGroup,
} from '../../types';
import { BehaviorBadge } from './BehaviorBadge';

interface TrackIntelligencePanelProps {
  trackId: string;
  priority?: ThreatPriorityAssessment | null;
  behavior?: BehaviorClassification | null;
  group?: TrackGroup | null;
  formation?: CoordinatedFormation | null;
  intelligence?: DefensiveIntelligenceSummary | null;
  onSelectGroup?: (groupId: string) => void;
}

const PRIORITY_LEVEL_COLORS: Record<string, { bg: string; border: string; text: string; label: string }> = {
  LOW: { bg: 'rgba(34, 197, 94, 0.12)', border: 'rgba(34, 197, 94, 0.4)', text: '#4ade80', label: 'LOW' },
  MEDIUM: { bg: 'rgba(234, 179, 8, 0.15)', border: 'rgba(234, 179, 8, 0.4)', text: '#facc15', label: 'MEDIUM' },
  HIGH: { bg: 'rgba(251, 146, 60, 0.18)', border: 'rgba(251, 146, 60, 0.45)', text: '#fb923c', label: 'HIGH' },
  CRITICAL: { bg: 'rgba(239, 68, 68, 0.22)', border: 'rgba(239, 68, 68, 0.5)', text: '#f87171', label: 'CRITICAL' },
};

export const TrackIntelligencePanel: React.FC<TrackIntelligencePanelProps> = ({
  trackId,
  priority,
  behavior,
  group,
  formation,
  intelligence,
  onSelectGroup,
}) => {
  const prioLevel = priority?.priority_level || 'LOW';
  const levelStyle = PRIORITY_LEVEL_COLORS[prioLevel] || PRIORITY_LEVEL_COLORS.LOW;

  return (
    <div
      role="region"
      aria-label={`Defensive Intelligence for Track ${trackId}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md, 12px)',
        padding: 'var(--space-md, 12px)',
        backgroundColor: 'var(--bg-surface, #1e293b)',
        border: '1px solid var(--border-subtle, #334155)',
        borderRadius: 'var(--radius-md, 6px)',
      }}
    >
      {/* Header: Track ID & Priority Score */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle, #334155)', paddingBottom: '8px' }}>
        <div>
          <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
            Track Intelligence Analysis
          </span>
          <h4 className="font-mono text-sm" style={{ margin: 0, fontWeight: 700, color: 'var(--text-primary, #f8fafc)' }}>
            {trackId}
          </h4>
        </div>
        {priority && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                padding: '2px 8px',
                borderRadius: '4px',
                fontSize: '11px',
                fontWeight: 700,
                backgroundColor: levelStyle.bg,
                border: `1px solid ${levelStyle.border}`,
                color: levelStyle.text,
                fontFamily: 'var(--font-mono, monospace)',
              }}
            >
              {levelStyle.label} ({priority.priority_score.toFixed(1)})
            </span>
          </div>
        )}
      </div>

      {/* Behavioral State & Group Correlation */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px', fontSize: '11px' }}>
        <div>
          <span className="text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>Behavioral State</span>
          {behavior ? (
            <BehaviorBadge state={behavior.state} confidence={behavior.confidence} />
          ) : (
            <span className="font-mono text-muted">NORMAL (Default)</span>
          )}
          {behavior?.duration_seconds != null && behavior.duration_seconds > 0 && (
            <span className="font-mono text-muted" style={{ display: 'block', fontSize: '9.5px', marginTop: '2px' }}>
              Duration: {behavior.duration_seconds.toFixed(0)}s
            </span>
          )}
        </div>

        <div>
          <span className="text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>Group Affiliation</span>
          {group ? (
            <button
              type="button"
              onClick={() => onSelectGroup?.(group.group_id)}
              className="btn btn-subtle btn-xs font-mono"
              style={{ padding: '2px 6px', color: '#c084fc', border: '1px solid rgba(192, 132, 252, 0.4)' }}
            >
              {group.group_id} ({group.member_count} tracks)
            </button>
          ) : (
            <span className="font-mono text-muted">Isolated / Ungrouped</span>
          )}
        </div>
      </div>

      {/* Coordinated Formation Telemetry (if available) */}
      {formation && (
        <div
          style={{
            padding: '8px',
            backgroundColor: 'rgba(56, 189, 248, 0.08)',
            border: '1px solid rgba(56, 189, 248, 0.25)',
            borderRadius: 'var(--radius-sm, 4px)',
            fontSize: '11px',
          }}
        >
          <div className="uppercase-tracking" style={{ fontSize: '9px', color: '#38bdf8', fontWeight: 700, marginBottom: '4px' }}>
            ⬡ Coordinated Formation Telemetry
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '4px' }}>
            <div>
              <span className="text-muted" style={{ fontSize: '9px' }}>Sync Index</span>
              <div className="font-mono" style={{ fontWeight: 600, color: '#38bdf8' }}>
                {(formation.synchronization_index * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <span className="text-muted" style={{ fontSize: '9px' }}>Heading Disp.</span>
              <div className="font-mono" style={{ fontWeight: 600 }}>
                {formation.heading_dispersion_deg.toFixed(1)}°
              </div>
            </div>
            <div>
              <span className="text-muted" style={{ fontSize: '9px' }}>Velocity Disp.</span>
              <div className="font-mono" style={{ fontWeight: 600 }}>
                {formation.velocity_dispersion_mps.toFixed(1)} m/s
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Explainable Defensive Priority Factors */}
      {priority && priority.factors && priority.factors.length > 0 && (
        <div>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '9.5px', fontWeight: 700, marginBottom: '6px' }}>
            Explainable Priority Factors (Reconciled)
          </div>
          <table
            style={{
              width: '100%',
              fontSize: '11px',
              fontFamily: 'var(--font-mono, monospace)',
              borderCollapse: 'collapse',
            }}
          >
            <thead>
              <tr style={{ color: 'var(--text-muted, #94a3b8)', borderBottom: '1px solid var(--border-subtle, #334155)', textAlign: 'left' }}>
                <th style={{ padding: '3px 4px', fontWeight: 600 }}>Factor</th>
                <th style={{ padding: '3px 4px', fontWeight: 600, textAlign: 'right' }}>Score</th>
                <th style={{ padding: '3px 4px', fontWeight: 600, textAlign: 'right' }}>Weight</th>
                <th style={{ padding: '3px 4px', fontWeight: 600, textAlign: 'right' }}>Contrib</th>
              </tr>
            </thead>
            <tbody>
              {priority.factors.map((f) => (
                <tr
                  key={f.name}
                  style={{
                    borderBottom: '1px solid rgba(51, 65, 85, 0.4)',
                    color: f.contribution > 10 ? 'var(--text-primary, #f8fafc)' : 'var(--text-secondary, #cbd5e1)',
                  }}
                  title={f.description}
                >
                  <td style={{ padding: '4px', textTransform: 'capitalize' }}>{f.name}</td>
                  <td style={{ padding: '4px', textAlign: 'right' }}>{f.score.toFixed(0)}</td>
                  <td style={{ padding: '4px', textAlign: 'right', color: 'var(--text-muted, #94a3b8)' }}>×{f.weight.toFixed(2)}</td>
                  <td style={{ padding: '4px', textAlign: 'right', fontWeight: 600, color: f.contribution >= 15 ? '#fb923c' : 'inherit' }}>
                    → {f.contribution.toFixed(1)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          {priority.reason && (
            <p className="font-mono text-xs text-muted" style={{ marginTop: '6px', marginBottom: 0, fontStyle: 'italic', lineHeight: 1.3 }}>
              {priority.reason}
            </p>
          )}
        </div>
      )}

      {/* Kinematic Features and Ingress summary */}
      {intelligence?.features && (
        <div style={{ padding: '6px', backgroundColor: 'var(--bg-canvas, #0f172a)', borderRadius: 'var(--radius-sm, 4px)', border: '1px solid var(--border-subtle, #334155)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '9px', marginBottom: '4px' }}>
            Kinematic Telemetry
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '2px', fontSize: '10.5px' }}>
            <div className="font-mono text-muted">Speed: <span style={{ color: 'var(--text-primary, #f8fafc)' }}>{intelligence.features.speed_mps.toFixed(1)} m/s</span></div>
            <div className="font-mono text-muted">Turn: <span style={{ color: 'var(--text-primary, #f8fafc)' }}>{intelligence.features.turn_rate_dps.toFixed(1)}°/s</span></div>
            <div className="font-mono text-muted">Accel: <span style={{ color: 'var(--text-primary, #f8fafc)' }}>{intelligence.features.acceleration_mps2.toFixed(1)} m/s²</span></div>
            <div className="font-mono text-muted">Confidence: <span style={{ color: 'var(--text-primary, #f8fafc)' }}>{(intelligence.anomaly.sensor_confidence * 100).toFixed(0)}%</span></div>
          </div>
        </div>
      )}
    </div>
  );
};
