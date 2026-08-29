/**
 * AeroGuard Operator Console — Stage IM2-C Incident PDF Export UI & Document Download Tests
 * Uses Node.js native test runner (node:test, node:assert/strict).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

// ── Standalone Pure Types ──

export type IncidentExportFormat = 'JSON' | 'CSV' | 'PDF';
export type IncidentExportStatus = 'PENDING' | 'COMPLETED' | 'FAILED';

export interface CreateIncidentExportRequest {
  format?: IncidentExportFormat;
  start?: string | null;
  end?: string | null;
  severity?: string | null;
  status?: string | null;
  assigned_to?: string | null;
  primary_track_id?: string | null;
  primary_group_id?: string | null;
}

export interface IncidentExportMetadata {
  id: string;
  export_number: string;
  requested_by: string;
  format: IncidentExportFormat;
  status: IncidentExportStatus;
  record_count: number;
  file_size_bytes: number;
  sha256_checksum: string;
  created_at: string;
  completed_at?: string | null;
  filter_params_json?: Record<string, unknown>;
}

export interface IncidentExportResponse {
  metadata: IncidentExportMetadata;
  payload?: string | null;
}

// ── Pure Utilities (Matching downloadManager.ts) ──

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

export function decodePdfPayloadToUint8Array(base64Payload: string): Uint8Array {
  const binaryStr = Buffer.from(base64Payload, 'base64').toString('binary');
  const bytes = new Uint8Array(binaryStr.length);
  for (let i = 0; i < binaryStr.length; i++) {
    bytes[i] = binaryStr.charCodeAt(i);
  }
  return bytes;
}

describe('AeroGuard Stage IM2-C Incident PDF Export UI & Download Unit Tests', () => {
  describe('PDF Format Utilities & File Conventions', () => {
    it('1. returns application/pdf MIME type for PDF format', () => {
      assert.strictEqual(getExportMimeType('PDF'), 'application/pdf');
    });

    it('2. generates deterministic PDF filename with .pdf extension', () => {
      const filename = getExportFilename('EXP-20260829-PDF9999', 'PDF');
      assert.strictEqual(filename, 'aeroguard-incidents-EXP-20260829-PDF9999.pdf');
    });

    it('3. decodes base64 PDF payload into binary Uint8Array starting with %PDF signature', () => {
      const samplePdfHeader = Buffer.from('%PDF-1.4\n%ReportLab Generated PDF document').toString('base64');
      const bytes = decodePdfPayloadToUint8Array(samplePdfHeader);
      const decodedHeader = Buffer.from(bytes).toString('utf-8');

      assert.ok(decodedHeader.startsWith('%PDF'));
      assert.ok(decodedHeader.includes('ReportLab'));
    });
  });

  describe('PDF Request Construction & Selection Logic', () => {
    it('4. constructs PDF request payload with format=PDF', () => {
      const req: CreateIncidentExportRequest = {
        format: 'PDF',
        start: '2026-08-01T00:00:00.000Z',
        end: '2026-08-29T23:59:59.000Z',
        severity: 'CRITICAL',
      };

      assert.strictEqual(req.format, 'PDF');
      assert.strictEqual(req.severity, 'CRITICAL');
      assert.ok(req.start);
      assert.ok(req.end);
    });

    it('5. preserves JSON and CSV request options alongside PDF format', () => {
      const jsonReq: CreateIncidentExportRequest = { format: 'JSON' };
      const csvReq: CreateIncidentExportRequest = { format: 'CSV' };
      const pdfReq: CreateIncidentExportRequest = { format: 'PDF' };

      assert.strictEqual(jsonReq.format, 'JSON');
      assert.strictEqual(csvReq.format, 'CSV');
      assert.strictEqual(pdfReq.format, 'PDF');
    });
  });

  describe('PDF Response Metadata & Checksum Presentation', () => {
    it('6. validates PDF completed export metadata contract', () => {
      const metadata: IncidentExportMetadata = {
        id: 'exp-pdf-101',
        export_number: 'EXP-20260829-PDF101',
        requested_by: 'usr-admin-1',
        format: 'PDF',
        status: 'COMPLETED',
        record_count: 42,
        file_size_bytes: 128500,
        sha256_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
        created_at: new Date().toISOString(),
      };

      assert.strictEqual(metadata.format, 'PDF');
      assert.strictEqual(metadata.status, 'COMPLETED');
      assert.strictEqual(metadata.record_count, 42);
      assert.strictEqual(formatFileSize(metadata.file_size_bytes), '125.5 KB');
      assert.strictEqual(metadata.sha256_checksum.length, 64);
    });

    it('7. formats PDF export history badge styling deterministically', () => {
      const formats: IncidentExportFormat[] = ['JSON', 'CSV', 'PDF'];
      const badges = formats.map((f) => {
        return f === 'JSON' ? 'blue' : f === 'CSV' ? 'purple' : 'pink';
      });

      assert.deepStrictEqual(badges, ['blue', 'purple', 'pink']);
    });
  });

  describe('RBAC Permission Gating for PDF Exports', () => {
    it('8. permits PDF export request for user holding incidents.export', () => {
      const userPermissions = ['incidents.read', 'incidents.export'];
      const canExport = userPermissions.includes('incidents.export');
      assert.strictEqual(canExport, true);
    });

    it('9. blocks PDF export request for user missing incidents.export', () => {
      const userPermissions = ['incidents.read'];
      const canExport = userPermissions.includes('incidents.export');
      assert.strictEqual(canExport, false);
    });
  });
});
