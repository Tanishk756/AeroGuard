/**
 * AeroGuard Create Incident Modal Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useState } from 'react';
import { CreateIncidentRequest, IncidentSeverity, IncidentSource } from '../../types';

export interface CreateIncidentModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (data: CreateIncidentRequest) => Promise<void>;
  isSubmitting?: boolean;
}

export const CreateIncidentModal: React.FC<CreateIncidentModalProps> = ({
  isOpen,
  onClose,
  onSubmit,
  isSubmitting = false,
}) => {
  const [title, setTitle] = useState('');
  const [description, setDescription] = useState('');
  const [severity, setSeverity] = useState<IncidentSeverity>('MEDIUM');
  const [source, setSource] = useState<IncidentSource>('OPERATOR');
  const [trackId, setTrackId] = useState('');
  const [groupId, setGroupId] = useState('');
  const [alertId, setAlertId] = useState('');
  const [error, setError] = useState<string | null>(null);

  if (!isOpen) return null;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!title.trim()) {
      setError('Incident title is required');
      return;
    }

    setError(null);
    try {
      await onSubmit({
        title: title.trim(),
        description: description.trim() || undefined,
        severity,
        source,
        primary_track_id: trackId.trim() || undefined,
        primary_group_id: groupId.trim() || undefined,
        originating_alert_id: alertId.trim() || undefined,
      });
      onClose();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to create incident');
    }
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="create-incident-modal-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.65)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        zIndex: 1000,
        padding: '16px',
      }}
    >
      <div
        style={{
          backgroundColor: 'var(--bg-surface, #1e293b)',
          border: '1px solid var(--border-medium, #334155)',
          borderRadius: '6px',
          width: '100%',
          maxWidth: '520px',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h3 id="create-incident-modal-title" style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
            Create Operational Incident
          </h3>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onClose} aria-label="Close modal">
            ✕
          </button>
        </div>

        <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label className="font-mono text-xs text-muted" htmlFor="inc-title">
              Title *
            </label>
            <input
              id="inc-title"
              type="text"
              className="tactical-input font-mono text-xs"
              placeholder="e.g. Unauthorized Swarm Incursion near Sector 4"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              required
              autoFocus
            />
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
            <label className="font-mono text-xs text-muted" htmlFor="inc-desc">
              Description (Optional)
            </label>
            <textarea
              id="inc-desc"
              className="tactical-input font-mono text-xs"
              style={{ minHeight: '54px', resize: 'vertical' }}
              placeholder="Additional operational context, observed behaviors, or perimeter alerts..."
              value={description}
              onChange={(e) => setDescription(e.target.value)}
            />
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label className="font-mono text-xs text-muted" htmlFor="inc-sev">
                Severity
              </label>
              <select
                id="inc-sev"
                className="tactical-select font-mono text-xs"
                value={severity}
                onChange={(e) => setSeverity(e.target.value as IncidentSeverity)}
              >
                <option value="LOW">LOW</option>
                <option value="MEDIUM">MEDIUM</option>
                <option value="HIGH">HIGH</option>
                <option value="CRITICAL">CRITICAL</option>
              </select>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label className="font-mono text-xs text-muted" htmlFor="inc-src">
                Source
              </label>
              <select
                id="inc-src"
                className="tactical-select font-mono text-xs"
                value={source}
                onChange={(e) => setSource(e.target.value as IncidentSource)}
              >
                <option value="OPERATOR">OPERATOR</option>
                <option value="ALERT">ALERT</option>
                <option value="AI_ANOMALY">AI_ANOMALY</option>
                <option value="AI_SWARM">AI_SWARM</option>
                <option value="SYSTEM">SYSTEM</option>
                <option value="EXTERNAL">EXTERNAL</option>
              </select>
            </div>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label className="font-mono text-xs text-muted" htmlFor="inc-trk">
                Track ID
              </label>
              <input
                id="inc-trk"
                type="text"
                className="tactical-input font-mono text-xs"
                placeholder="TRK-..."
                value={trackId}
                onChange={(e) => setTrackId(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label className="font-mono text-xs text-muted" htmlFor="inc-grp">
                Group ID
              </label>
              <input
                id="inc-grp"
                type="text"
                className="tactical-input font-mono text-xs"
                placeholder="GRP-..."
                value={groupId}
                onChange={(e) => setGroupId(e.target.value)}
              />
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
              <label className="font-mono text-xs text-muted" htmlFor="inc-alt">
                Alert ID
              </label>
              <input
                id="inc-alt"
                type="text"
                className="tactical-input font-mono text-xs"
                placeholder="ALT-..."
                value={alertId}
                onChange={(e) => setAlertId(e.target.value)}
              />
            </div>
          </div>

          {error && (
            <div role="alert" className="font-mono text-xs" style={{ color: 'var(--status-critical, #ef4444)' }}>
              {error}
            </div>
          )}

          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '6px' }}>
            <button type="button" className="btn btn-secondary btn-sm font-mono" onClick={onClose}>
              Cancel
            </button>
            <button type="submit" className="btn btn-primary btn-sm font-mono" disabled={isSubmitting}>
              {isSubmitting ? 'Creating...' : 'Create Incident'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};
