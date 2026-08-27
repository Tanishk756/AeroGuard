import React from 'react';
import { BehavioralState } from '../../types';

interface BehaviorBadgeProps {
  state: BehavioralState | string;
  confidence?: number;
  showIcon?: boolean;
}

const BEHAVIOR_CONFIG: Record<string, { label: string; icon: string; bg: string; border: string; text: string }> = {
  NORMAL: {
    label: 'NORMAL',
    icon: '●',
    bg: 'rgba(34, 197, 94, 0.12)',
    border: 'rgba(34, 197, 94, 0.35)',
    text: '#4ade80',
  },
  APPROACHING: {
    label: 'APPROACHING',
    icon: '↘',
    bg: 'rgba(234, 179, 8, 0.15)',
    border: 'rgba(234, 179, 8, 0.4)',
    text: '#facc15',
  },
  DEPARTING: {
    label: 'DEPARTING',
    icon: '↗',
    bg: 'rgba(56, 189, 248, 0.12)',
    border: 'rgba(56, 189, 248, 0.35)',
    text: '#38bdf8',
  },
  LOITERING: {
    label: 'LOITERING',
    icon: '⟳',
    bg: 'rgba(251, 146, 60, 0.15)',
    border: 'rgba(251, 146, 60, 0.4)',
    text: '#fb923c',
  },
  RAPID_CHANGE: {
    label: 'RAPID CHANGE',
    icon: '⚡',
    bg: 'rgba(244, 63, 94, 0.15)',
    border: 'rgba(244, 63, 94, 0.4)',
    text: '#fb7185',
  },
  COORDINATED: {
    label: 'COORDINATED',
    icon: '⬡',
    bg: 'rgba(168, 85, 247, 0.15)',
    border: 'rgba(168, 85, 247, 0.4)',
    text: '#c084fc',
  },
  ANOMALOUS: {
    label: 'ANOMALOUS',
    icon: '⚠',
    bg: 'rgba(239, 68, 68, 0.18)',
    border: 'rgba(239, 68, 68, 0.45)',
    text: '#f87171',
  },
};

export const BehaviorBadge: React.FC<BehaviorBadgeProps> = ({
  state,
  confidence,
  showIcon = true,
}) => {
  const normState = String(state || 'NORMAL').toUpperCase();
  const config = BEHAVIOR_CONFIG[normState] || BEHAVIOR_CONFIG.NORMAL;

  return (
    <span
      role="status"
      aria-label={`Behavioral state: ${config.label}${confidence != null ? ` (${(confidence * 100).toFixed(0)}% confidence)` : ''}`}
      style={{
        display: 'inline-flex',
        alignItems: 'center',
        gap: '4px',
        padding: '2px 6px',
        borderRadius: 'var(--radius-sm, 4px)',
        fontSize: '10.5px',
        fontWeight: 600,
        fontFamily: 'var(--font-mono, monospace)',
        backgroundColor: config.bg,
        border: `1px solid ${config.border}`,
        color: config.text,
        letterSpacing: '0.04em',
        lineHeight: 1.2,
      }}
    >
      {showIcon && <span aria-hidden="true">{config.icon}</span>}
      <span>{config.label}</span>
      {confidence != null && (
        <span style={{ opacity: 0.75, fontSize: '9.5px' }}>
          {(confidence * 100).toFixed(0)}%
        </span>
      )}
    </span>
  );
};
