import assert from 'node:assert';
import test, { describe, it } from 'node:test';

class PureAcousticAlertEngine {
  private muted: boolean = false;
  private acknowledgedAlerts: Set<string> = new Set();
  private lastAlertTime: number = 0;

  public isMuted(): boolean {
    return this.muted;
  }

  public mute(): void {
    this.muted = true;
  }

  public unmute(): void {
    this.muted = false;
  }

  public acknowledgeAlert(alertId: string): void {
    this.acknowledgedAlerts.add(alertId);
  }

  public isAcknowledged(alertId: string): boolean {
    return this.acknowledgedAlerts.has(alertId);
  }

  public playCriticalAlert(alertId?: string, mockNow?: number): boolean {
    if (this.muted) return false;
    if (alertId && this.acknowledgedAlerts.has(alertId)) return false;

    const now = mockNow ?? Date.now();
    if (now - this.lastAlertTime < 500) return false;
    this.lastAlertTime = now;
    return true;
  }
}

describe('AeroGuard Stage PR4 Acoustic Alert Engine Unit Tests', () => {
  describe('Mute and Unmute State Management', () => {
    it('correctly toggles mute and unmute state', () => {
      const engine = new PureAcousticAlertEngine();
      engine.mute();
      assert.strictEqual(engine.isMuted(), true);
      assert.strictEqual(engine.playCriticalAlert('test-alert-1', 1000), false);

      engine.unmute();
      assert.strictEqual(engine.isMuted(), false);
      assert.strictEqual(engine.playCriticalAlert('test-alert-1', 2000), true);
    });
  });

  describe('Alert Deduplication and Acknowledgment', () => {
    it('correctly deduplicates acknowledged alerts', () => {
      const engine = new PureAcousticAlertEngine();
      const alertId = 'alert-ack-123';
      engine.acknowledgeAlert(alertId);
      assert.strictEqual(engine.isAcknowledged(alertId), true);
      assert.strictEqual(engine.playCriticalAlert(alertId, 3000), false);
    });

    it('suppresses rapid alert storms within 500ms window', () => {
      const engine = new PureAcousticAlertEngine();
      assert.strictEqual(engine.playCriticalAlert('alert-1', 5000), true);
      assert.strictEqual(engine.playCriticalAlert('alert-2', 5100), false);
      assert.strictEqual(engine.playCriticalAlert('alert-3', 5600), true);
    });
  });
});
