import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { SwarmVehicleTelemetry, SwarmTelemetrySnapshot } from '../types/swarm';

describe('AeroGuard Stage S11 Swarm Telemetry & Safety Types Unit Tests', () => {
  it('correctly constructs SwarmVehicleTelemetry object', () => {
    const telemetry: Partial<SwarmVehicleTelemetry> = {
      vehicle_id: 'v-01',
      autopilot_type: 'ARDUPILOT',
      role: 'LEADER',
      slot_index: 0,
      current_position_enu: [0, 0, 10],
      current_velocity_enu: [1, 0, 0],
      current_heading_deg: 90,
      desired_position_enu: [0, 0, 10],
      desired_velocity_enu: [1, 0, 0],
      position_error_m: 0.0,
      health_status: 'HEALTHY',
      last_telemetry_timestamp: 1000,
    };

    assert.strictEqual(telemetry.vehicle_id, 'v-01');
    assert.strictEqual(telemetry.role, 'LEADER');
    assert.strictEqual(telemetry.current_heading_deg, 90);
  });

  it('verifies SwarmTelemetrySnapshot spatial metrics formatting', () => {
    const snapshot: Partial<SwarmTelemetrySnapshot> = {
      swarm_id: 'swm-01',
      health: 'HEALTHY',
      timestamp: '2026-09-11T00:00:00Z',
    };

    assert.strictEqual(snapshot.swarm_id, 'swm-01');
    assert.strictEqual(snapshot.health, 'HEALTHY');
  });
});
