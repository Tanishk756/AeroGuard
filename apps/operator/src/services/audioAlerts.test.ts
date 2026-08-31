import { describe, it, expect, beforeEach } from 'vitest';
import { audioAlertEngine } from './audioAlerts';

describe('AcousticAlertEngine', () => {
  beforeEach(() => {
    audioAlertEngine.unmute();
  });

  it('should mute and unmute correctly', () => {
    audioAlertEngine.mute();
    expect(audioAlertEngine.isMuted()).toBe(true);
    expect(audioAlertEngine.playCriticalAlert('test-alert-1')).toBe(false);

    audioAlertEngine.unmute();
    expect(audioAlertEngine.isMuted()).toBe(false);
  });

  it('should deduplicate acknowledged alerts', () => {
    const alertId = 'alert-ack-123';
    audioAlertEngine.acknowledgeAlert(alertId);
    expect(audioAlertEngine.isAcknowledged(alertId)).toBe(true);
    expect(audioAlertEngine.playCriticalAlert(alertId)).toBe(false);
  });
});
