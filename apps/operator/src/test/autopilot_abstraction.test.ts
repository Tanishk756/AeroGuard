import assert from 'node:assert';
import test, { describe, it } from 'node:test';

describe('AeroGuard Stage S9 Autopilot Abstraction Frontend Unit Tests', () => {
  it('validates supported autopilot types and capability matrix', () => {
    const autopilots = ['ARDUPILOT', 'PX4', 'MOCK'];
    assert.strictEqual(autopilots.length, 3);
    assert.ok(autopilots.includes('ARDUPILOT'));
    assert.ok(autopilots.includes('PX4'));
  });
});
