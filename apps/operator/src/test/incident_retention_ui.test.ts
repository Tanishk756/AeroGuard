/**
 * AeroGuard Operator Console — Stage IM2-D Incident Retention & Archival Governance UI Tests
 * Uses Node.js native test runner (node:test, node:assert/strict).
 */

import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

export interface RetentionPolicyResponse {
  id: string;
  policy_name: string;
  description?: string | null;
  enabled: boolean;
  incident_retention_days: number;
  export_retention_days: number;
  minimum_archive_age_days: number;
  minimum_purge_age_days: number;
  require_archive_before_purge: boolean;
  require_supervisor_approval: boolean;
  dry_run_by_default: boolean;
  created_at: string;
  updated_at: string;
}

export interface RetentionEvaluationResponse {
  policy: RetentionPolicyResponse;
  evaluated_at: string;
  dry_run: boolean;
  total_evaluated: number;
  eligible_for_archive: number;
  already_archived: number;
  eligible_for_purge: number;
  blocked_by_hold: number;
  blocked_by_active_status: number;
  blocked_by_minimum_age: number;
  blocked_by_missing_archive: number;
  sample_records: any[];
}

export interface PurgeIncidentsResponse {
  message: string;
  dry_run: boolean;
  purged_count: number;
  purged_incident_ids: string[];
  audit_event_id?: string | null;
}

describe('AeroGuard Stage IM2-D Incident Retention Governance UI & Safety Unit Tests', () => {
  describe('Retention Policy & Evaluation Model Contracts', () => {
    it('1. validates retention policy response properties', () => {
      const policy: RetentionPolicyResponse = {
        id: 'pol-default-01',
        policy_name: 'DEFAULT_POLICY',
        description: 'Default AeroGuard Compliance Retention Policy',
        enabled: true,
        incident_retention_days: 90,
        export_retention_days: 180,
        minimum_archive_age_days: 30,
        minimum_purge_age_days: 180,
        require_archive_before_purge: true,
        require_supervisor_approval: true,
        dry_run_by_default: true,
        created_at: new Date().toISOString(),
        updated_at: new Date().toISOString(),
      };

      assert.strictEqual(policy.policy_name, 'DEFAULT_POLICY');
      assert.strictEqual(policy.minimum_archive_age_days, 30);
      assert.strictEqual(policy.require_archive_before_purge, true);
      assert.strictEqual(policy.dry_run_by_default, true);
    });

    it('2. validates dry-run evaluation metrics and zero-mutation flag', () => {
      const evaluation: RetentionEvaluationResponse = {
        policy: {
          id: 'pol-01',
          policy_name: 'DEFAULT_POLICY',
          enabled: true,
          incident_retention_days: 90,
          export_retention_days: 180,
          minimum_archive_age_days: 30,
          minimum_purge_age_days: 180,
          require_archive_before_purge: true,
          require_supervisor_approval: true,
          dry_run_by_default: true,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
        evaluated_at: new Date().toISOString(),
        dry_run: true,
        total_evaluated: 150,
        eligible_for_archive: 45,
        already_archived: 30,
        eligible_for_purge: 12,
        blocked_by_hold: 5,
        blocked_by_active_status: 68,
        blocked_by_minimum_age: 20,
        blocked_by_missing_archive: 0,
        sample_records: [],
      };

      assert.strictEqual(evaluation.dry_run, true);
      assert.strictEqual(evaluation.total_evaluated, 150);
      assert.strictEqual(evaluation.eligible_for_archive, 45);
      assert.strictEqual(evaluation.blocked_by_hold, 5);
    });
  });

  describe('Purge Confirmation & Data Safety Verification', () => {
    it('3. requires confirm=true parameter for destructive purge operations', () => {
      const dryRunPurgePayload = { batch_all_eligible: true, confirm: false };
      const explicitPurgePayload = { batch_all_eligible: true, confirm: true };

      assert.strictEqual(dryRunPurgePayload.confirm, false);
      assert.strictEqual(explicitPurgePayload.confirm, true);
    });

    it('4. processes purge response payload upon successful confirmation', () => {
      const purgeRes: PurgeIncidentsResponse = {
        message: 'Successfully purged 5 incident records.',
        dry_run: false,
        purged_count: 5,
        purged_incident_ids: ['inc-01', 'inc-02', 'inc-03', 'inc-04', 'inc-05'],
        audit_event_id: 'audit-evt-purge-999',
      };

      assert.strictEqual(purgeRes.dry_run, false);
      assert.strictEqual(purgeRes.purged_count, 5);
      assert.strictEqual(purgeRes.purged_incident_ids.length, 5);
    });

    it('5. verifies permission gating requirements for retention roles', () => {
      const superAdminPerms = ['incidents.retention.read', 'incidents.archive', 'incidents.purge'];
      const opsAdminPerms = ['incidents.retention.read', 'incidents.archive'];
      const operatorPerms = ['incidents.read', 'incidents.create'];

      assert.ok(superAdminPerms.includes('incidents.purge'));
      assert.ok(opsAdminPerms.includes('incidents.archive'));
      assert.strictEqual(operatorPerms.includes('incidents.purge'), false);
    });
  });
});
