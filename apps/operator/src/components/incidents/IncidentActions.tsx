/**
 * AeroGuard Incident Action Controls & Modals Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import {
  AcknowledgeIncidentRequest,
  AssignIncidentRequest,
  CloseIncidentRequest,
  DeEscalateIncidentRequest,
  EscalateIncidentRequest,
  Incident,
  IncidentSeverity,
  IncidentStatus,
  ResolveIncidentRequest,
  TriageIncidentRequest,
} from '../../types';

export interface IncidentActionsProps {
  incident: Incident;
  isMutating?: boolean;
  onAcknowledge: (id: string, data?: AcknowledgeIncidentRequest) => Promise<Incident>;
  onAssign: (id: string, data: AssignIncidentRequest) => Promise<Incident>;
  onTriage: (id: string, data: TriageIncidentRequest) => Promise<Incident>;
  onEscalate: (id: string, data: EscalateIncidentRequest) => Promise<Incident>;
  onDeEscalate: (id: string, data: DeEscalateIncidentRequest) => Promise<Incident>;
  onResolve: (id: string, data: ResolveIncidentRequest) => Promise<Incident>;
  onClose: (id: string, data?: CloseIncidentRequest) => Promise<Incident>;
}

type ModalType =
  | 'ACKNOWLEDGE'
  | 'ASSIGN'
  | 'TRIAGE'
  | 'ESCALATE'
  | 'DE_ESCALATE'
  | 'RESOLVE'
  | 'CLOSE'
  | null;

export const IncidentActions: React.FC<IncidentActionsProps> = ({
  incident,
  isMutating = false,
  onAcknowledge,
  onAssign,
  onTriage,
  onEscalate,
  onDeEscalate,
  onResolve,
  onClose,
}) => {
  const { hasPermission } = useAuth();

  const canTriage = hasPermission('incidents.triage');
  const canAssign = hasPermission('incidents.assign');
  const canManage = hasPermission('incidents.manage');
  const canClose = hasPermission('incidents.close');

  const [activeModal, setActiveModal] = useState<ModalType>(null);
  const [modalText, setModalText] = useState('');
  const [targetUser, setTargetUser] = useState('');
  const [selectedSeverity, setSelectedSeverity] = useState<IncidentSeverity>(incident.severity);
  const [deEscalateTarget, setDeEscalateTarget] = useState<IncidentStatus>('TRIAGED');
  const [error, setError] = useState<string | null>(null);

  const status = incident.status;

  const openModal = (type: ModalType) => {
    setActiveModal(type);
    setModalText('');
    setTargetUser('');
    setSelectedSeverity(incident.severity);
    setDeEscalateTarget(incident.status === 'ESCALATED' ? 'TRIAGED' : 'ACKNOWLEDGED');
    setError(null);
  };

  const closeModal = () => {
    setActiveModal(null);
    setModalText('');
    setError(null);
  };

  const handleModalSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError(null);
    try {
      if (activeModal === 'ACKNOWLEDGE') {
        await onAcknowledge(incident.id, { message: modalText.trim() || undefined });
      } else if (activeModal === 'ASSIGN') {
        if (!targetUser.trim()) {
          setError('Assignee identifier is required');
          return;
        }
        await onAssign(incident.id, { assigned_to: targetUser.trim(), reason: modalText.trim() || undefined });
      } else if (activeModal === 'TRIAGE') {
        await onTriage(incident.id, { severity: selectedSeverity, notes: modalText.trim() || undefined });
      } else if (activeModal === 'ESCALATE') {
        if (!modalText.trim()) {
          setError('Escalation reason is required');
          return;
        }
        await onEscalate(incident.id, { reason: modalText.trim() });
      } else if (activeModal === 'DE_ESCALATE') {
        if (!modalText.trim()) {
          setError('De-escalation reason is required');
          return;
        }
        await onDeEscalate(incident.id, { target_status: deEscalateTarget, reason: modalText.trim() });
      } else if (activeModal === 'RESOLVE') {
        if (!modalText.trim()) {
          setError('Resolution summary is required');
          return;
        }
        await onResolve(incident.id, { resolution_summary: modalText.trim() });
      } else if (activeModal === 'CLOSE') {
        await onClose(incident.id, { closure_notes: modalText.trim() || undefined });
      }
      closeModal();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Action failed');
    }
  };

  if (status === 'CLOSED') {
    return (
      <div
        style={{
          padding: '10px 20px',
          backgroundColor: 'rgba(107, 114, 128, 0.1)',
          borderBottom: '1px solid var(--border-medium, #334155)',
          display: 'flex',
          alignItems: 'center',
          gap: '8px',
        }}
      >
        <span className="font-mono text-xs text-muted">
          🔒 This incident is CLOSED and archived. No further lifecycle mutations are permitted.
        </span>
      </div>
    );
  }

  return (
    <>
      <div
        style={{
          padding: '10px 20px',
          backgroundColor: 'var(--bg-surface, #1e293b)',
          borderBottom: '1px solid var(--border-medium, #334155)',
          display: 'flex',
          alignItems: 'center',
          flexWrap: 'wrap',
          gap: '8px',
        }}
        role="toolbar"
        aria-label="Incident Lifecycle Actions"
      >
        <span className="font-mono text-xs text-muted" style={{ marginRight: '4px' }}>
          ACTIONS:
        </span>

        {/* NEW state actions */}
        {status === 'NEW' && canTriage && (
          <button
            type="button"
            className="btn btn-primary btn-sm font-mono"
            onClick={() => openModal('ACKNOWLEDGE')}
            disabled={isMutating}
          >
            Acknowledge
          </button>
        )}

        {/* Assign (NEW, ACKNOWLEDGED, TRIAGED, ESCALATED) */}
        {['NEW', 'ACKNOWLEDGED', 'TRIAGED', 'ESCALATED'].includes(status) && canAssign && (
          <button
            type="button"
            className="btn btn-secondary btn-sm font-mono"
            onClick={() => openModal('ASSIGN')}
            disabled={isMutating}
          >
            {incident.assigned_to ? 'Reassign' : 'Assign'}
          </button>
        )}

        {/* Triage Severity (NEW, ACKNOWLEDGED, TRIAGED, ESCALATED) */}
        {['NEW', 'ACKNOWLEDGED', 'TRIAGED', 'ESCALATED'].includes(status) && canTriage && (
          <button
            type="button"
            className="btn btn-secondary btn-sm font-mono"
            onClick={() => openModal('TRIAGE')}
            disabled={isMutating}
          >
            Triage Severity
          </button>
        )}

        {/* Escalate (ACKNOWLEDGED, TRIAGED) */}
        {['ACKNOWLEDGED', 'TRIAGED'].includes(status) && canTriage && (
          <button
            type="button"
            className="btn btn-secondary btn-sm font-mono"
            style={{ color: '#f87171', borderColor: 'rgba(239, 68, 68, 0.4)' }}
            onClick={() => openModal('ESCALATE')}
            disabled={isMutating}
          >
            ⚡ Escalate
          </button>
        )}

        {/* De-escalate (ESCALATED, TRIAGED) */}
        {['ESCALATED', 'TRIAGED'].includes(status) && canTriage && (
          <button
            type="button"
            className="btn btn-secondary btn-sm font-mono"
            onClick={() => openModal('DE_ESCALATE')}
            disabled={isMutating}
          >
            De-escalate
          </button>
        )}

        {/* Resolve (TRIAGED, ESCALATED, ACKNOWLEDGED) */}
        {['ACKNOWLEDGED', 'TRIAGED', 'ESCALATED'].includes(status) && canManage && (
          <button
            type="button"
            className="btn btn-secondary btn-sm font-mono"
            style={{ color: '#4ade80', borderColor: 'rgba(34, 197, 94, 0.4)' }}
            onClick={() => openModal('RESOLVE')}
            disabled={isMutating}
          >
            ✓ Resolve
          </button>
        )}

        {/* Close (RESOLVED) */}
        {status === 'RESOLVED' && canClose && (
          <button
            type="button"
            className="btn btn-secondary btn-sm font-mono"
            onClick={() => openModal('CLOSE')}
            disabled={isMutating}
          >
            🔒 Formal Close
          </button>
        )}
      </div>

      {/* Confirmation & Form Modal */}
      {activeModal && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="incident-action-modal-title"
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
              maxWidth: '480px',
              padding: '20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <h3 id="incident-action-modal-title" style={{ margin: 0, fontSize: '15px', fontWeight: 700 }}>
                {activeModal === 'ACKNOWLEDGE' && 'Acknowledge Incident'}
                {activeModal === 'ASSIGN' && (incident.assigned_to ? 'Reassign Incident' : 'Assign Incident')}
                {activeModal === 'TRIAGE' && 'Triage Incident Severity'}
                {activeModal === 'ESCALATE' && 'Escalate Incident'}
                {activeModal === 'DE_ESCALATE' && 'De-escalate Incident'}
                {activeModal === 'RESOLVE' && 'Resolve Incident'}
                {activeModal === 'CLOSE' && 'Formal Incident Closure'}
              </h3>
              <button
                type="button"
                className="btn btn-secondary btn-sm"
                onClick={closeModal}
                aria-label="Close modal"
              >
                ✕
              </button>
            </div>

            <form onSubmit={handleModalSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              {activeModal === 'ASSIGN' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label className="font-mono text-xs text-muted" htmlFor="assignee-input">
                    Assignee Username / Operator ID:
                  </label>
                  <input
                    id="assignee-input"
                    type="text"
                    className="tactical-input font-mono text-xs"
                    placeholder="e.g. operator_1, analyst_2"
                    value={targetUser}
                    onChange={(e) => setTargetUser(e.target.value)}
                    required
                    autoFocus
                  />
                </div>
              )}

              {activeModal === 'TRIAGE' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label className="font-mono text-xs text-muted" htmlFor="severity-select">
                    Assessed Operational Severity:
                  </label>
                  <select
                    id="severity-select"
                    className="tactical-select font-mono text-xs"
                    value={selectedSeverity}
                    onChange={(e) => setSelectedSeverity(e.target.value as IncidentSeverity)}
                  >
                    <option value="CRITICAL">CRITICAL (Immediate Multi-Sensor Attention)</option>
                    <option value="HIGH">HIGH (Elevated Tracking & Perimeter Alert)</option>
                    <option value="MEDIUM">MEDIUM (Standard Operational Review)</option>
                    <option value="LOW">LOW (Informational / Baseline Observation)</option>
                  </select>
                </div>
              )}

              {activeModal === 'DE_ESCALATE' && (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label className="font-mono text-xs text-muted" htmlFor="de-escalate-select">
                    Target Operational Status:
                  </label>
                  <select
                    id="de-escalate-select"
                    className="tactical-select font-mono text-xs"
                    value={deEscalateTarget}
                    onChange={(e) => setDeEscalateTarget(e.target.value as IncidentStatus)}
                  >
                    <option value="TRIAGED">TRIAGED</option>
                    <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
                  </select>
                </div>
              )}

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label className="font-mono text-xs text-muted" htmlFor="action-notes-input">
                  {activeModal === 'RESOLVE'
                    ? 'Resolution Summary (Required):'
                    : activeModal === 'ESCALATE' || activeModal === 'DE_ESCALATE'
                    ? 'Reason (Required):'
                    : 'Notes / Reason (Optional):'}
                </label>
                <textarea
                  id="action-notes-input"
                  className="tactical-input font-mono text-xs"
                  style={{ minHeight: '60px', resize: 'vertical' }}
                  placeholder="Enter context, procedural findings, or closure explanation..."
                  value={modalText}
                  onChange={(e) => setModalText(e.target.value)}
                  required={['RESOLVE', 'ESCALATE', 'DE_ESCALATE'].includes(activeModal || '')}
                />
              </div>

              {error && (
                <div role="alert" className="font-mono text-xs" style={{ color: 'var(--status-critical, #ef4444)' }}>
                  {error}
                </div>
              )}

              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
                <button type="button" className="btn btn-secondary btn-sm font-mono" onClick={closeModal}>
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary btn-sm font-mono" disabled={isMutating}>
                  {isMutating ? 'Submitting...' : 'Confirm Action'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </>
  );
};
