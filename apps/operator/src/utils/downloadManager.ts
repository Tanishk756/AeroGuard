/**
 * AeroGuard Operator Console Download Manager Utility
 * Stage IM2-B: Operator Console Export Modal UI & Payload Download Manager
 */

import { IncidentExportFormat } from '../types';

export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function getExportFilename(exportNumber: string, format: IncidentExportFormat): string {
  const ext = format.toLowerCase();
  return `aeroguard-incidents-${exportNumber}.${ext}`;
}

export function getExportMimeType(format: IncidentExportFormat): string {
  switch (format) {
    case 'JSON':
      return 'application/json';
    case 'CSV':
      return 'text/csv;charset=utf-8';
    case 'PDF':
      return 'application/pdf';
    default:
      return 'text/plain';
  }
}

export function downloadPayload(
  exportNumber: string,
  format: IncidentExportFormat,
  payload: string
): void {
  if (!payload) return;

  const mimeType = getExportMimeType(format);
  const filename = getExportFilename(exportNumber, format);

  let blob: Blob;
  if (format === 'PDF') {
    try {
      const binaryStr = window.atob ? window.atob(payload) : Buffer.from(payload, 'base64').toString('binary');
      const bytes = new Uint8Array(binaryStr.length);
      for (let i = 0; i < binaryStr.length; i++) {
        bytes[i] = binaryStr.charCodeAt(i);
      }
      blob = new Blob([bytes], { type: mimeType });
    } catch {
      blob = new Blob([payload], { type: mimeType });
    }
  } else {
    blob = new Blob([payload], { type: mimeType });
  }

  const url = URL.createObjectURL(blob);

  const link = document.createElement('a');
  link.href = url;
  link.download = filename;
  link.style.display = 'none';

  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);

  // Revoke Object URL to avoid memory leaks
  setTimeout(() => {
    URL.revokeObjectURL(url);
  }, 100);
}
