/**
 * AeroGuard Incident Export Modal Component
 * Stage IM2-B: Operator Console Export Modal UI & Payload Download Manager
 */

import React, { useEffect, useState } from 'react';
import { createIncidentExport } from '../../api/incidents';
import {
  CreateIncidentExportRequest,
  IncidentExportFormat,
  IncidentExportMetadata,
  IncidentExportResponse,
  IncidentSeverity,
  IncidentStatus,
} from '../../types';
import { downloadPayload, formatFileSize } from '../../utils/downloadManager';

export interface IncidentExportModalProps {
  isOpen: boolean;
  onClose: () => void;
  onExportSuccess?: (metadata: IncidentExportMetadata) => void;
}

export type ExportDatePreset = 'LAST_24H' | 'LAST_7D' | 'LAST_30D' | 'CUSTOM' | 'ALL';

export const IncidentExportModal: React.FC<IncidentExportModalProps> = ({
  isOpen,
  onClose,
  onExportSuccess,
}) => {
  const [format, setFormat] = useState<IncidentExportFormat>('JSON');
  const [preset, setPreset] = useState<ExportDatePreset>('LAST_7D');
  const [customStart, setCustomStart] = useState('');
  const [customEnd, setCustomEnd] = useState('');
  const [severity, setSeverity] = useState<IncidentSeverity | ''>('');
  const [status, setStatus] = useState<IncidentStatus | ''>('');
  const [assignedTo, setAssignedTo] = useState('');
  const [primaryTrackId, setPrimaryTrackId] = useState('');
  const [primaryGroupId, setPrimaryGroupId] = useState('');

  const [isGenerating, setIsGenerating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [completedResult, setCompletedResult] = useState<IncidentExportResponse | null>(null);
  const [checksumCopied, setChecksumCopied] = useState(false);

  // Escape key handler
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && isOpen && !isGenerating) {
        onClose();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [isOpen, isGenerating, onClose]);

  if (!isOpen) return null;

  const handleReset = () => {
    setError(null);
    setCompletedResult(null);
    setChecksumCopied(false);
  };

  const handleClose = () => {
    handleReset();
    onClose();
  };

  const computeDateRange = (): { start?: string | null; end?: string | null } => {
    const now = new Date();
    if (preset === 'LAST_24H') {
      const start = new Date(now.getTime() - 24 * 60 * 60 * 1000);
      return { start: start.toISOString(), end: now.toISOString() };
    }
    if (preset === 'LAST_7D') {
      const start = new Date(now.getTime() - 7 * 24 * 60 * 60 * 1000);
      return { start: start.toISOString(), end: now.toISOString() };
    }
    if (preset === 'LAST_30D') {
      const start = new Date(now.getTime() - 30 * 24 * 60 * 60 * 1000);
      return { start: start.toISOString(), end: now.toISOString() };
    }
    if (preset === 'CUSTOM') {
      return {
        start: customStart ? new Date(customStart).toISOString() : null,
        end: customEnd ? new Date(customEnd).toISOString() : null,
      };
    }
    return { start: null, end: null };
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    handleReset();
    setIsGenerating(true);

    const { start, end } = computeDateRange();

    const requestPayload: CreateIncidentExportRequest = {
      format,
      start,
      end,
      severity: severity ? severity : null,
      status: status ? status : null,
      assigned_to: assignedTo.trim() || null,
      primary_track_id: primaryTrackId.trim() || null,
      primary_group_id: primaryGroupId.trim() || null,
    };

    try {
      const res = await createIncidentExport(requestPayload);
      setCompletedResult(res);
      if (onExportSuccess) {
        onExportSuccess(res.metadata);
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
      } else {
        setError('Failed to generate incident export payload.');
      }
    } finally {
      setIsGenerating(false);
    }
  };

  const handleDownload = () => {
    if (!completedResult || !completedResult.payload) return;
    downloadPayload(
      completedResult.metadata.export_number,
      completedResult.metadata.format,
      completedResult.payload
    );
  };

  const handleCopyChecksum = () => {
    if (!completedResult?.metadata.sha256_checksum) return;
    navigator.clipboard.writeText(completedResult.metadata.sha256_checksum);
    setChecksumCopied(true);
    setTimeout(() => setChecksumCopied(false), 2000);
  };

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="export-modal-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(0, 0, 0, 0.7)',
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
          maxWidth: '560px',
          padding: '24px',
          display: 'flex',
          flexDirection: 'column',
          gap: '16px',
          boxShadow: '0 20px 25px -5px rgba(0, 0, 0, 0.5)',
        }}
      >
        {/* Header */}
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <div>
            <h3 id="export-modal-title" style={{ margin: 0, fontSize: '16px', fontWeight: 700 }}>
              Export Incident Records
            </h3>
            <p className="text-muted text-xs font-mono" style={{ margin: '2px 0 0' }}>
              Deterministic compliance archival &amp; serialization
            </p>
          </div>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={handleClose}
            aria-label="Close export modal"
            disabled={isGenerating}
          >
            ✕
          </button>
        </div>

        {/* Error Alert Banner */}
        {error && (
          <div
            role="alert"
            style={{
              padding: '10px 12px',
              backgroundColor: 'rgba(239, 68, 68, 0.15)',
              border: '1px solid var(--status-critical, #ef4444)',
              borderRadius: '4px',
              color: '#fca5a5',
              fontSize: '12px',
            }}
            className="font-mono"
          >
            ⚠ {error}
          </div>
        )}

        {/* COMPLETED EXPORT VIEW */}
        {completedResult ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
            <div
              style={{
                backgroundColor: 'rgba(34, 197, 94, 0.1)',
                border: '1px solid var(--status-success, #22c55e)',
                borderRadius: '6px',
                padding: '16px',
                display: 'flex',
                flexDirection: 'column',
                gap: '10px',
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="font-mono text-xs text-muted">EXPORT IDENTIFIER</span>
                <span className="font-mono text-sm" style={{ fontWeight: 700, color: '#4ade80' }}>
                  {completedResult.metadata.export_number}
                </span>
              </div>

              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                <div>
                  <span className="font-mono text-xs text-muted">FORMAT: </span>
                  <span className="font-mono text-xs">{completedResult.metadata.format}</span>
                </div>
                <div>
                  <span className="font-mono text-xs text-muted">SIZE: </span>
                  <span className="font-mono text-xs">
                    {formatFileSize(completedResult.metadata.file_size_bytes)}
                  </span>
                </div>
                <div>
                  <span className="font-mono text-xs text-muted">RECORDS: </span>
                  <span className="font-mono text-xs font-bold">
                    {completedResult.metadata.record_count}
                    {completedResult.metadata.record_count === 0 ? ' (Empty export)' : ''}
                  </span>
                </div>
                <div>
                  <span className="font-mono text-xs text-muted">STATUS: </span>
                  <span className="font-mono text-xs text-success" style={{ fontWeight: 600 }}>
                    {completedResult.metadata.status}
                  </span>
                </div>
              </div>

              {/* SHA-256 Checksum Container */}
              <div style={{ marginTop: '6px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span className="font-mono text-xs text-muted">SHA-256 CHECKSUM (SERVER INTEGRITY)</span>
                  <button
                    type="button"
                    className="btn btn-secondary btn-sm font-mono"
                    style={{ fontSize: '10px', padding: '2px 6px' }}
                    onClick={handleCopyChecksum}
                  >
                    {checksumCopied ? '✓ Copied' : 'Copy Hash'}
                  </button>
                </div>
                <code
                  className="font-mono text-xs"
                  style={{
                    backgroundColor: 'rgba(0, 0, 0, 0.4)',
                    padding: '8px',
                    borderRadius: '4px',
                    wordBreak: 'break-all',
                    color: '#94a3b8',
                    border: '1px solid var(--border-medium, #334155)',
                  }}
                >
                  {completedResult.metadata.sha256_checksum}
                </code>
              </div>
            </div>

            {completedResult.metadata.record_count === 0 && (
              <div
                style={{
                  fontSize: '12px',
                  color: 'var(--color-warning, #f59e0b)',
                  backgroundColor: 'rgba(245, 158, 11, 0.1)',
                  padding: '8px 12px',
                  borderRadius: '4px',
                  border: '1px solid rgba(245, 158, 11, 0.3)',
                }}
                className="font-mono"
              >
                ℹ The export generated successfully, but zero incident records matched your filter criteria.
              </div>
            )}

            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <button
                type="button"
                className="btn btn-secondary font-mono text-xs"
                onClick={() => setCompletedResult(null)}
              >
                ← New Export
              </button>
              <button
                type="button"
                className="btn btn-primary font-mono text-xs"
                onClick={handleDownload}
                disabled={!completedResult.payload}
              >
                📥 Download Export File
              </button>
            </div>
          </div>
        ) : (
          /* EXPORT FORM CONFIGURATION */
          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {/* Format Selection */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="font-mono text-xs text-muted">EXPORT FORMAT</label>
              <div style={{ display: 'flex', gap: '12px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="exportFormat"
                    value="JSON"
                    checked={format === 'JSON'}
                    onChange={() => setFormat('JSON')}
                    disabled={isGenerating}
                  />
                  <span className="font-mono text-xs">JSON (Structured Timeline)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="exportFormat"
                    value="CSV"
                    checked={format === 'CSV'}
                    onChange={() => setFormat('CSV')}
                    disabled={isGenerating}
                  />
                  <span className="font-mono text-xs">CSV (RFC 4180 Flattened Table)</span>
                </label>
              </div>
            </div>

            {/* Date Range Presets */}
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              <label className="font-mono text-xs text-muted" htmlFor="export-preset">
                TIME WINDOW PRESET
              </label>
              <select
                id="export-preset"
                className="tactical-select font-mono text-xs"
                value={preset}
                onChange={(e) => setPreset(e.target.value as ExportDatePreset)}
                disabled={isGenerating}
              >
                <option value="LAST_24H">Last 24 Hours</option>
                <option value="LAST_7D">Last 7 Days</option>
                <option value="LAST_30D">Last 30 Days</option>
                <option value="ALL">All Records (No Time Filter)</option>
                <option value="CUSTOM">Custom Date Range</option>
              </select>
            </div>

            {/* Custom Date Pickers */}
            {preset === 'CUSTOM' && (
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label className="font-mono text-xs text-muted" htmlFor="custom-start">
                    Start Timestamp
                  </label>
                  <input
                    id="custom-start"
                    type="datetime-local"
                    className="tactical-input font-mono text-xs"
                    value={customStart}
                    onChange={(e) => setCustomStart(e.target.value)}
                    disabled={isGenerating}
                  />
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <label className="font-mono text-xs text-muted" htmlFor="custom-end">
                    End Timestamp
                  </label>
                  <input
                    id="custom-end"
                    type="datetime-local"
                    className="tactical-input font-mono text-xs"
                    value={customEnd}
                    onChange={(e) => setCustomEnd(e.target.value)}
                    disabled={isGenerating}
                  />
                </div>
              </div>
            )}

            {/* Severity & Status Filters */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label className="font-mono text-xs text-muted" htmlFor="export-sev">
                  Severity Filter (Optional)
                </label>
                <select
                  id="export-sev"
                  className="tactical-select font-mono text-xs"
                  value={severity}
                  onChange={(e) => setSeverity(e.target.value as IncidentSeverity | '')}
                  disabled={isGenerating}
                >
                  <option value="">All Severities</option>
                  <option value="LOW">LOW</option>
                  <option value="MEDIUM">MEDIUM</option>
                  <option value="HIGH">HIGH</option>
                  <option value="CRITICAL">CRITICAL</option>
                </select>
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label className="font-mono text-xs text-muted" htmlFor="export-stat">
                  Status Filter (Optional)
                </label>
                <select
                  id="export-stat"
                  className="tactical-select font-mono text-xs"
                  value={status}
                  onChange={(e) => setStatus(e.target.value as IncidentStatus | '')}
                  disabled={isGenerating}
                >
                  <option value="">All Statuses</option>
                  <option value="NEW">NEW</option>
                  <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
                  <option value="TRIAGED">TRIAGED</option>
                  <option value="ESCALATED">ESCALATED</option>
                  <option value="RESOLVED">RESOLVED</option>
                  <option value="CLOSED">CLOSED</option>
                </select>
              </div>
            </div>

            {/* Correlation Filters */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label className="font-mono text-xs text-muted" htmlFor="export-track">
                  Primary Track ID (Optional)
                </label>
                <input
                  id="export-track"
                  type="text"
                  className="tactical-input font-mono text-xs"
                  placeholder="e.g. TRK-102"
                  value={primaryTrackId}
                  onChange={(e) => setPrimaryTrackId(e.target.value)}
                  disabled={isGenerating}
                />
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                <label className="font-mono text-xs text-muted" htmlFor="export-group">
                  Primary Swarm/Group ID (Optional)
                </label>
                <input
                  id="export-group"
                  type="text"
                  className="tactical-input font-mono text-xs"
                  placeholder="e.g. GRP-404"
                  value={primaryGroupId}
                  onChange={(e) => setPrimaryGroupId(e.target.value)}
                  disabled={isGenerating}
                />
              </div>
            </div>

            {/* CONFIGURATION SUMMARY PREVIEW */}
            <div
              style={{
                backgroundColor: 'rgba(0, 0, 0, 0.25)',
                border: '1px solid var(--border-medium, #334155)',
                borderRadius: '4px',
                padding: '10px 12px',
                display: 'flex',
                flexDirection: 'column',
                gap: '4px',
              }}
            >
              <span className="font-mono text-xs text-muted">EXPORT CONFIGURATION SUMMARY</span>
              <div className="font-mono text-xs">
                Format: <strong>{format}</strong> | Preset: <strong>{preset}</strong>
                {severity && ` | Severity: ${severity}`}
                {status && ` | Status: ${status}`}
                {primaryTrackId && ` | Track: ${primaryTrackId}`}
                {primaryGroupId && ` | Group: ${primaryGroupId}`}
              </div>
            </div>

            {/* Submission Actions */}
            <div style={{ display: 'flex', gap: '10px', justifyContent: 'flex-end', marginTop: '8px' }}>
              <button
                type="button"
                className="btn btn-secondary font-mono text-xs"
                onClick={handleClose}
                disabled={isGenerating}
              >
                Cancel
              </button>
              <button
                type="submit"
                className="btn btn-primary font-mono text-xs"
                disabled={isGenerating}
              >
                {isGenerating ? 'Generating export payload…' : 'Generate Export'}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
};
