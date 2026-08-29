/**
 * AeroGuard Operator Console — Stage IM2-D Incident Retention & Archival Governance Console
 */

import React, { useEffect, useState } from 'react';
import {
  ArchiveIncidentsResponse,
  PurgeIncidentsResponse,
  RetentionEvaluationResponse,
  RetentionHoldResponse,
  RetentionPolicyResponse,
} from '../../types/incident';

export function IncidentRetentionGovernance() {
  const [policy, setPolicy] = useState<RetentionPolicyResponse | null>(null);
  const [evaluation, setEvaluation] = useState<RetentionEvaluationResponse | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveResult, setArchiveResult] = useState<ArchiveIncidentsResponse | null>(null);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [purgeResult, setPurgeResult] = useState<PurgeIncidentsResponse | null>(null);
  const [showPurgeConfirm, setShowPurgeConfirm] = useState<boolean>(false);
  const [holdReason, setHoldReason] = useState<string>('');
  const [targetIncidentId, setTargetIncidentId] = useState<string>('');

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [resPol, resEval] = await Promise.all([
        fetch('/api/v1/incidents/retention/policy'),
        fetch('/api/v1/incidents/retention/evaluate?dry_run=true'),
      ]);

      if (!resPol.ok || !resEval.ok) {
        throw new Error('Failed to load retention governance data');
      }

      const polData: RetentionPolicyResponse = await resPol.json();
      const evalData: RetentionEvaluationResponse = await resEval.json();

      setPolicy(polData);
      setEvaluation(evalData);
    } catch (err: any) {
      setError(err.message || 'Error fetching retention configuration');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  const handleTriggerArchive = async () => {
    setIsArchiving(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/incidents/retention/archive', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_all_eligible: true, archive_format: 'JSON' }),
      });
      if (!res.ok) throw new Error('Archival execution failed');
      const data: ArchiveIncidentsResponse = await res.json();
      setArchiveResult(data);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Archival request failed');
    } finally {
      setIsArchiving(false);
    }
  };

  const handleExecutePurge = async () => {
    setIsPurging(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/incidents/retention/purge', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ batch_all_eligible: true, confirm: true }),
      });
      if (!res.ok) throw new Error('Purge execution failed');
      const data: PurgeIncidentsResponse = await res.json();
      setPurgeResult(data);
      setShowPurgeConfirm(false);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Purge execution failed');
    } finally {
      setIsPurging(false);
    }
  };

  const handlePlaceHold = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!targetIncidentId || !holdReason) return;
    try {
      const res = await fetch('/api/v1/incidents/retention/holds', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ incident_id: targetIncidentId, reason: holdReason }),
      });
      if (!res.ok) throw new Error('Failed to place retention hold');
      setTargetIncidentId('');
      setHoldReason('');
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Failed to place hold');
    }
  };

  if (isLoading) {
    return (
      <div className="font-mono text-xs text-muted" style={{ padding: '24px', textAlign: 'center' }}>
        Loading incident retention policy & evaluation state…
      </div>
    );
  }

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '16px' }} className="font-mono">
      {/* Header Banner */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid var(--border-medium, #334155)', paddingBottom: '12px' }}>
        <div>
          <h2 style={{ fontSize: '16px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
            Incident Retention & Archival Governance
          </h2>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>
            Data Lifecycle, Cold Storage Archival, Compliance Holds & Controlled Purge
          </span>
        </div>
        <button
          type="button"
          onClick={fetchData}
          style={{
            padding: '6px 12px',
            backgroundColor: '#1e293b',
            color: '#f8fafc',
            border: '1px solid #334155',
            borderRadius: '4px',
            cursor: 'pointer',
            fontSize: '11px',
          }}
        >
          🔄 Refresh State
        </button>
      </div>

      {error && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', borderRadius: '4px', fontSize: '12px' }}>
          ⚠ {error}
        </div>
      )}

      {/* Policy Configuration Grid */}
      {policy && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
          <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#60a5fa', marginBottom: '12px', marginTop: 0 }}>
            ACTIVE RETENTION POLICY: {policy.policy_name}
          </h3>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '12px', fontSize: '12px' }}>
            <div>
              <span className="text-muted">Incident Retention:</span> <strong style={{ color: '#f8fafc' }}>{policy.incident_retention_days} days</strong>
            </div>
            <div>
              <span className="text-muted">Minimum Archive Age:</span> <strong style={{ color: '#f8fafc' }}>{policy.minimum_archive_age_days} days</strong>
            </div>
            <div>
              <span className="text-muted">Minimum Purge Age:</span> <strong style={{ color: '#f8fafc' }}>{policy.minimum_purge_age_days} days</strong>
            </div>
            <div>
              <span className="text-muted">Require Archive Before Purge:</span>{' '}
              <strong style={{ color: policy.require_archive_before_purge ? '#4ade80' : '#f87171' }}>
                {policy.require_archive_before_purge ? 'YES' : 'NO'}
              </strong>
            </div>
          </div>
        </div>
      )}

      {/* Evaluation Dashboard Summary */}
      {evaluation && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc', margin: 0 }}>
              DRY-RUN EVALUATION METRICS (ZERO MUTATIONS)
            </h3>
            <span style={{ fontSize: '10px', color: '#64748b' }}>
              Evaluated at: {new Date(evaluation.evaluated_at).toLocaleString()}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))', gap: '10px', textAlign: 'center' }}>
            <div style={{ backgroundColor: '#1e293b', padding: '12px', borderRadius: '4px' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#f8fafc' }}>{evaluation.total_evaluated}</div>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>TOTAL EVALUATED</div>
            </div>
            <div style={{ backgroundColor: 'rgba(59, 130, 246, 0.15)', padding: '12px', borderRadius: '4px', border: '1px solid rgba(59, 130, 246, 0.3)' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#60a5fa' }}>{evaluation.eligible_for_archive}</div>
              <div style={{ fontSize: '10px', color: '#93c5fd' }}>ELIGIBLE ARCHIVE</div>
            </div>
            <div style={{ backgroundColor: 'rgba(168, 85, 247, 0.15)', padding: '12px', borderRadius: '4px', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#c084fc' }}>{evaluation.already_archived}</div>
              <div style={{ fontSize: '10px', color: '#e9d5ff' }}>ALREADY ARCHIVED</div>
            </div>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', padding: '12px', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#f87171' }}>{evaluation.eligible_for_purge}</div>
              <div style={{ fontSize: '10px', color: '#fca5a5' }}>ELIGIBLE PURGE</div>
            </div>
            <div style={{ backgroundColor: 'rgba(234, 179, 8, 0.15)', padding: '12px', borderRadius: '4px', border: '1px solid rgba(234, 179, 8, 0.3)' }}>
              <div style={{ fontSize: '18px', fontWeight: 700, color: '#fde047' }}>{evaluation.blocked_by_hold}</div>
              <div style={{ fontSize: '10px', color: '#fef08a' }}>BLOCKED BY HOLD</div>
            </div>
          </div>
        </div>
      )}

      {/* Action Buttons Toolbar */}
      <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
        <button
          type="button"
          onClick={handleTriggerArchive}
          disabled={isArchiving}
          style={{
            padding: '8px 16px',
            backgroundColor: '#2563eb',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            cursor: isArchiving ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
          }}
        >
          {isArchiving ? 'Archiving…' : '📦 Execute Cold Storage Archival'}
        </button>

        <button
          type="button"
          onClick={() => setShowPurgeConfirm(true)}
          disabled={isPurging}
          style={{
            padding: '8px 16px',
            backgroundColor: '#dc2626',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            cursor: isPurging ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
          }}
        >
          🗑️ Execute Purge (Requires Confirmation)
        </button>
      </div>

      {archiveResult && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(34, 197, 94, 0.15)', border: '1px solid #22c55e', color: '#86efac', borderRadius: '4px', fontSize: '12px' }}>
          ✓ {archiveResult.message}
        </div>
      )}

      {purgeResult && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(34, 197, 94, 0.15)', border: '1px solid #22c55e', color: '#86efac', borderRadius: '4px', fontSize: '12px' }}>
          ✓ {purgeResult.message}
        </div>
      )}

      {/* Compliance Hold Dialog Form */}
      <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
        <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#f8fafc', marginTop: 0, marginBottom: '12px' }}>
          🔒 PLACE LEGAL / COMPLIANCE RETENTION HOLD
        </h3>
        <form onSubmit={handlePlaceHold} style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          <input
            type="text"
            placeholder="Incident ID (UUID)"
            value={targetIncidentId}
            onChange={(e) => setTargetIncidentId(e.target.value)}
            style={{ padding: '6px 10px', backgroundColor: '#1e293b', color: '#f8fafc', border: '1px solid #334155', borderRadius: '4px', fontSize: '12px', flex: '1 1 200px' }}
            required
          />
          <input
            type="text"
            placeholder="Hold Reason (e.g. Audit hold)"
            value={holdReason}
            onChange={(e) => setHoldReason(e.target.value)}
            style={{ padding: '6px 10px', backgroundColor: '#1e293b', color: '#f8fafc', border: '1px solid #334155', borderRadius: '4px', fontSize: '12px', flex: '2 1 300px' }}
            required
          />
          <button
            type="submit"
            style={{ padding: '6px 14px', backgroundColor: '#d97706', color: '#ffffff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
          >
            Place Hold
          </button>
        </form>
      </div>

      {/* Explicit Purge Confirmation Dialog */}
      {showPurgeConfirm && (
        <div style={{ position: 'fixed', inset: 0, backgroundColor: 'rgba(0, 0, 0, 0.75)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1000 }}>
          <div style={{ backgroundColor: '#0f172a', border: '1px solid #ef4444', borderRadius: '8px', padding: '24px', maxWidth: '480px', width: '90%' }}>
            <h3 style={{ color: '#f87171', marginTop: 0, fontSize: '16px' }}>⚠ CONFIRM DESTRUCTIVE PURGE OPERATION</h3>
            <p style={{ color: '#cbd5e1', fontSize: '12px', lineHeight: '1.5' }}>
              You are about to permanently delete all verified, eligible archived incident records past the minimum retention purge age threshold ({policy?.minimum_purge_age_days} days).
            </p>
            <p style={{ color: '#fca5a5', fontSize: '11px', fontWeight: 600 }}>
              THIS ACTION CANNOT BE UNDONE. THIS WILL PERMANENTLY REMOVE INCIDENT EVENT HISTORY AND DATABASE RECORDS.
            </p>
            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px', marginTop: '20px' }}>
              <button
                type="button"
                onClick={() => setShowPurgeConfirm(false)}
                style={{ padding: '6px 12px', backgroundColor: '#334155', color: '#f8fafc', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px' }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleExecutePurge}
                style={{ padding: '6px 16px', backgroundColor: '#dc2626', color: '#ffffff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontSize: '12px', fontWeight: 600 }}
              >
                Confirm Destructive Purge
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
