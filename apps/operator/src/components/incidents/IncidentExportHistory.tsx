/**
 * AeroGuard Incident Export History Component
 * Stage IM2-B: Operator Console Export Modal UI & Payload Download Manager
 */

import React, { useEffect, useState } from 'react';
import { getIncidentExport, getIncidentExportHistory } from '../../api/incidents';
import { IncidentExportMetadata } from '../../types';
import { downloadPayload, formatFileSize } from '../../utils/downloadManager';

export interface IncidentExportHistoryProps {
  onRefreshTrigger?: number;
}

export const IncidentExportHistory: React.FC<IncidentExportHistoryProps> = ({
  onRefreshTrigger = 0,
}) => {
  const [history, setHistory] = useState<IncidentExportMetadata[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [downloadingId, setDownloadingId] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [offset, setOffset] = useState(0);
  const limit = 10;

  const fetchHistory = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const items = await getIncidentExportHistory({ limit, offset });
      setHistory(items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to fetch export history');
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    fetchHistory();
  }, [offset, onRefreshTrigger]);

  const handleDownloadItem = async (item: IncidentExportMetadata) => {
    setDownloadingId(item.id);
    try {
      const exportRes = await getIncidentExport(item.id);
      if (exportRes.payload) {
        downloadPayload(item.export_number, item.format, exportRes.payload);
      } else {
        setError(`Payload for export ${item.export_number} is unavailable.`);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to retrieve export file.');
    } finally {
      setDownloadingId(null);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
        backgroundColor: 'var(--bg-surface, #1e293b)',
        border: '1px solid var(--border-medium, #334155)',
        borderRadius: '6px',
        padding: '16px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h4 style={{ margin: 0, fontSize: '14px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Export Archival History
          </h4>
          <span className="font-mono text-xs text-muted">
            Audit history &amp; tamper-evident SHA-256 checksums
          </span>
        </div>
        <button
          type="button"
          className="btn btn-secondary btn-sm font-mono"
          onClick={fetchHistory}
          disabled={isLoading}
        >
          ↻ Refresh History
        </button>
      </div>

      {error && (
        <div
          role="alert"
          style={{
            padding: '8px 12px',
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

      {isLoading ? (
        <div className="font-mono text-xs text-muted" style={{ padding: '16px', textAlign: 'center' }}>
          Loading export history records…
        </div>
      ) : history.length === 0 ? (
        <div className="font-mono text-xs text-muted" style={{ padding: '16px', textAlign: 'center' }}>
          No export history found.
        </div>
      ) : (
        <div style={{ overflowX: 'auto' }}>
          <table
            style={{
              width: '100%',
              borderCollapse: 'collapse',
              textAlign: 'left',
              fontSize: '12px',
            }}
            className="font-mono"
          >
            <thead>
              <tr style={{ borderBottom: '1px solid var(--border-medium, #334155)', color: '#94a3b8' }}>
                <th style={{ padding: '8px' }}>EXPORT NUMBER</th>
                <th style={{ padding: '8px' }}>FORMAT</th>
                <th style={{ padding: '8px' }}>RECORDS</th>
                <th style={{ padding: '8px' }}>SIZE</th>
                <th style={{ padding: '8px' }}>CREATED AT</th>
                <th style={{ padding: '8px' }}>SHA-256 CHECKSUM</th>
                <th style={{ padding: '8px', textAlign: 'right' }}>ACTION</th>
              </tr>
            </thead>
            <tbody>
              {history.map((item) => (
                <tr
                  key={item.id}
                  style={{ borderBottom: '1px solid rgba(51, 65, 85, 0.5)' }}
                >
                  <td style={{ padding: '8px', fontWeight: 600, color: '#f8fafc' }}>
                    {item.export_number}
                  </td>
                  <td style={{ padding: '8px' }}>
                    <span
                      style={{
                        padding: '2px 6px',
                        borderRadius: '3px',
                        fontSize: '10px',
                        backgroundColor: item.format === 'JSON' ? 'rgba(59, 130, 246, 0.2)' : 'rgba(168, 85, 247, 0.2)',
                        color: item.format === 'JSON' ? '#60a5fa' : '#c084fc',
                        border: `1px solid ${item.format === 'JSON' ? '#3b82f6' : '#a855f7'}`,
                      }}
                    >
                      {item.format}
                    </span>
                  </td>
                  <td style={{ padding: '8px' }}>{item.record_count}</td>
                  <td style={{ padding: '8px' }}>{formatFileSize(item.file_size_bytes)}</td>
                  <td style={{ padding: '8px', color: '#94a3b8' }}>
                    {new Date(item.created_at).toLocaleString()}
                  </td>
                  <td style={{ padding: '8px', color: '#64748b' }}>
                    <code
                      style={{ fontSize: '10px' }}
                      title={item.sha256_checksum}
                    >
                      {item.sha256_checksum.substring(0, 12)}…
                    </code>
                  </td>
                  <td style={{ padding: '8px', textAlign: 'right' }}>
                    <button
                      type="button"
                      className="btn btn-secondary btn-sm font-mono"
                      style={{ fontSize: '11px', padding: '2px 8px' }}
                      onClick={() => handleDownloadItem(item)}
                      disabled={downloadingId === item.id}
                    >
                      {downloadingId === item.id ? 'Downloading…' : '📥 Download'}
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* Pagination Footer */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', paddingTop: '8px' }}>
        <button
          type="button"
          className="btn btn-secondary btn-sm font-mono"
          onClick={() => setOffset(Math.max(0, offset - limit))}
          disabled={offset === 0 || isLoading}
        >
          ← Previous
        </button>
        <span className="font-mono text-xs text-muted">
          Showing Page {Math.floor(offset / limit) + 1}
        </span>
        <button
          type="button"
          className="btn btn-secondary btn-sm font-mono"
          onClick={() => setOffset(offset + limit)}
          disabled={history.length < limit || isLoading}
        >
          Next →
        </button>
      </div>
    </div>
  );
};
