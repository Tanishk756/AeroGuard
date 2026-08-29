/**
 * AeroGuard Incident Defensive Action Composer Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useState } from 'react';
import { DefensiveActionCategory } from '../../types';

export interface IncidentActionComposerProps {
  onLogAction: (category: DefensiveActionCategory, message?: string) => Promise<void>;
  isSubmitting?: boolean;
  canManage?: boolean;
}

const ACTION_CATEGORIES: { value: DefensiveActionCategory; label: string; desc: string }[] = [
  { value: 'SENSOR_REVIEW', label: 'Sensor Review', desc: 'Inspect raw radar, RF, or optical sensor telemetry' },
  { value: 'TRACK_CORRELATION_REVIEW', label: 'Track Correlation Review', desc: 'Validate kinematic fusion and track association' },
  { value: 'OPERATOR_CONTACT', label: 'Operator Contact', desc: 'Coordinate with sector or airspace operator' },
  { value: 'SUPERVISOR_ESCALATION', label: 'Supervisor Escalation', desc: 'Brief operational supervisor on incident status' },
  { value: 'PROCEDURE_REVIEW', label: 'Procedure Review', desc: 'Review defensive SOP and perimeter compliance' },
  { value: 'SCENARIO_REVIEW', label: 'Scenario Review', desc: 'Cross-reference simulation scenario rehearsal logs' },
  { value: 'OTHER', label: 'Other Defensive Action', desc: 'General procedural situational-awareness action' },
];

export const IncidentActionComposer: React.FC<IncidentActionComposerProps> = ({
  onLogAction,
  isSubmitting = false,
  canManage = false,
}) => {
  const [category, setCategory] = useState<DefensiveActionCategory>('SENSOR_REVIEW');
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!canManage) {
    return (
      <div className="font-mono text-xs text-muted" style={{ padding: '12px 20px', fontStyle: 'italic' }}>
        You do not have permission to log defensive actions (requires incidents.manage).
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      await onLogAction(category, message.trim() || undefined);
      setMessage('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to log defensive action');
    }
  };

  return (
    <form
      onSubmit={handleSubmit}
      style={{
        padding: '16px 20px',
        backgroundColor: 'var(--bg-surface, #1e293b)',
        borderTop: '1px solid var(--border-medium, #334155)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <label
          htmlFor="incident-action-category"
          style={{
            fontSize: '12px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--text-secondary, #94a3b8)',
          }}
        >
          Log Procedural Defensive Action
        </label>
        <span
          className="font-mono text-xs"
          style={{
            color: '#38bdf8',
            backgroundColor: 'rgba(56, 189, 248, 0.1)',
            padding: '2px 6px',
            borderRadius: '3px',
          }}
        >
          Procedural Record Only
        </span>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: '1fr', gap: '8px' }}>
        <select
          id="incident-action-category"
          className="tactical-select font-mono text-xs"
          value={category}
          onChange={(e) => setCategory(e.target.value as DefensiveActionCategory)}
          disabled={isSubmitting}
        >
          {ACTION_CATEGORIES.map((c) => (
            <option key={c.value} value={c.value}>
              {c.label} ({c.desc})
            </option>
          ))}
        </select>

        <input
          type="text"
          className="tactical-input font-mono text-xs"
          placeholder="Details / findings summary (optional)..."
          value={message}
          onChange={(e) => {
            setMessage(e.target.value);
            if (error) setError(null);
          }}
          disabled={isSubmitting}
          maxLength={500}
        />
      </div>

      {error && (
        <div role="alert" className="font-mono text-xs" style={{ color: 'var(--status-critical, #ef4444)' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '2px' }}>
        <span className="font-mono text-xs text-muted" style={{ fontSize: '11px' }}>
          * Records procedural review for audit logs. Contains zero weapon or kinetic effects.
        </span>
        <button
          type="submit"
          className="btn btn-secondary btn-sm font-mono"
          disabled={isSubmitting}
        >
          {isSubmitting ? 'Logging...' : 'Log Defensive Action'}
        </button>
      </div>
    </form>
  );
};
