/**
 * AeroGuard Operator Console — Stage IM3-D Incident Retention, Archival & Cold Storage Integrity Governance Console
 */

import React, { useEffect, useState } from 'react';
import {
  ArchiveIncidentsResponse,
  IntegrityCheckResponse,
  IntegritySummaryResponse,
  IntegrityVerificationBatchResponse,
  PresignedArchiveDownloadResponse,
  PurgeIncidentsResponse,
  RetentionEvaluationResponse,
  RetentionPolicyResponse,
  StorageHealthResponse,
} from '../../types/incident';

export function IncidentRetentionGovernance() {
  const [policy, setPolicy] = useState<RetentionPolicyResponse | null>(null);
  const [evaluation, setEvaluation] = useState<RetentionEvaluationResponse | null>(null);
  const [storageHealth, setStorageHealth] = useState<StorageHealthResponse | null>(null);
  const [integritySummary, setIntegritySummary] = useState<IntegritySummaryResponse | null>(null);
  const [integrityChecks, setIntegrityChecks] = useState<IntegrityCheckResponse[]>([]);
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [isArchiving, setIsArchiving] = useState<boolean>(false);
  const [archiveResult, setArchiveResult] = useState<ArchiveIncidentsResponse | null>(null);
  const [isPurging, setIsPurging] = useState<boolean>(false);
  const [purgeResult, setPurgeResult] = useState<PurgeIncidentsResponse | null>(null);
  const [isVerifyingIntegrity, setIsVerifyingIntegrity] = useState<boolean>(false);
  const [integrityBatchResult, setIntegrityBatchResult] = useState<IntegrityVerificationBatchResponse | null>(null);
  const [showPurgeConfirm, setShowPurgeConfirm] = useState<boolean>(false);
  const [holdReason, setHoldReason] = useState<string>('');
  const [targetIncidentId, setTargetIncidentId] = useState<string>('');

  // Presigned Download State
  const [downloadingArchiveId, setDownloadingArchiveId] = useState<string | null>(null);
  const [activePresignedUrl, setActivePresignedUrl] = useState<PresignedArchiveDownloadResponse | null>(null);
  const [downloadError, setDownloadError] = useState<string | null>(null);

  const fetchData = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [resPol, resEval, resHealth, resIntSummary, resIntChecks] = await Promise.all([
        fetch('/api/v1/incidents/retention/policy'),
        fetch('/api/v1/incidents/retention/evaluate?dry_run=true'),
        fetch('/api/v1/incidents/retention/storage/health'),
        fetch('/api/v1/incidents/retention/integrity/summary'),
        fetch('/api/v1/incidents/retention/integrity?limit=50'),
      ]);

      if (!resPol.ok || !resEval.ok) {
        throw new Error('Failed to load retention governance data');
      }

      const polData: RetentionPolicyResponse = await resPol.json();
      const evalData: RetentionEvaluationResponse = await resEval.json();
      const healthData: StorageHealthResponse = resHealth.ok ? await resHealth.json() : null;
      const intSummaryData: IntegritySummaryResponse = resIntSummary.ok ? await resIntSummary.json() : null;
      const intChecksData: IntegrityCheckResponse[] = resIntChecks.ok ? await resIntChecks.json() : [];

      setPolicy(polData);
      setEvaluation(evalData);
      setStorageHealth(healthData);
      setIntegritySummary(intSummaryData);
      setIntegrityChecks(intChecksData);
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

  const handleRunIntegrityCheck = async () => {
    setIsVerifyingIntegrity(true);
    setError(null);
    try {
      const res = await fetch('/api/v1/incidents/retention/integrity/check?limit=100', {
        method: 'POST',
      });
      if (!res.ok) throw new Error('Integrity verification execution failed');
      const data: IntegrityVerificationBatchResponse = await res.json();
      setIntegrityBatchResult(data);
      await fetchData();
    } catch (err: any) {
      setError(err.message || 'Integrity check failed');
    } finally {
      setIsVerifyingIntegrity(false);
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

  const handleRequestPresignedDownload = async (archiveId: string) => {
    setDownloadingArchiveId(archiveId);
    setDownloadError(null);
    setActivePresignedUrl(null);
    try {
      const res = await fetch(`/api/v1/incidents/retention/archives/${archiveId}/download-url?expires_in_seconds=300`);
      if (!res.ok) {
        const errJson = await res.json().catch(() => ({}));
        throw new Error(errJson.detail || 'Failed to generate S3 presigned download URL');
      }
      const data: PresignedArchiveDownloadResponse = await res.json();
      setActivePresignedUrl(data);

      const link = document.createElement('a');
      link.href = data.url;
      link.download = `${data.archive_number}.json`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
    } catch (err: any) {
      setDownloadError(err.message || 'Download request failed');
    } finally {
      setDownloadingArchiveId(null);
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
            Incident Retention, Archival & Cold Storage Integrity
          </h2>
          <span style={{ fontSize: '11px', color: '#94a3b8' }}>
            Multi-Provider Storage Router, Presigned S3 Downloads & Cloud Integrity Reconciliation
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

      {/* Storage Health Telemetry Banner */}
      {storageHealth && (
        <div style={{ padding: '12px 16px', backgroundColor: '#0f172a', border: `1px solid ${storageHealth.status === 'HEALTHY' ? '#059669' : '#dc2626'}`, borderRadius: '6px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <div>
            <span style={{ fontSize: '11px', color: '#94a3b8', display: 'block' }}>COLD STORAGE PROVIDER HEALTH STATUS</span>
            <strong style={{ fontSize: '14px', color: storageHealth.status === 'HEALTHY' ? '#34d399' : '#f87171' }}>
              PROVIDER: {storageHealth.provider} ({storageHealth.status})
            </strong>
          </div>
          <div style={{ fontSize: '11px', color: '#cbd5e1', textAlign: 'right' }}>
            {storageHealth.provider === 'S3' ? (
              <>
                <div>Bucket: {storageHealth.bucket_name}</div>
                <div>Region: {storageHealth.region}</div>
              </>
            ) : (
              <div>Location: {storageHealth.location}</div>
            )}
          </div>
        </div>
      )}

      {error && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', borderRadius: '4px', fontSize: '12px' }}>
          ⚠ {error}
        </div>
      )}

      {downloadError && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(239, 68, 68, 0.15)', border: '1px solid #ef4444', color: '#fca5a5', borderRadius: '4px', fontSize: '12px' }}>
          ⚠ Download Error: {downloadError}. Request a new download link.
        </div>
      )}

      {activePresignedUrl && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(59, 130, 246, 0.15)', border: '1px solid #3b82f6', color: '#93c5fd', borderRadius: '4px', fontSize: '12px' }}>
          ✓ Secure download URL issued for {activePresignedUrl.archive_number}. Link expires in {Math.round(activePresignedUrl.expires_in_seconds / 60)} minutes.
        </div>
      )}

      {/* Cold Storage Integrity Summary Dashboard */}
      {integritySummary && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '12px' }}>
            <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#34d399', margin: 0 }}>
              🛡️ COLD STORAGE ARCHIVE INTEGRITY SUMMARY
            </h3>
            <span style={{ fontSize: '10px', color: '#64748b' }}>
              Last Verified: {integritySummary.last_checked_at ? new Date(integritySummary.last_checked_at).toLocaleString() : 'Never'}
            </span>
          </div>

          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(130px, 1fr))', gap: '10px', textAlign: 'center' }}>
            <div style={{ backgroundColor: '#1e293b', padding: '10px', borderRadius: '4px' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#f8fafc' }}>{integritySummary.total_checks}</div>
              <div style={{ fontSize: '10px', color: '#94a3b8' }}>TOTAL CHECKS</div>
            </div>
            <div style={{ backgroundColor: 'rgba(34, 197, 94, 0.15)', padding: '10px', borderRadius: '4px', border: '1px solid rgba(34, 197, 94, 0.3)' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#4ade80' }}>{integritySummary.healthy_count}</div>
              <div style={{ fontSize: '10px', color: '#86efac' }}>HEALTHY</div>
            </div>
            <div style={{ backgroundColor: 'rgba(239, 68, 68, 0.15)', padding: '10px', borderRadius: '4px', border: '1px solid rgba(239, 68, 68, 0.3)' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#f87171' }}>{integritySummary.missing_count}</div>
              <div style={{ fontSize: '10px', color: '#fca5a5' }}>MISSING</div>
            </div>
            <div style={{ backgroundColor: 'rgba(234, 179, 8, 0.15)', padding: '10px', borderRadius: '4px', border: '1px solid rgba(234, 179, 8, 0.3)' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#fde047' }}>{integritySummary.mismatch_count}</div>
              <div style={{ fontSize: '10px', color: '#fef08a' }}>MISMATCHES</div>
            </div>
            <div style={{ backgroundColor: 'rgba(168, 85, 247, 0.15)', padding: '10px', borderRadius: '4px', border: '1px solid rgba(168, 85, 247, 0.3)' }}>
              <div style={{ fontSize: '16px', fontWeight: 700, color: '#c084fc' }}>{integritySummary.orphan_count}</div>
              <div style={{ fontSize: '10px', color: '#e9d5ff' }}>ORPHANS</div>
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
          onClick={handleRunIntegrityCheck}
          disabled={isVerifyingIntegrity}
          style={{
            padding: '8px 16px',
            backgroundColor: '#059669',
            color: '#ffffff',
            border: 'none',
            borderRadius: '4px',
            cursor: isVerifyingIntegrity ? 'not-allowed' : 'pointer',
            fontSize: '12px',
            fontWeight: 600,
          }}
        >
          {isVerifyingIntegrity ? 'Verifying Integrity…' : '🔍 Run Bounded Integrity Check'}
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

      {integrityBatchResult && (
        <div style={{ padding: '10px 14px', backgroundColor: 'rgba(34, 197, 94, 0.15)', border: '1px solid #22c55e', color: '#86efac', borderRadius: '4px', fontSize: '12px' }}>
          ✓ {integrityBatchResult.message}
        </div>
      )}

      {/* Integrity Verification History Table */}
      {integrityChecks.length > 0 && (
        <div style={{ backgroundColor: '#0f172a', border: '1px solid #1e293b', borderRadius: '6px', padding: '16px' }}>
          <h3 style={{ fontSize: '13px', fontWeight: 600, color: '#38bdf8', marginTop: 0, marginBottom: '12px' }}>
            INTEGRITY VERIFICATION AUDIT TRAIL ({integrityChecks.length} CHECKS)
          </h3>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '11px', textAlign: 'left' }}>
              <thead>
                <tr style={{ borderBottom: '1px solid #334155', color: '#94a3b8' }}>
                  <th style={{ padding: '6px 8px' }}>Archive Number</th>
                  <th style={{ padding: '6px 8px' }}>Provider</th>
                  <th style={{ padding: '6px 8px' }}>Status</th>
                  <th style={{ padding: '6px 8px' }}>Expected Checksum</th>
                  <th style={{ padding: '6px 8px' }}>Observed Checksum</th>
                  <th style={{ padding: '6px 8px' }}>Checked At</th>
                </tr>
              </thead>
              <tbody>
                {integrityChecks.map((chk) => {
                  const isHealthy = chk.status === 'HEALTHY';
                  const isMissing = chk.status === 'OBJECT_MISSING';
                  const isMismatch = chk.status === 'CHECKSUM_MISMATCH' || chk.status === 'METADATA_MISMATCH';
                  const isOrphan = chk.status === 'ORPHAN_OBJECT';

                  let statusColor = '#94a3b8';
                  if (isHealthy) statusColor = '#4ade80';
                  else if (isMissing) statusColor = '#f87171';
                  else if (isMismatch) statusColor = '#fde047';
                  else if (isOrphan) statusColor = '#c084fc';

                  return (
                    <tr key={chk.id} style={{ borderBottom: '1px solid #1e293b', color: '#f8fafc' }}>
                      <td style={{ padding: '6px 8px', fontWeight: 600 }}>{chk.archive_number}</td>
                      <td style={{ padding: '6px 8px', color: '#cbd5e1' }}>{chk.storage_provider}</td>
                      <td style={{ padding: '6px 8px', color: statusColor, fontWeight: 700 }}>{chk.status}</td>
                      <td style={{ padding: '6px 8px', color: '#64748b' }}>
                        {chk.expected_checksum ? `${chk.expected_checksum.substring(0, 12)}…` : 'N/A'}
                      </td>
                      <td style={{ padding: '6px 8px', color: '#64748b' }}>
                        {chk.observed_checksum ? `${chk.observed_checksum.substring(0, 12)}…` : 'N/A'}
                      </td>
                      <td style={{ padding: '6px 8px', color: '#94a3b8' }}>{new Date(chk.checked_at).toLocaleString()}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
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
