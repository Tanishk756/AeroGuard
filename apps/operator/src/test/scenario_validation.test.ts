import assert from 'node:assert';
import test, { describe, it } from 'node:test';

describe('AeroGuard Stage S6 Scenario Validation Rules Unit Tests', () => {
  it('validates wind speed threshold diagnostics', () => {
    const evaluateWind = (speed: number) => {
      const errors: string[] = [];
      const warnings: string[] = [];
      if (speed < 0 || speed > 50) errors.push(`Wind speed ${speed} m/s out of range [0, 50]`);
      else if (speed > 15) warnings.push(`High wind speed ${speed} m/s may destabilize multicopters`);
      return { valid: errors.length === 0, errors, warnings };
    };

    assert.strictEqual(evaluateWind(5.0).valid, true);
    assert.strictEqual(evaluateWind(20.0).valid, true);
    assert.strictEqual(evaluateWind(20.0).warnings.length, 1);
    assert.strictEqual(evaluateWind(60.0).valid, false);
  });
});
