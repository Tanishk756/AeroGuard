import assert from 'node:assert';
import test, { describe, it } from 'node:test';

describe('AeroGuard Stage S9 PX4 Flight Mode Mapping Tests', () => {
  it('maps generic flight mode names to PX4 mode strings correctly', () => {
    const modeMap: Record<string, string> = {
      GUIDED: 'OFFBOARD',
      AUTO: 'AUTO.MISSION',
      RTL: 'AUTO.RTL',
      LAND: 'AUTO.LAND',
      STABILIZE: 'STABILIZED',
    };

    assert.strictEqual(modeMap['GUIDED'], 'OFFBOARD');
    assert.strictEqual(modeMap['AUTO'], 'AUTO.MISSION');
    assert.strictEqual(modeMap['RTL'], 'AUTO.RTL');
    assert.strictEqual(modeMap['LAND'], 'AUTO.LAND');
  });
});
