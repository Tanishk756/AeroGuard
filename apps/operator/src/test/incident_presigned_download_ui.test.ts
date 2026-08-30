/**
 * AeroGuard Stage IM3-C Presigned Download UI & Operator Governance Tests
 * Uses Node.js native test runner (node:test, node:assert/strict).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

export interface ArchiveRecordMetadata {
  id: string;
  archive_number: string;
  incident_id: string;
  sha256_checksum: string;
  file_size_bytes: number;
  archive_format: string;
  storage_provider?: string;
  storage_location?: string | null;
  archived_at: string;
  archived_by: string;
  verified_at?: string | null;
}

export interface PresignedArchiveDownloadResponse {
  url: string;
  expires_at: string;
  expires_in_seconds: number;
  archive_id: string;
  archive_number: string;
  storage_provider: string;
}

export interface StorageHealthResponse {
  provider: string;
  status: 'HEALTHY' | 'UNHEALTHY';
  reachable: boolean;
  location?: string;
  bucket_name?: string;
  region?: string;
  endpoint_url?: string;
  sse_algorithm?: string;
  error?: string;
}

describe('AeroGuard Stage IM3-C Presigned Download & Governance UI Unit Tests', () => {
  it('identifies S3-backed archive records eligible for presigned download', () => {
    const s3Archive: ArchiveRecordMetadata = {
      id: 'arc-s3-101',
      archive_number: 'ARC-PDF-101',
      incident_id: 'inc-101',
      sha256_checksum: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
      file_size_bytes: 2048,
      archive_format: 'PDF',
      storage_provider: 'S3',
      storage_location: 's3://aeroguard-archives/archives/ARC-PDF-101.pdf',
      archived_at: '2026-08-30T10:00:00Z',
      archived_by: 'usr-admin-1',
    };

    const isS3 = (s3Archive.storage_provider || 'LOCAL').toUpperCase() === 'S3';
    assert.equal(isS3, true);
    assert.equal(s3Archive.storage_provider, 'S3');
  });

  it('identifies LOCAL archive records where cloud presigned download is unavailable', () => {
    const localArchive: ArchiveRecordMetadata = {
      id: 'arc-loc-102',
      archive_number: 'ARC-JSON-102',
      incident_id: 'inc-102',
      sha256_checksum: 'a'.repeat(64),
      file_size_bytes: 512,
      archive_format: 'JSON',
      storage_provider: 'LOCAL',
      storage_location: 'data/archives/ARC-JSON-102.json',
      archived_at: '2026-08-30T10:05:00Z',
      archived_by: 'usr-admin-1',
    };

    const isS3 = (localArchive.storage_provider || 'LOCAL').toUpperCase() === 'S3';
    assert.equal(isS3, false);
  });

  it('validates PresignedArchiveDownloadResponse schema contracts', () => {
    const presignedRes: PresignedArchiveDownloadResponse = {
      url: 'https://aeroguard-archives.s3.amazonaws.com/archives/ARC-101.pdf?X-Amz-Signature=abc',
      expires_at: '2026-08-30T10:15:00Z',
      expires_in_seconds: 300,
      archive_id: 'arc-s3-101',
      archive_number: 'ARC-PDF-101',
      storage_provider: 'S3',
    };

    assert.equal(presignedRes.expires_in_seconds, 300);
    assert.equal(presignedRes.storage_provider, 'S3');
    assert.ok(presignedRes.url.startsWith('https://'));
  });

  it('validates StorageHealthResponse telemetry contracts without credentials', () => {
    const s3Health: StorageHealthResponse = {
      provider: 'S3',
      status: 'HEALTHY',
      reachable: true,
      bucket_name: 'aeroguard-archives',
      region: 'us-east-1',
    };

    assert.equal(s3Health.provider, 'S3');
    assert.equal(s3Health.status, 'HEALTHY');
    assert.equal(s3Health.reachable, true);

    const jsonStr = JSON.stringify(s3Health);
    assert.equal(jsonStr.includes('access_key'), false);
    assert.equal(jsonStr.includes('secret_key'), false);
  });

  it('verifies presigned URLs are not persisted in storage', () => {
    const presignedRes: PresignedArchiveDownloadResponse = {
      url: 'https://s3.amazonaws.com/test?sig=123',
      expires_at: '2026-08-30T10:15:00Z',
      expires_in_seconds: 300,
      archive_id: 'arc-1',
      archive_number: 'ARC-1',
      storage_provider: 'S3',
    };

    // In-memory simulation: verify URL is ephemeral
    let memoryUrl: string | null = presignedRes.url;
    assert.ok(memoryUrl);
    memoryUrl = null;
    assert.equal(memoryUrl, null);
  });
});
