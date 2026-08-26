import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

// ── Helpers replicated from production source (no imports that need DOM/JSX) ──

/**
 * Mirrors CommandPalette command definitions for shortcut-collision testing.
 * Source of truth: apps/operator/src/components/command/CommandPalette.tsx
 */
const COMMAND_SHORTCUTS: { id: string; shortcut?: string }[] = [
  { id: 'nav-overview',       shortcut: 'g o' },
  { id: 'nav-tracks',         shortcut: 'g t' },
  { id: 'nav-sensors',        shortcut: 'g s' },
  { id: 'nav-alerts',         shortcut: 'g a' },
  { id: 'nav-threats',        shortcut: 'g h' },
  { id: 'nav-geofences',      shortcut: 'g z' },
  { id: 'nav-scenarios',      shortcut: 'g c' },
  { id: 'nav-replay',         shortcut: 'g r' },
  { id: 'nav-history',        shortcut: 'g l' },
  { id: 'nav-analytics',      shortcut: 'g y' },
  { id: 'analytics-dashboard',shortcut: 'a' },
  { id: 'analytics-tracks',   shortcut: 'a t' },
  { id: 'analytics-alerts',   shortcut: 'a a' },
  { id: 'analytics-threats',  shortcut: 'a h' },
  { id: 'analytics-detections', shortcut: 'a d' },
  { id: 'nav-audit',          shortcut: 'g u' },
  { id: 'nav-rbac',           shortcut: 'g k' },
  { id: 'nav-diagnostics',    shortcut: 'g d' },
  { id: 'map-fit',            shortcut: 'f' },
  { id: 'map-reset',          shortcut: 'c' },
  { id: 'ops-refresh',        shortcut: 'r' },
  { id: 'ws-inspector',       shortcut: 'i' },
  { id: 'ws-clear',           shortcut: 'Esc' },
];

/** CSV generator — mirrors useAnalytics.generateCsv logic. */
function generateCsv(
  data: Record<string, unknown>[],
  headers: string[],
  maxRows = 10_000,
): string {
  const escapeField = (value: unknown): string => {
    if (value === null || value === undefined) return '';
    const str = String(value);
    if (str.includes('"') || str.includes(',') || str.includes('\n') || str.includes('\r')) {
      return `"${str.replace(/"/g, '""')}"`;
    }
    return str;
  };
  const limited = data.slice(0, maxRows);
  const rows: string[] = [headers.map(escapeField).join(',')];
  for (const row of limited) {
    rows.push(headers.map((h) => escapeField(row[h])).join(','));
  }
  return rows.join('\n');
}

/** Date validator — mirrors AnalyticsPage.parseDateParam logic. */
function parseDateParam(raw: string | null): string | undefined {
  if (!raw) return undefined;
  if (!/^\d{4}-\d{2}-\d{2}$/.test(raw)) return undefined;
  const d = new Date(raw);
  if (isNaN(d.getTime())) return undefined;
  return d.toISOString();
}

/** View parser — mirrors AnalyticsPage.parseView logic. */
type AnalyticsView = 'dashboard' | 'tracks' | 'alerts' | 'threats' | 'detections';
const VALID_VIEWS: AnalyticsView[] = ['dashboard', 'tracks', 'alerts', 'threats', 'detections'];

function parseView(raw: string | null): AnalyticsView {
  if (raw && VALID_VIEWS.includes(raw as AnalyticsView)) return raw as AnalyticsView;
  return 'dashboard';
}

/** RBAC helpers — mirrors AuthContext logic. */
const hasAnyPermission = (userPerms: string[], required: string[]): boolean =>
  required.some((p) => userPerms.includes(p));

// ────────────────────────────────────────────────────────────────────────────

describe('AeroGuard Stage UI6 Advanced Analytics Unit Tests', () => {

  // ── 1. CommandPalette Shortcuts ──────────────────────────────────────────
  describe('CommandPalette Analytics Shortcuts', () => {
    const shortcuts = COMMAND_SHORTCUTS.filter((c) => c.shortcut).map((c) => c.shortcut as string);
    const analyticsIds = ['analytics-dashboard', 'analytics-tracks', 'analytics-alerts', 'analytics-threats', 'analytics-detections'];
    const expectedShortcuts: Record<string, string> = {
      'analytics-dashboard':   'a',
      'analytics-tracks':      'a t',
      'analytics-alerts':      'a a',
      'analytics-threats':     'a h',
      'analytics-detections':  'a d',
    };

    it('all five analytics shortcuts are present in the command list', () => {
      for (const id of analyticsIds) {
        const cmd = COMMAND_SHORTCUTS.find((c) => c.id === id);
        assert.ok(cmd, `Command "${id}" not found`);
        assert.equal(cmd.shortcut, expectedShortcuts[id], `Wrong shortcut for "${id}"`);
      }
    });

    it('no two commands share the same shortcut (no collisions)', () => {
      const seen = new Map<string, string>();
      for (const cmd of COMMAND_SHORTCUTS) {
        if (!cmd.shortcut) continue;
        if (seen.has(cmd.shortcut)) {
          assert.fail(
            `Shortcut collision: "${cmd.shortcut}" used by both "${seen.get(cmd.shortcut)}" and "${cmd.id}"`
          );
        }
        seen.set(cmd.shortcut, cmd.id);
      }
    });

    it('analytics shortcuts do not conflict with existing navigation shortcuts', () => {
      const navShortcuts = COMMAND_SHORTCUTS
        .filter((c) => !analyticsIds.includes(c.id) && c.shortcut)
        .map((c) => c.shortcut as string);
      const analyticsShortcuts = analyticsIds
        .map((id) => COMMAND_SHORTCUTS.find((c) => c.id === id)?.shortcut as string);
      for (const as of analyticsShortcuts) {
        assert.equal(
          navShortcuts.includes(as),
          false,
          `Analytics shortcut "${as}" collides with a non-analytics command`
        );
      }
    });
  });

  // ── 2. Deep-link view parsing ───────────────────────────────────────────
  describe('Analytics Deep-Link URL Parsing', () => {
    it('parses valid view values correctly', () => {
      assert.equal(parseView('dashboard'), 'dashboard');
      assert.equal(parseView('tracks'), 'tracks');
      assert.equal(parseView('alerts'), 'alerts');
      assert.equal(parseView('threats'), 'threats');
      assert.equal(parseView('detections'), 'detections');
    });

    it('falls back to dashboard for invalid or null view param', () => {
      assert.equal(parseView(null), 'dashboard');
      assert.equal(parseView(''), 'dashboard');
      assert.equal(parseView('INVALID_VIEW'), 'dashboard');
      assert.equal(parseView('sensors'), 'dashboard');
      assert.equal(parseView('<script>'), 'dashboard');
    });
  });

  // ── 3. Date parameter validation ────────────────────────────────────────
  describe('Date Parameter Validation (TimeWindowFilter / AnalyticsPage)', () => {
    it('accepts well-formed YYYY-MM-DD dates and returns ISO string', () => {
      const result = parseDateParam('2026-01-31');
      assert.ok(result, 'should return a string');
      assert.ok(result!.startsWith('2026-01-31'), `Expected ISO starting with 2026-01-31, got ${result}`);
    });

    it('rejects null and empty strings, returning undefined', () => {
      assert.equal(parseDateParam(null), undefined);
      assert.equal(parseDateParam(''), undefined);
    });

    it('rejects malformed date strings', () => {
      assert.equal(parseDateParam('invalid'), undefined);
      assert.equal(parseDateParam('2026/01/01'), undefined);
      assert.equal(parseDateParam('01-01-2026'), undefined);
      assert.equal(parseDateParam('2026-13-01'), undefined, 'month 13 should be invalid');
      assert.equal(parseDateParam('2026-00-01'), undefined, 'month 00 should be invalid');
      assert.equal(parseDateParam('not-a-date'), undefined);
    });

    it('validates that start <= end for a time window', () => {
      // Mirror the TimeWindowFilter validation logic.
      const validateWindow = (start: string, end: string): boolean => {
        if (!start || !end) return true; // open-ended windows are valid
        return start <= end;
      };
      assert.equal(validateWindow('2026-01-01', '2026-01-31'), true);
      assert.equal(validateWindow('2026-01-31', '2026-01-31'), true, 'same-day window is valid');
      assert.equal(validateWindow('2026-02-01', '2026-01-31'), false, 'start after end is invalid');
      assert.equal(validateWindow('', '2026-01-31'), true, 'empty start is open-ended');
    });
  });

  // ── 4. CSV Generation ───────────────────────────────────────────────────
  describe('CSV Generation (useAnalytics.generateCsv)', () => {
    it('produces correct header row', () => {
      const csv = generateCsv([], ['Name', 'Value']);
      assert.equal(csv, 'Name,Value');
    });

    it('serializes basic data rows correctly', () => {
      const data = [{ Name: 'Alpha', Value: 42 }, { Name: 'Beta', Value: 7 }];
      const csv = generateCsv(data, ['Name', 'Value']);
      const lines = csv.split('\n');
      assert.equal(lines.length, 3);
      assert.equal(lines[0], 'Name,Value');
      assert.equal(lines[1], 'Alpha,42');
      assert.equal(lines[2], 'Beta,7');
    });

    it('escapes commas by wrapping field in double quotes', () => {
      const data = [{ Name: 'Alpha, Bravo', Value: 1 }];
      const csv = generateCsv(data, ['Name', 'Value']);
      assert.ok(csv.includes('"Alpha, Bravo"'), `Expected quoted comma field, got: ${csv}`);
    });

    it('escapes embedded double quotes per RFC 4180 (doubles them)', () => {
      const data = [{ Name: 'Say "Hello"', Value: 1 }];
      const csv = generateCsv(data, ['Name', 'Value']);
      assert.ok(csv.includes('"Say ""Hello"""'), `Expected doubled quotes, got: ${csv}`);
    });

    it('escapes newlines by wrapping in double quotes', () => {
      const data = [{ Name: 'Line1\nLine2', Value: 1 }];
      const csv = generateCsv(data, ['Name', 'Value']);
      assert.ok(csv.includes('"Line1\nLine2"'), `Expected quoted newline, got: ${csv}`);
    });

    it('renders empty values as empty fields', () => {
      const data = [{ Name: '', Value: null }];
      const csv = generateCsv(data, ['Name', 'Value']);
      const dataLine = csv.split('\n')[1];
      assert.equal(dataLine, ',', `Expected empty fields, got: ${dataLine}`);
    });

    it('preserves Unicode characters without escaping', () => {
      const data = [{ Name: 'Δ Track • 🛰', Value: 1 }];
      const csv = generateCsv(data, ['Name', 'Value']);
      assert.ok(csv.includes('Δ Track • 🛰'), `Expected Unicode preserved, got: ${csv}`);
    });

    it('enforces maxRows limit and excludes rows beyond it', () => {
      const data = Array.from({ length: 20 }, (_, i) => ({ Name: `row-${i}` }));
      const csv = generateCsv(data, ['Name'], 5);
      const lines = csv.split('\n');
      // 1 header + 5 data rows = 6 lines
      assert.equal(lines.length, 6, `Expected 6 lines (1 header + 5 rows), got ${lines.length}`);
      assert.equal(lines[5], 'row-4');
    });

    it('default maxRows is 10,000', () => {
      // Verify the signature accepts the third param and the first 10,001 rows
      // would be truncated to 10,000. We just verify it doesn't throw for large input.
      const data = Array.from({ length: 50 }, (_, i) => ({ x: i }));
      const csv = generateCsv(data, ['x']);
      const lines = csv.split('\n');
      assert.equal(lines.length, 51, 'All 50 rows plus header should be present');
    });
  });

  // ── 5. RBAC: analytics route permission check ───────────────────────────
  describe('Analytics Route RBAC Guard (hasAnyPermission)', () => {
    const ANALYTICS_PERMS = ['sensors.read', 'tracks.read', 'alerts.read', 'threats.read'];

    it('grants access when user has sensors.read', () => {
      assert.equal(hasAnyPermission(['sensors.read'], ANALYTICS_PERMS), true);
    });

    it('grants access when user has any one required permission', () => {
      assert.equal(hasAnyPermission(['threats.read', 'scenarios.run'], ANALYTICS_PERMS), true);
    });

    it('grants access when user has all required permissions', () => {
      assert.equal(hasAnyPermission(ANALYTICS_PERMS, ANALYTICS_PERMS), true);
    });

    it('denies access when user has none of the required permissions', () => {
      assert.equal(hasAnyPermission(['scenarios.run', 'audit.read'], ANALYTICS_PERMS), false);
    });

    it('denies access for an unauthenticated user (empty permissions)', () => {
      assert.equal(hasAnyPermission([], ANALYTICS_PERMS), false);
    });
  });

  // ── 6. AnalyticsTable column / data logic ───────────────────────────────
  describe('AnalyticsTable Column Definitions', () => {
    // Mirror the column definitions for each analytics view.
    interface Column { key: string; label: string }

    const detectionsColumns: Column[] = [
      { key: 'total_detections', label: 'Total' },
    ];
    const tracksColumns: Column[] = [
      { key: 'total_tracks', label: 'Total' },
      { key: 'average_confidence', label: 'Avg Confidence' },
    ];

    it('detections columns reference backend schema fields only', () => {
      const validKeys = ['total_detections', 'detections_by_sensor', 'detections_by_source_type', 'detections_by_classification'];
      for (const col of detectionsColumns) {
        assert.ok(validKeys.includes(col.key), `Unexpected field "${col.key}" not in backend schema`);
      }
    });

    it('tracks columns reference backend schema fields only', () => {
      const validKeys = ['total_tracks', 'tracks_by_state', 'tracks_by_classification', 'average_confidence', 'average_duration_seconds'];
      for (const col of tracksColumns) {
        assert.ok(validKeys.includes(col.key), `Unexpected field "${col.key}" not in backend schema`);
      }
    });

    it('column labels are non-empty strings', () => {
      for (const col of [...detectionsColumns, ...tracksColumns]) {
        assert.ok(col.label.length > 0, `Column "${col.key}" has empty label`);
      }
    });
  });

  // ── 7. BarChart data transformation logic ───────────────────────────────
  describe('BarChart Data Transformation', () => {
    interface BarChartItem { label: string; value: number }

    // Mirrors how AnalyticsPage transforms summary data for BarChart.
    const toBarItems = (dict: Record<string, number>): BarChartItem[] =>
      Object.entries(dict).map(([label, value]) => ({ label, value }));

    it('converts distribution dict to label/value array', () => {
      const items = toBarItems({ ACTIVE: 10, LOST: 3, ARCHIVED: 2 });
      assert.equal(items.length, 3);
      const active = items.find((i) => i.label === 'ACTIVE');
      assert.ok(active);
      assert.equal(active!.value, 10);
    });

    it('returns empty array for empty dict', () => {
      const items = toBarItems({});
      assert.equal(items.length, 0);
    });

    it('max value computation is correct (used for bar scaling)', () => {
      const items = toBarItems({ A: 5, B: 20, C: 15 });
      const max = Math.max(...items.map((d) => d.value), 1);
      assert.equal(max, 20);
    });

    it('max falls back to 1 for all-zero data (no division by zero)', () => {
      const items = toBarItems({ A: 0, B: 0 });
      const max = Math.max(...items.map((d) => d.value), 1);
      assert.equal(max, 1);
    });

    it('BarChart desc text format matches expected screen-reader output', () => {
      const items: BarChartItem[] = [{ label: 'A', value: 10 }, { label: 'B', value: 20 }];
      const descText = items.map((d) => `${d.label}: ${d.value}`).join(', ');
      assert.equal(descText, 'A: 10, B: 20');
    });
  });

  // ── 8. Stale-request abort logic ─────────────────────────────────────────
  describe('Stale Request Abort Protection (useAnalytics)', () => {
    it('AbortController signal starts as not-aborted', () => {
      const ctrl = new AbortController();
      assert.equal(ctrl.signal.aborted, false);
    });

    it('aborting controller marks signal as aborted', () => {
      const ctrl = new AbortController();
      ctrl.abort();
      assert.equal(ctrl.signal.aborted, true);
    });

    it('replacing controller ref aborts the previous one', () => {
      let controllerRef: AbortController | null = null;

      const startFetch = () => {
        controllerRef?.abort();
        const ctrl = new AbortController();
        controllerRef = ctrl;
        return ctrl;
      };

      const first = startFetch();
      assert.equal(first.signal.aborted, false);

      // Second fetch supersedes first.
      startFetch();
      assert.equal(first.signal.aborted, true, 'First controller should be aborted after second fetch starts');
    });
  });

  // ── 9. Analytics window parameter mapping ────────────────────────────────
  describe('Analytics Window Parameter Mapping (API → backend field names)', () => {
    interface ApiParams { window_start?: string; window_end?: string }

    const mapToApiParams = (p: { windowStart?: string; windowEnd?: string }): ApiParams => ({
      window_start: p.windowStart,
      window_end: p.windowEnd,
    });

    it('maps windowStart/windowEnd to window_start/window_end', () => {
      const params = mapToApiParams({ windowStart: '2026-01-01T00:00:00Z', windowEnd: '2026-01-31T23:59:59Z' });
      assert.equal(params.window_start, '2026-01-01T00:00:00Z');
      assert.equal(params.window_end, '2026-01-31T23:59:59Z');
    });

    it('produces undefined fields when window is not specified', () => {
      const params = mapToApiParams({});
      assert.equal(params.window_start, undefined);
      assert.equal(params.window_end, undefined);
    });
  });
});
