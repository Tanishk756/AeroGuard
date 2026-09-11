import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { Swarm, SwarmState, FormationType, SafetyEvent } from '../types/swarm';

describe('AeroGuard Stage S10 Multi-Vehicle Swarm & Formation Types Unit Tests', () => {
  it('correctly constructs a multi-vehicle heterogeneous swarm object', () => {
    const swarm: Swarm = {
      id: 'swm-01',
      name: 'Alpha Swarm',
      formation_type: 'V_FORMATION',
      formation_spacing_m: 10.0,
      min_separation_m: 5.0,
      status: 'IDLE',
      leader_vehicle_id: 'v-01',
      members: [
        { id: 'm-1', swarm_id: 'swm-01', vehicle_id: 'v-01', role: 'LEADER', slot_index: 0, offset_x: 0, offset_y: 0, offset_z: 0 },
        { id: 'm-2', swarm_id: 'swm-01', vehicle_id: 'v-02', role: 'FOLLOWER', slot_index: 1, offset_x: -10, offset_y: -10, offset_z: 0 },
        { id: 'm-3', swarm_id: 'swm-01', vehicle_id: 'v-03', role: 'FOLLOWER', slot_index: 2, offset_x: -10, offset_y: 10, offset_z: 0 },
      ],
      created_at: '2026-09-11T00:00:00Z',
      updated_at: '2026-09-11T00:00:00Z',
    };

    assert.strictEqual(swarm.id, 'swm-01');
    assert.strictEqual(swarm.formation_type, 'V_FORMATION');
    assert.strictEqual(swarm.members.length, 3);
    assert.strictEqual(swarm.members[0].role, 'LEADER');
  });

  it('correctly parses SwarmState telemetry and safety events', () => {
    const event: SafetyEvent = {
      event_type: 'MINIMUM_SEPARATION_BREACH',
      severity: 'CRITICAL',
      vehicle_id: 'v-01',
      target_vehicle_id: 'v-02',
      distance_m: 3.5,
      threshold_m: 5.0,
      timestamp: '2026-09-11T00:00:00Z',
      message: 'Minimum separation breach',
    };

    const swarmState: SwarmState = {
      swarm_id: 'swm-01',
      leader_vehicle_id: 'v-01',
      formation_type: 'V_FORMATION',
      health: 'CRITICAL',
      vehicle_states: {},
      safety_events: [event],
      timestamp: '2026-09-11T00:00:00Z',
    };

    assert.strictEqual(swarmState.health, 'CRITICAL');
    assert.strictEqual(swarmState.safety_events.length, 1);
    assert.strictEqual(swarmState.safety_events[0].event_type, 'MINIMUM_SEPARATION_BREACH');
  });
});
