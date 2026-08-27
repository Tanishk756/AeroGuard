import assert from 'node:assert';
import test, { describe, it } from 'node:test';

// ── Pure logic mirroring production desktop bridge & window state ──

export interface Alert {
  id: string;
  type: string;
  severity: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  status: 'OPEN' | 'ACKNOWLEDGED' | 'RESOLVED';
  track_id?: string | null;
  sensor_id?: string | null;
  reason: string;
}

function evaluateIsTauri(winObj: Record<string, unknown> | undefined): boolean {
  if (!winObj) return false;
  return Boolean(winObj.__TAURI_INTERNALS__ || winObj.__TAURI__);
}

function evaluateBackendOnlineStatus(status?: string): boolean {
  if (!status) return false;
  const normalized = status.toLowerCase().trim();
  return normalized === 'healthy' || normalized === 'degraded';
}

function clampWindowDimensions(
  width: number,
  height: number,
  minWidth = 1280,
  minHeight = 800,
  maxWidth = 7680,
  maxHeight = 4320
): { width: number; height: number } {
  return {
    width: Math.max(minWidth, Math.min(maxWidth, width)),
    height: Math.max(minHeight, Math.min(maxHeight, height)),
  };
}

function resolveWindowStateTransition(
  action: 'minimize' | 'maximize' | 'unmaximize' | 'toggleMaximize' | 'close',
  currentMaximized: boolean,
  isDesktop: boolean
): { executed: boolean; nextMaximized: boolean } {
  if (!isDesktop) {
    return { executed: false, nextMaximized: false };
  }

  switch (action) {
    case 'maximize':
      return { executed: true, nextMaximized: true };
    case 'unmaximize':
      return { executed: true, nextMaximized: false };
    case 'toggleMaximize':
      return { executed: true, nextMaximized: !currentMaximized };
    case 'minimize':
      return { executed: true, nextMaximized: currentMaximized };
    case 'close':
      return { executed: true, nextMaximized: currentMaximized };
    default:
      return { executed: false, nextMaximized: currentMaximized };
  }
}

interface TitlebarControlSpec {
  id: string;
  symbol: string;
  ariaLabel: string;
  tooltip: string;
}

function getTitlebarControlSpecs(isMaximized: boolean): TitlebarControlSpec[] {
  return [
    {
      id: 'btn-minimize',
      symbol: '🗕',
      ariaLabel: 'Minimize Window',
      tooltip: 'Minimize Window',
    },
    {
      id: 'btn-maximize-restore',
      symbol: isMaximized ? '🗗' : '🗖',
      ariaLabel: isMaximized ? 'Restore Window' : 'Maximize Window',
      tooltip: isMaximized ? 'Restore Window' : 'Maximize Window',
    },
    {
      id: 'btn-close',
      symbol: '✕',
      ariaLabel: 'Close Application',
      tooltip: 'Close Application',
    },
  ];
}

interface TrayActionResolution {
  action: 'toggle' | 'quit' | 'unknown';
  handled: boolean;
  effect: 'show_and_focus' | 'exit_process' | 'noop';
}

function resolveTrayMenuAction(actionId: string): TrayActionResolution {
  switch (actionId) {
    case 'toggle':
      return { action: 'toggle', handled: true, effect: 'show_and_focus' };
    case 'quit':
      return { action: 'quit', handled: true, effect: 'exit_process' };
    default:
      return { action: 'unknown', handled: false, effect: 'noop' };
  }
}

class AlertNotificationDeduplicator {
  private notifiedKeys = new Map<string, number>();
  private readonly maxCapacity: number;

  constructor(maxCapacity = 100) {
    this.maxCapacity = maxCapacity;
  }

  public makeKey(alert: Pick<Alert, 'id' | 'status' | 'severity'>): string {
    return `${alert.id}:${alert.status}:${alert.severity}`;
  }

  public shouldNotify(alert: Pick<Alert, 'id' | 'status' | 'severity'>): boolean {
    const key = this.makeKey(alert);
    if (this.notifiedKeys.has(key)) {
      return false;
    }

    if (this.notifiedKeys.size >= this.maxCapacity) {
      const entries = Array.from(this.notifiedKeys.entries());
      entries.sort((a, b) => a[1] - b[1]);
      for (let i = 0; i < Math.min(30, entries.length); i++) {
        this.notifiedKeys.delete(entries[i][0]);
      }
    }

    this.notifiedKeys.set(key, Date.now());
    return true;
  }

  public clear(): void {
    this.notifiedKeys.clear();
  }

  public size(): number {
    return this.notifiedKeys.size;
  }
}

function isAlertSeverityEligible(alert: Pick<Alert, 'severity' | 'status'>): boolean {
  if (alert.status && alert.status !== 'OPEN') {
    return false;
  }
  const sev = (alert.severity || '').toUpperCase();
  return sev === 'CRITICAL' || sev === 'HIGH';
}

function sanitizeNotificationBody(text: string): string {
  if (!text) return '';
  let clean = text
    .replace(/(bearer\s+[a-zA-Z0-9._-]+)/gi, '[REDACTED]')
    .replace(/(password\s*=\s*\S+)/gi, 'password=[REDACTED]')
    .replace(/(token\s*=\s*\S+)/gi, 'token=[REDACTED]');

  if (clean.length > 200) {
    clean = clean.substring(0, 197) + '...';
  }
  return clean;
}

function simulateDispatchAlertNotifications(
  alerts: Alert[],
  isTauriRunning: boolean,
  isOnline: boolean,
  deduplicator: AlertNotificationDeduplicator
): number {
  if (!isTauriRunning || !isOnline || !Array.isArray(alerts)) {
    return 0;
  }

  let count = 0;
  for (const alert of alerts) {
    if (isAlertSeverityEligible(alert) && deduplicator.shouldNotify(alert)) {
      count++;
    }
  }
  return count;
}

describe('AeroGuard Stage UI8 Desktop Bridge & Environment Unit Tests', () => {
  describe('Tauri Environment Detection & Browser Fallback', () => {
    it('returns false in standard browser environment where __TAURI_INTERNALS__ is undefined', () => {
      assert.strictEqual(evaluateIsTauri(undefined), false);
      assert.strictEqual(evaluateIsTauri({}), false);
      assert.strictEqual(evaluateIsTauri({ window: {} }), false);
    });

    it('returns true when __TAURI_INTERNALS__ or __TAURI__ exists on global object', () => {
      assert.strictEqual(evaluateIsTauri({ __TAURI_INTERNALS__: {} }), true);
      assert.strictEqual(evaluateIsTauri({ __TAURI__: {} }), true);
    });

    it('safely no-ops window control actions in browser environment without throwing', () => {
      const actions: ('minimize' | 'maximize' | 'unmaximize' | 'toggleMaximize' | 'close')[] = [
        'minimize',
        'maximize',
        'unmaximize',
        'toggleMaximize',
        'close',
      ];

      for (const act of actions) {
        const result = resolveWindowStateTransition(act, false, false);
        assert.strictEqual(result.executed, false, `Action ${act} should not execute in browser`);
        assert.strictEqual(result.nextMaximized, false);
      }
    });
  });

  describe('Desktop Window State Transitions', () => {
    it('correctly transitions maximized state upon maximize command in desktop mode', () => {
      const result = resolveWindowStateTransition('maximize', false, true);
      assert.strictEqual(result.executed, true);
      assert.strictEqual(result.nextMaximized, true);
    });

    it('correctly transitions restored state upon unmaximize command in desktop mode', () => {
      const result = resolveWindowStateTransition('unmaximize', true, true);
      assert.strictEqual(result.executed, true);
      assert.strictEqual(result.nextMaximized, false);
    });

    it('toggles maximized state accurately between true and false', () => {
      const toggleFromNormal = resolveWindowStateTransition('toggleMaximize', false, true);
      assert.strictEqual(toggleFromNormal.executed, true);
      assert.strictEqual(toggleFromNormal.nextMaximized, true);

      const toggleFromMaximized = resolveWindowStateTransition('toggleMaximize', true, true);
      assert.strictEqual(toggleFromMaximized.executed, true);
      assert.strictEqual(toggleFromMaximized.nextMaximized, false);
    });

    it('preserves maximized state on minimize and close actions', () => {
      const minResult = resolveWindowStateTransition('minimize', true, true);
      assert.strictEqual(minResult.executed, true);
      assert.strictEqual(minResult.nextMaximized, true);

      const closeResult = resolveWindowStateTransition('close', false, true);
      assert.strictEqual(closeResult.executed, true);
      assert.strictEqual(closeResult.nextMaximized, false);
    });
  });

  describe('Window Dimension Boundary Clamping', () => {
    it('enforces minimum tactical window bounds of 1280x800', () => {
      const small = clampWindowDimensions(1024, 768);
      assert.strictEqual(small.width, 1280);
      assert.strictEqual(small.height, 800);
    });

    it('preserves valid standard operational resolutions (1440x900, 1920x1080, 2560x1440)', () => {
      const r1 = clampWindowDimensions(1440, 900);
      assert.strictEqual(r1.width, 1440);
      assert.strictEqual(r1.height, 900);

      const r2 = clampWindowDimensions(1920, 1080);
      assert.strictEqual(r2.width, 1920);
      assert.strictEqual(r2.height, 1080);

      const r3 = clampWindowDimensions(2560, 1440);
      assert.strictEqual(r3.width, 2560);
      assert.strictEqual(r3.height, 1440);
    });

    it('clamps overly large dimensions to max safe bounds', () => {
      const oversized = clampWindowDimensions(10000, 8000);
      assert.strictEqual(oversized.width, 7680);
      assert.strictEqual(oversized.height, 4320);
    });
  });

  describe('Backend Connectivity & Health Interpretation', () => {
    it('evaluates healthy and degraded backend responses as online', () => {
      assert.strictEqual(evaluateBackendOnlineStatus('healthy'), true);
      assert.strictEqual(evaluateBackendOnlineStatus('HEALTHY'), true);
      assert.strictEqual(evaluateBackendOnlineStatus('degraded'), true);
      assert.strictEqual(evaluateBackendOnlineStatus('DEGRADED'), true);
    });

    it('evaluates unhealthy, offline, empty, or undefined responses as offline', () => {
      assert.strictEqual(evaluateBackendOnlineStatus('unhealthy'), false);
      assert.strictEqual(evaluateBackendOnlineStatus('offline'), false);
      assert.strictEqual(evaluateBackendOnlineStatus(''), false);
      assert.strictEqual(evaluateBackendOnlineStatus(undefined), false);
    });
  });

  describe('Desktop Titlebar Accessibility & Control Specifications', () => {
    it('generates correct accessibility specs for normal window state', () => {
      const controls = getTitlebarControlSpecs(false);
      assert.strictEqual(controls.length, 3);

      const min = controls.find((c) => c.id === 'btn-minimize');
      assert.ok(min);
      assert.strictEqual(min.ariaLabel, 'Minimize Window');

      const max = controls.find((c) => c.id === 'btn-maximize-restore');
      assert.ok(max);
      assert.strictEqual(max.ariaLabel, 'Maximize Window');
      assert.strictEqual(max.symbol, '🗖');

      const close = controls.find((c) => c.id === 'btn-close');
      assert.ok(close);
      assert.strictEqual(close.ariaLabel, 'Close Application');
    });

    it('updates maximize/restore spec when window is maximized', () => {
      const controls = getTitlebarControlSpecs(true);
      const maxRestore = controls.find((c) => c.id === 'btn-maximize-restore');
      assert.ok(maxRestore);
      assert.strictEqual(maxRestore.ariaLabel, 'Restore Window');
      assert.strictEqual(maxRestore.symbol, '🗗');
    });
  });

  describe('Native Alert Notification Severity Filtering', () => {
    it('accepts CRITICAL and HIGH severity alerts in OPEN state', () => {
      assert.strictEqual(isAlertSeverityEligible({ severity: 'CRITICAL', status: 'OPEN' }), true);
      assert.strictEqual(isAlertSeverityEligible({ severity: 'HIGH', status: 'OPEN' }), true);
    });

    it('rejects MEDIUM and LOW severity alerts', () => {
      assert.strictEqual(isAlertSeverityEligible({ severity: 'MEDIUM', status: 'OPEN' }), false);
      assert.strictEqual(isAlertSeverityEligible({ severity: 'LOW', status: 'OPEN' }), false);
    });

    it('rejects non-OPEN alerts regardless of severity', () => {
      assert.strictEqual(isAlertSeverityEligible({ severity: 'CRITICAL', status: 'ACKNOWLEDGED' }), false);
      assert.strictEqual(isAlertSeverityEligible({ severity: 'CRITICAL', status: 'RESOLVED' }), false);
      assert.strictEqual(isAlertSeverityEligible({ severity: 'HIGH', status: 'ACKNOWLEDGED' }), false);
    });
  });

  describe('Bounded In-Memory Alert Notification Deduplication', () => {
    it('deduplicates identical alert occurrences correctly', () => {
      const deduplicator = new AlertNotificationDeduplicator(10);
      const alert: Pick<Alert, 'id' | 'status' | 'severity'> = {
        id: 'alt-001',
        status: 'OPEN',
        severity: 'CRITICAL',
      };

      assert.strictEqual(deduplicator.shouldNotify(alert), true);
      assert.strictEqual(deduplicator.shouldNotify(alert), false);
      assert.strictEqual(deduplicator.shouldNotify(alert), false);
    });

    it('allows re-notification when alert state transitions', () => {
      const deduplicator = new AlertNotificationDeduplicator(10);
      const alertOpen: Pick<Alert, 'id' | 'status' | 'severity'> = {
        id: 'alt-002',
        status: 'OPEN',
        severity: 'HIGH',
      };
      const alertAck: Pick<Alert, 'id' | 'status' | 'severity'> = {
        id: 'alt-002',
        status: 'ACKNOWLEDGED',
        severity: 'HIGH',
      };

      assert.strictEqual(deduplicator.shouldNotify(alertOpen), true);
      assert.strictEqual(deduplicator.shouldNotify(alertAck), true);
    });

    it('bounds cache size and trims oldest entries when exceeding max capacity', () => {
      const capacity = 5;
      const deduplicator = new AlertNotificationDeduplicator(capacity);

      for (let i = 0; i < 10; i++) {
        deduplicator.shouldNotify({
          id: `alt-${i}`,
          status: 'OPEN',
          severity: 'CRITICAL',
        });
      }

      assert.ok(deduplicator.size() <= capacity, `Size ${deduplicator.size()} should not exceed ${capacity}`);
    });
  });

  describe('Notification Payload Sanitization', () => {
    it('strips credentials, passwords, and tokens from notification messages', () => {
      const dirty = 'Alert triggered with bearer eyJhbGciOi... and password=supersecret';
      const clean = sanitizeNotificationBody(dirty);
      assert.ok(!clean.toLowerCase().includes('bearer eyj'));
      assert.ok(!clean.toLowerCase().includes('password=supersecret'));
      assert.ok(clean.includes('[REDACTED]'));
    });

    it('truncates oversized messages cleanly with ellipsis', () => {
      const longMessage = 'A'.repeat(300);
      const clean = sanitizeNotificationBody(longMessage);
      assert.strictEqual(clean.length, 200);
      assert.ok(clean.endsWith('...'));
    });
  });

  describe('Notification Dispatch Environmental Rules', () => {
    it('suppresses notifications when running in standard browser mode', () => {
      const deduplicator = new AlertNotificationDeduplicator();
      const alerts: Alert[] = [
        { id: '1', type: 'GEOFENCE_BREACH', severity: 'CRITICAL', status: 'OPEN', reason: 'Breach' },
      ];
      const count = simulateDispatchAlertNotifications(alerts, false, true, deduplicator);
      assert.strictEqual(count, 0);
    });

    it('suppresses notifications when backend is offline', () => {
      const deduplicator = new AlertNotificationDeduplicator();
      const alerts: Alert[] = [
        { id: '1', type: 'GEOFENCE_BREACH', severity: 'CRITICAL', status: 'OPEN', reason: 'Breach' },
      ];
      const count = simulateDispatchAlertNotifications(alerts, true, false, deduplicator);
      assert.strictEqual(count, 0);
    });

    it('dispatches eligible alerts when in desktop mode and online', () => {
      const deduplicator = new AlertNotificationDeduplicator();
      const alerts: Alert[] = [
        { id: '1', type: 'GEOFENCE_BREACH', severity: 'CRITICAL', status: 'OPEN', reason: 'Breach' },
        { id: '2', type: 'SENSOR_OFFLINE', severity: 'LOW', status: 'OPEN', reason: 'Low' },
      ];
      const count = simulateDispatchAlertNotifications(alerts, true, true, deduplicator);
      assert.strictEqual(count, 1);
    });
  });

  describe('System Tray Menu Action Resolution', () => {
    it('maps toggle action to show_and_focus', () => {
      const res = resolveTrayMenuAction('toggle');
      assert.strictEqual(res.handled, true);
      assert.strictEqual(res.effect, 'show_and_focus');
    });

    it('maps quit action to exit_process', () => {
      const res = resolveTrayMenuAction('quit');
      assert.strictEqual(res.handled, true);
      assert.strictEqual(res.effect, 'exit_process');
    });

    it('safely handles unknown tray action IDs', () => {
      const res = resolveTrayMenuAction('unknown_id');
      assert.strictEqual(res.handled, false);
      assert.strictEqual(res.effect, 'noop');
    });
  });
});
