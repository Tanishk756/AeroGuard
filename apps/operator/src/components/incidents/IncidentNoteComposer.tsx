/**
 * AeroGuard Incident Note Composer Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useState } from 'react';

export interface IncidentNoteComposerProps {
  onSubmitNote: (message: string) => Promise<void>;
  isSubmitting?: boolean;
  canManage?: boolean;
}

export const IncidentNoteComposer: React.FC<IncidentNoteComposerProps> = ({
  onSubmitNote,
  isSubmitting = false,
  canManage = false,
}) => {
  const [message, setMessage] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!canManage) {
    return (
      <div className="font-mono text-xs text-muted" style={{ padding: '12px 20px', fontStyle: 'italic' }}>
        You do not have permission to add observation notes to this incident (requires incidents.manage).
      </div>
    );
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    const clean = message.trim();
    if (!clean) {
      setError('Note message cannot be blank');
      return;
    }
    if (clean.length > 2000) {
      setError('Note message exceeds 2000 characters');
      return;
    }

    setError(null);
    try {
      await onSubmitNote(clean);
      setMessage('');
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to save note');
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
        gap: '8px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <label
          htmlFor="incident-note-input"
          style={{
            fontSize: '12px',
            fontWeight: 700,
            textTransform: 'uppercase',
            letterSpacing: '0.04em',
            color: 'var(--text-secondary, #94a3b8)',
          }}
        >
          Add Operator Observation Note
        </label>
        <span className="font-mono text-xs text-muted">{message.length} / 2000</span>
      </div>

      <textarea
        id="incident-note-input"
        className="tactical-input font-mono text-xs"
        style={{
          minHeight: '64px',
          resize: 'vertical',
          padding: '8px',
        }}
        placeholder="Enter timestamped observation, findings, or operator notes..."
        value={message}
        onChange={(e) => {
          setMessage(e.target.value);
          if (error) setError(null);
        }}
        disabled={isSubmitting}
        maxLength={2000}
      />

      {error && (
        <div role="alert" className="font-mono text-xs" style={{ color: 'var(--status-critical, #ef4444)' }}>
          {error}
        </div>
      )}

      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
        <button
          type="button"
          className="btn btn-secondary btn-sm font-mono"
          onClick={() => {
            setMessage('');
            setError(null);
          }}
          disabled={!message || isSubmitting}
        >
          Clear
        </button>
        <button
          type="submit"
          className="btn btn-primary btn-sm font-mono"
          disabled={!message.trim() || isSubmitting}
        >
          {isSubmitting ? 'Saving...' : 'Post Note'}
        </button>
      </div>
    </form>
  );
};
