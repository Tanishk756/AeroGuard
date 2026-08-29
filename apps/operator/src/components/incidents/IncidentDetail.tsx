/**
 * AeroGuard Incident Detail Workspace Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import {
  AcknowledgeIncidentRequest,
  AddIncidentNoteRequest,
  AssignIncidentRequest,
  CloseIncidentRequest,
  DeEscalateIncidentRequest,
  DefensiveActionCategory,
  EscalateIncidentRequest,
  Incident,
  IncidentEvent,
  LogDefensiveActionRequest,
  ResolveIncidentRequest,
  TriageIncidentRequest,
} from '../../types';
import { IncidentActionComposer } from './IncidentActionComposer';
import { IncidentActions } from './IncidentActions';
import { IncidentHeader } from './IncidentHeader';
import { IncidentNoteComposer } from './IncidentNoteComposer';
import { IncidentTimeline } from './IncidentTimeline';

export interface IncidentDetailProps {
  incident: Incident | null;
  timeline: IncidentEvent[];
  isLoading?: boolean;
  isTimelineLoading?: boolean;
  isMutating?: boolean;
  onAcknowledge: (id: string, data?: AcknowledgeIncidentRequest) => Promise<Incident>;
  onAssign: (id: string, data: AssignIncidentRequest) => Promise<Incident>;
  onTriage: (id: string, data: TriageIncidentRequest) => Promise<Incident>;
  onEscalate: (id: string, data: EscalateIncidentRequest) => Promise<Incident>;
  onDeEscalate: (id: string, data: DeEscalateIncidentRequest) => Promise<Incident>;
  onResolve: (id: string, data: ResolveIncidentRequest) => Promise<Incident>;
  onClose: (id: string, data?: CloseIncidentRequest) => Promise<Incident>;
  onAddNote: (id: string, data: AddIncidentNoteRequest) => Promise<IncidentEvent>;
  onLogAction: (id: string, data: LogDefensiveActionRequest) => Promise<IncidentEvent>;
}

export const IncidentDetail: React.FC<IncidentDetailProps> = ({
  incident,
  timeline,
  isLoading = false,
  isTimelineLoading = false,
  isMutating = false,
  onAcknowledge,
  onAssign,
  onTriage,
  onEscalate,
  onDeEscalate,
  onResolve,
  onClose,
  onAddNote,
  onLogAction,
}) => {
  const navigate = useNavigate();
  const { hasPermission } = useAuth();
  const canManage = hasPermission('incidents.manage');

  const [activeTab, setActiveTab] = useState<'timeline' | 'notes' | 'actions'>('timeline');

  if (isLoading && !incident) {
    return (
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--bg-surface-elevated, #161f2e)',
        }}
        className="font-mono text-xs text-muted"
      >
        Loading incident details...
      </div>
    );
  }

  if (!incident) {
    return (
      <div
        style={{
          flex: 1,
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          gap: '8px',
          backgroundColor: 'var(--bg-surface-elevated, #161f2e)',
          padding: '24px',
          textAlign: 'center',
        }}
        className="font-mono text-xs text-muted"
      >
        <span style={{ fontSize: '24px' }}>📋</span>
        <span style={{ fontWeight: 600, color: 'var(--text-secondary, #94a3b8)' }}>No Incident Selected</span>
        <span>Select an incident from the registry to inspect its chronological timeline and operational state.</span>
      </div>
    );
  }

  return (
    <div
      style={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-surface-elevated, #161f2e)',
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      {/* Header */}
      <IncidentHeader incident={incident} />

      {/* Lifecycle Actions Bar */}
      <IncidentActions
        incident={incident}
        isMutating={isMutating}
        onAcknowledge={onAcknowledge}
        onAssign={onAssign}
        onTriage={onTriage}
        onEscalate={onEscalate}
        onDeEscalate={onDeEscalate}
        onResolve={onResolve}
        onClose={onClose}
      />

      {/* Correlation Strip */}
      <div
        style={{
          padding: '10px 20px',
          backgroundColor: 'rgba(0, 0, 0, 0.2)',
          borderBottom: '1px solid var(--border-medium, #334155)',
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '16px',
        }}
      >
        <span className="font-mono text-xs text-muted" style={{ fontWeight: 700 }}>
          CORRELATIONS:
        </span>

        {incident.primary_track_id ? (
          <button
            type="button"
            className="font-mono text-xs"
            onClick={() => navigate(`/app/tracks?track_id=${encodeURIComponent(incident.primary_track_id!)}`)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor: 'rgba(59, 130, 246, 0.15)',
              color: '#60a5fa',
              border: '1px solid rgba(59, 130, 246, 0.3)',
              borderRadius: '3px',
              padding: '2px 6px',
              cursor: 'pointer',
            }}
          >
            ◎ Track: {incident.primary_track_id}
          </button>
        ) : (
          <span className="font-mono text-xs text-muted">Track: NONE</span>
        )}

        {incident.primary_group_id ? (
          <button
            type="button"
            className="font-mono text-xs"
            onClick={() => navigate('/app/intelligence')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor: 'rgba(168, 85, 247, 0.15)',
              color: '#c084fc',
              border: '1px solid rgba(168, 85, 247, 0.3)',
              borderRadius: '3px',
              padding: '2px 6px',
              cursor: 'pointer',
            }}
          >
            🧠 Group: {incident.primary_group_id}
          </button>
        ) : (
          <span className="font-mono text-xs text-muted">Group: NONE</span>
        )}

        {incident.originating_alert_id ? (
          <button
            type="button"
            className="font-mono text-xs"
            onClick={() => navigate('/app/alerts')}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor: 'rgba(234, 179, 8, 0.15)',
              color: '#facc15',
              border: '1px solid rgba(234, 179, 8, 0.3)',
              borderRadius: '3px',
              padding: '2px 6px',
              cursor: 'pointer',
            }}
          >
            ▲ Alert: {incident.originating_alert_id}
          </button>
        ) : (
          <span className="font-mono text-xs text-muted">Alert: NONE</span>
        )}

        {incident.originating_intelligence_event_id && (
          <span
            className="font-mono text-xs"
            style={{
              color: '#cbd5e1',
              backgroundColor: 'rgba(255, 255, 255, 0.05)',
              padding: '2px 6px',
              borderRadius: '3px',
            }}
          >
            Intel Snapshot: {incident.originating_intelligence_event_id}
          </span>
        )}

        {(incident.primary_track_id || incident.primary_group_id) && (
          <button
            type="button"
            className="font-mono text-xs"
            onClick={() => {
              if (incident.primary_track_id) {
                navigate(`/app/overview?entity=track&id=${encodeURIComponent(incident.primary_track_id)}&incident_id=${encodeURIComponent(incident.id)}`);
              } else {
                navigate(`/app/overview?incident_id=${encodeURIComponent(incident.id)}`);
              }
            }}
            style={{
              marginLeft: 'auto',
              display: 'inline-flex',
              alignItems: 'center',
              gap: '4px',
              backgroundColor: 'rgba(14, 165, 233, 0.15)',
              color: '#38bdf8',
              border: '1px solid rgba(14, 165, 233, 0.3)',
              borderRadius: '3px',
              padding: '2px 8px',
              cursor: 'pointer',
              fontWeight: 600,
            }}
          >
            🗺 Show on Map
          </button>
        )}
      </div>

      {/* Tabs / Sub-views */}
      <div
        style={{
          display: 'flex',
          borderBottom: '1px solid var(--border-medium, #334155)',
          backgroundColor: 'var(--bg-surface, #1e293b)',
        }}
        role="tablist"
      >
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'timeline'}
          onClick={() => setActiveTab('timeline')}
          className="font-mono text-xs"
          style={{
            padding: '10px 16px',
            border: 'none',
            background: 'transparent',
            color: activeTab === 'timeline' ? 'var(--accent-primary, #3b82f6)' : 'var(--text-muted, #94a3b8)',
            borderBottom: activeTab === 'timeline' ? '2px solid var(--accent-primary, #3b82f6)' : '2px solid transparent',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          Timeline & Events ({timeline.length})
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'notes'}
          onClick={() => setActiveTab('notes')}
          className="font-mono text-xs"
          style={{
            padding: '10px 16px',
            border: 'none',
            background: 'transparent',
            color: activeTab === 'notes' ? 'var(--accent-primary, #3b82f6)' : 'var(--text-muted, #94a3b8)',
            borderBottom: activeTab === 'notes' ? '2px solid var(--accent-primary, #3b82f6)' : '2px solid transparent',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          + Add Note
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={activeTab === 'actions'}
          onClick={() => setActiveTab('actions')}
          className="font-mono text-xs"
          style={{
            padding: '10px 16px',
            border: 'none',
            background: 'transparent',
            color: activeTab === 'actions' ? 'var(--accent-primary, #3b82f6)' : 'var(--text-muted, #94a3b8)',
            borderBottom: activeTab === 'actions' ? '2px solid var(--accent-primary, #3b82f6)' : '2px solid transparent',
            fontWeight: 700,
            cursor: 'pointer',
          }}
        >
          + Log Defensive Action
        </button>
      </div>

      {/* Scrollable Content Pane */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {activeTab === 'timeline' && (
          <IncidentTimeline events={timeline} isLoading={isTimelineLoading} />
        )}
        {activeTab === 'notes' && (
          <IncidentNoteComposer
            onSubmitNote={async (msg) => {
              await onAddNote(incident.id, { message: msg });
              setActiveTab('timeline');
            }}
            isSubmitting={isMutating}
            canManage={canManage}
          />
        )}
        {activeTab === 'actions' && (
          <IncidentActionComposer
            onLogAction={async (cat: DefensiveActionCategory, msg?: string) => {
              await onLogAction(incident.id, { category: cat, message: msg });
              setActiveTab('timeline');
            }}
            isSubmitting={isMutating}
            canManage={canManage}
          />
        )}
      </div>
    </div>
  );
};
