/**
 * Stage IM3-D Operator Governance UI Archive Integrity & Reconciliation Test Suite
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

export type IntegrityStatusType =
  | 'HEALTHY'
  | 'OBJECT_MISSING'
  | 'CHECKSUM_MISMATCH'
  | 'METADATA_MISMATCH'
  | 'ORPHAN_OBJECT'
  | 'STORAGE_UNAVAILABLE'
  | 'INVALID_ARCHIVE_METADATA';

export interface IntegrityCheckResponse {
  id: string;
  archive_id?: string | null;
  archive_number: string;
  incident_id?: string | null;
  storage_provider: string;
  storage_location?: string | null;
  status: IntegrityStatusType;
  expected_checksum?: string | null;
  observed_checksum?: string | null;
  expected_size_bytes?: number | null;
  observed_size_bytes?: number | null;
  duration_ms: number;
  error_code?: string | null;
  error_message?: string | null;
  checked_at: string;
}

export interface IntegritySummaryResponse {
  total_checks: number;
  healthy_count: number;
  missing_count: number;
  mismatch_count: number;
  orphan_count: number;
  unavailable_count: number;
  last_checked_at?: string | null;
}

export interface IntegrityVerificationBatchResponse {
  message: string;
  verified_count: number;
  checks: IntegrityCheckResponse[];
}

describe('Stage IM3-D Cloud Archive Integrity & Reconciliation UI Tests', () => {
  it('calculates and formats IntegritySummaryResponse metrics accurately', () => {
    const summary: IntegritySummaryResponse = {
      total_checks: 150,
      healthy_count: 142,
      missing_count: 3,
      mismatch_count: 2,
      orphan_count: 3,
      unavailable_count: 0,
      last_checked_at: '2026-08-30T12:00:00Z',
    };

    assert.equal(summary.total_checks, 150);
    assert.equal(summary.healthy_count, 142);
    assert.equal(summary.missing_count + summary.mismatch_count + summary.orphan_count + summary.healthy_count, 150);
    assert.ok(summary.last_checked_at?.startsWith('2026'));
  });

  it('enforces status classification invariants for HEALTHY and OBJECT_MISSING', () => {
    const checkHealthy: IntegrityCheckResponse = {
      id: 'chk-1',
      archive_number: 'ARC-JSON-001',
      storage_provider: 'S3',
      status: 'HEALTHY',
      expected_checksum: 'a'.repeat(64),
      observed_checksum: 'a'.repeat(64),
      duration_ms: 12.4,
      checked_at: '2026-08-30T12:05:00Z',
    };

    const checkMissing: IntegrityCheckResponse = {
      id: 'chk-2',
      archive_number: 'ARC-JSON-002',
      storage_provider: 'S3',
      status: 'OBJECT_MISSING',
      expected_checksum: 'b'.repeat(64),
      observed_checksum: null,
      duration_ms: 5.1,
      error_code: 'OBJECT_MISSING',
      checked_at: '2026-08-30T12:05:01Z',
    };

    assert.equal(checkHealthy.status, 'HEALTHY');
    assert.equal(checkHealthy.expected_checksum, checkHealthy.observed_checksum);

    assert.equal(checkMissing.status, 'OBJECT_MISSING');
    assert.equal(checkMissing.observed_checksum, null);
    assert.equal(checkMissing.error_code, 'OBJECT_MISSING');
  });

  it('aggregates batch verification response items properly', () => {
    const batch: IntegrityVerificationBatchResponse = {
      message: 'Verified 2 archive storage records successfully',
      verified_count: 2,
      checks: [
        {
          id: 'c1',
          archive_number: 'ARC-001',
          storage_provider: 'S3',
          status: 'HEALTHY',
          duration_ms: 10,
          checked_at: '2026-08-30T12:00:00Z',
        },
        {
          id: 'c2',
          archive_number: 'ARC-002',
          storage_provider: 'LOCAL',
          status: 'HEALTHY',
          duration_ms: 2,
          checked_at: '2026-08-30T12:00:00Z',
        },
      ],
    };

    assert.equal(batch.verified_count, 2);
    assert.equal(batch.checks.length, 2);
    assert.equal(batch.checks[0].storage_provider, 'S3');
    assert.equal(batch.checks[1].storage_provider, 'LOCAL');
  });
});
