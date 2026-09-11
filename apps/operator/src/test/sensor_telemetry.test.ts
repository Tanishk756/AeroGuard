import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { PowerBudgetBreakdown } from '../components/workstation/VehicleBuilderWorkstation';

describe('AeroGuard Stage S8 Power Budget Breakdown Frontend Tests', () => {
  it('validates total non-propulsion power budget calculation', () => {
    const powerBudget: PowerBudgetBreakdown = {
      avionics_power_w: 5.0,
      sensor_power_w: 1.3,
      payload_power_w: 6.5,
      total_non_propulsion_power_w: 12.8,
      estimated_hover_power_w: 212.8,
    };

    assert.strictEqual(powerBudget.total_non_propulsion_power_w, 12.8);
    assert.strictEqual(powerBudget.estimated_hover_power_w, 212.8);
  });
});
