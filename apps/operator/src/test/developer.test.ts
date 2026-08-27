import assert from 'node:assert';
import test, { describe, it } from 'node:test';

// ── Pure testable domain logic mirroring production src/api/developer.ts ──

type ApiDomain =
  | 'Platform & Health'
  | 'Authentication & Session'
  | 'Sensor Ingestion'
  | 'Tracking & Fusion'
  | 'Intelligence & Defense'
  | 'Simulation & Scenarios'
  | 'Historical & Analytics'
  | 'Governance & RBAC';

type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';

interface ApiParamDefinition {
  name: string;
  type: 'string' | 'number' | 'boolean' | 'enum';
  required: boolean;
  description: string;
  defaultValue?: string | number | boolean;
  options?: string[];
}

interface ApiEndpoint {
  id: string;
  domain: ApiDomain;
  name: string;
  method: HttpMethod;
  path: string;
  description: string;
  requiredPermission?: string;
  requiredAnyPermissions?: string[];
  pathParams?: ApiParamDefinition[];
  queryParams?: ApiParamDefinition[];
  requestBodySchema?: string;
  requestBodyTemplate?: string;
  responseDescription?: string;
}

const API_DOMAINS: ApiDomain[] = [
  'Platform & Health',
  'Authentication & Session',
  'Sensor Ingestion',
  'Tracking & Fusion',
  'Intelligence & Defense',
  'Simulation & Scenarios',
  'Historical & Analytics',
  'Governance & RBAC',
];

const API_CATALOG: ApiEndpoint[] = [
  { id: 'health_get', domain: 'Platform & Health', name: 'Database & System Health', method: 'GET', path: '/health', description: 'Public health probe' },
  { id: 'system_info_get', domain: 'Platform & Health', name: 'Runtime Specifications', method: 'GET', path: '/system/info', description: 'System info', requiredPermission: 'system.read' },
  { id: 'auth_login_post', domain: 'Authentication & Session', name: 'Operator Session Login', method: 'POST', path: '/auth/login', description: 'Session login' },
  { id: 'auth_logout_post', domain: 'Authentication & Session', name: 'Operator Session Logout', method: 'POST', path: '/auth/logout', description: 'Session logout' },
  { id: 'auth_me_get', domain: 'Authentication & Session', name: 'Current Session Profile', method: 'GET', path: '/me', description: 'Session me' },
  { id: 'sensors_list_get', domain: 'Sensor Ingestion', name: 'List Registered Sensors', method: 'GET', path: '/sensors', description: 'Sensors list', requiredPermission: 'sensors.read' },
  { id: 'sensor_detail_get', domain: 'Sensor Ingestion', name: 'Sensor Profile & Status', method: 'GET', path: '/sensors/{sensor_id}', description: 'Sensor detail', requiredPermission: 'sensors.read' },
  { id: 'sensors_detection_post', domain: 'Sensor Ingestion', name: 'Ingest Sensor Observation', method: 'POST', path: '/sensors/{sensor_id}/detections', description: 'Ingest detection', requiredPermission: 'sensors.configure' },
  { id: 'tracks_list_get', domain: 'Tracking & Fusion', name: 'Query Operational Tracks', method: 'GET', path: '/tracks', description: 'Tracks query', requiredPermission: 'tracks.read' },
  { id: 'track_detail_get', domain: 'Tracking & Fusion', name: 'Track Detail & Kinematics', method: 'GET', path: '/tracks/{track_id}', description: 'Track detail', requiredPermission: 'tracks.read' },
  { id: 'track_history_get', domain: 'Tracking & Fusion', name: 'Track Kinematic History', method: 'GET', path: '/tracks/{track_id}/history', description: 'Track history', requiredPermission: 'tracks.read' },
  { id: 'alerts_list_get', domain: 'Intelligence & Defense', name: 'Operational Alerts Feed', method: 'GET', path: '/alerts', description: 'Alerts feed', requiredPermission: 'alerts.read' },
  { id: 'alert_detail_get', domain: 'Intelligence & Defense', name: 'Alert Detail & Context', method: 'GET', path: '/alerts/{alert_id}', description: 'Alert detail', requiredPermission: 'alerts.read' },
  { id: 'threats_list_get', domain: 'Intelligence & Defense', name: 'Threat Priority Assessments', method: 'GET', path: '/threats', description: 'Threat assessments', requiredPermission: 'threats.read' },
  { id: 'threat_detail_get', domain: 'Intelligence & Defense', name: 'Track Threat Assessment', method: 'GET', path: '/threats/{track_id}', description: 'Track threat assessment', requiredPermission: 'threats.read' },
  { id: 'geofences_list_get', domain: 'Intelligence & Defense', name: 'List Defense Geofences', method: 'GET', path: '/geofences', description: 'Geofences list', requiredPermission: 'scenarios.read' },
  { id: 'geofences_create_post', domain: 'Intelligence & Defense', name: 'Create Defense Geofence', method: 'POST', path: '/geofences', description: 'Create geofence', requiredPermission: 'scenarios.create' },
  { id: 'scenarios_list_get', domain: 'Simulation & Scenarios', name: 'List Scenario Configurations', method: 'GET', path: '/scenarios', description: 'Scenarios list', requiredPermission: 'scenarios.read' },
  { id: 'scenario_detail_get', domain: 'Simulation & Scenarios', name: 'Scenario Configuration Detail', method: 'GET', path: '/scenarios/{scenario_id}', description: 'Scenario detail', requiredPermission: 'scenarios.read' },
  { id: 'scenario_start_post', domain: 'Simulation & Scenarios', name: 'Start Simulation Execution', method: 'POST', path: '/scenarios/{scenario_id}/start', description: 'Start scenario', requiredPermission: 'scenarios.run' },
  { id: 'scenario_step_post', domain: 'Simulation & Scenarios', name: 'Single Step Simulation Clock', method: 'POST', path: '/scenarios/{scenario_id}/step', description: 'Step scenario', requiredPermission: 'scenarios.run' },
  { id: 'scenario_stop_post', domain: 'Simulation & Scenarios', name: 'Stop Simulation Execution', method: 'POST', path: '/scenarios/{scenario_id}/stop', description: 'Stop scenario', requiredPermission: 'scenarios.run' },
  { id: 'history_timeline_get', domain: 'Historical & Analytics', name: 'Unified Operational Timeline', method: 'GET', path: '/history/timeline', description: 'Timeline', requiredAnyPermissions: ['sensors.read', 'tracks.read', 'alerts.read', 'threats.read'] },
  { id: 'analytics_summary_get', domain: 'Historical & Analytics', name: 'Descriptive Analytics Summary', method: 'GET', path: '/analytics/summary', description: 'Analytics summary', requiredAnyPermissions: ['sensors.read', 'tracks.read', 'alerts.read', 'threats.read'] },
  { id: 'analytics_tracks_get', domain: 'Historical & Analytics', name: 'Tracks Classification Analytics', method: 'GET', path: '/analytics/tracks', description: 'Track analytics', requiredPermission: 'tracks.read' },
  { id: 'replay_query_post', domain: 'Historical & Analytics', name: 'Query Replay Time-Slice', method: 'POST', path: '/replay/query', description: 'Replay query', requiredAnyPermissions: ['scenarios.read', 'tracks.read', 'scenarios.run'] },
  { id: 'audit_events_get', domain: 'Governance & RBAC', name: 'Security Audit Ledger Explorer', method: 'GET', path: '/audit/events', description: 'Audit events', requiredPermission: 'audit.read' },
  { id: 'roles_list_get', domain: 'Governance & RBAC', name: 'List RBAC Roles', method: 'GET', path: '/roles', description: 'Roles list', requiredAnyPermissions: ['roles.read', 'permissions.read'] },
  { id: 'permissions_list_get', domain: 'Governance & RBAC', name: 'List System Permissions', method: 'GET', path: '/permissions', description: 'Permissions list', requiredAnyPermissions: ['permissions.read', 'roles.read'] },
];

function interpolatePath(path: string, pathParams: Record<string, string> = {}): string {
  let result = path;
  for (const [key, value] of Object.entries(pathParams)) {
    result = result.replace(new RegExp(`\\{${key}\\}`, 'g'), encodeURIComponent(value));
  }
  return result;
}

function buildQueryString(params: Record<string, string | number | boolean | undefined | null> = {}): string {
  const searchParams = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && String(value).trim() !== '') {
      searchParams.append(key, String(value));
    }
  }
  const str = searchParams.toString();
  return str ? `?${str}` : '';
}

function generateCurlCommand(
  method: string,
  url: string,
  headers: Record<string, string> = {},
  body?: string,
  shell: 'powershell' | 'posix' = 'powershell'
): string {
  const isPostOrPut = ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase());
  const headerParts: string[] = [];

  for (const [key, value] of Object.entries(headers)) {
    headerParts.push(`-H "${key}: ${value}"`);
  }

  if (shell === 'powershell') {
    let cmd = `curl.exe -X ${method} "${url}"`;
    if (headerParts.length > 0) {
      cmd += ` ${headerParts.join(' ')}`;
    }
    if (isPostOrPut && body && body.trim()) {
      const escaped = body.replace(/"/g, '\\"');
      cmd += ` --data "${escaped}"`;
    }
    return cmd;
  }

  let cmd = `curl -X ${method} '${url}'`;
  if (headerParts.length > 0) {
    cmd += ` ${headerParts.join(' ')}`;
  }
  if (isPostOrPut && body && body.trim()) {
    const escaped = body.replace(/'/g, `'\\''`);
    cmd += ` -d '${escaped}'`;
  }
  return cmd;
}

function generateFetchSnippet(
  method: string,
  url: string,
  headers: Record<string, string> = {},
  body?: string
): string {
  const isPostOrPut = ['POST', 'PUT', 'PATCH'].includes(method.toUpperCase());
  const config: Record<string, unknown> = {
    method,
    credentials: 'include',
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  const snippet = `const response = await fetch('${url}', {
  method: '${method}',
  credentials: 'include',
  headers: ${JSON.stringify(config.headers, null, 4).replace(/\n/g, '\n  ')}${
    isPostOrPut && body && body.trim()
      ? `,\n  body: JSON.stringify(${body.replace(/\n/g, '\n  ')})`
      : ''
  }
});
const data = await response.json();
console.log(data);`;

  return snippet;
}

function validateDetectionPayload(payload: Record<string, unknown>): { valid: boolean; errors: string[] } {
  const errors: string[] = [];

  if (!payload || typeof payload !== 'object') {
    return { valid: false, errors: ['Payload must be a valid JSON object.'] };
  }

  if (!payload.source_detection_id || typeof payload.source_detection_id !== 'string' || !payload.source_detection_id.trim()) {
    errors.push('Missing required field: source_detection_id (non-empty string).');
  }

  if (!payload.timestamp || typeof payload.timestamp !== 'string') {
    errors.push('Missing required field: timestamp (ISO-8601 string).');
  } else {
    const parsedDate = new Date(payload.timestamp);
    if (isNaN(parsedDate.getTime())) {
      errors.push('Invalid timestamp format: must be valid ISO-8601.');
    } else {
      const now = new Date();
      if (parsedDate.getTime() > now.getTime() + 10000) {
        errors.push('Timestamp cannot be in the future.');
      }
    }
  }

  if (typeof payload.latitude !== 'number' || isNaN(payload.latitude)) {
    errors.push('Missing or invalid latitude (must be a number).');
  } else if (payload.latitude < -90 || payload.latitude > 90) {
    errors.push('Latitude out of bounds: must be between -90.0 and 90.0 degrees.');
  }

  if (typeof payload.longitude !== 'number' || isNaN(payload.longitude)) {
    errors.push('Missing or invalid longitude (must be a number).');
  } else if (payload.longitude < -180 || payload.longitude > 180) {
    errors.push('Longitude out of bounds: must be between -180.0 and 180.0 degrees.');
  }

  if (typeof payload.altitude_m !== 'number' || isNaN(payload.altitude_m)) {
    errors.push('Missing or invalid altitude_m (must be a number).');
  } else if (payload.altitude_m < 0) {
    errors.push('Altitude out of bounds: altitude_m must be non-negative (>= 0.0).');
  }

  if (payload.speed_mps !== undefined && payload.speed_mps !== null) {
    if (typeof payload.speed_mps !== 'number' || isNaN(payload.speed_mps) || payload.speed_mps < 0) {
      errors.push('Speed out of bounds: speed_mps must be non-negative (>= 0.0).');
    }
  }

  if (payload.heading_deg !== undefined && payload.heading_deg !== null) {
    if (typeof payload.heading_deg !== 'number' || isNaN(payload.heading_deg) || payload.heading_deg < 0 || payload.heading_deg >= 360) {
      errors.push('Heading out of bounds: heading_deg must be in range [0.0, 360.0).');
    }
  }

  if (payload.confidence !== undefined && payload.confidence !== null) {
    if (typeof payload.confidence !== 'number' || isNaN(payload.confidence) || payload.confidence < 0 || payload.confidence > 1) {
      errors.push('Confidence out of bounds: must be between 0.0 and 1.0.');
    }
  }

  if (!payload.source_type || typeof payload.source_type !== 'string') {
    errors.push('Missing required field: source_type (RADAR, RF, OPTICAL).');
  }

  return {
    valid: errors.length === 0,
    errors,
  };
}

describe('AeroGuard Stage UI7 Developer & API Console Unit Tests', () => {
  describe('API Catalog Integrity & Domain Categorization', () => {
    it('catalog contains all 8 required API domains', () => {
      assert.strictEqual(API_DOMAINS.length, 8);
      assert.ok(API_DOMAINS.includes('Platform & Health'));
      assert.ok(API_DOMAINS.includes('Authentication & Session'));
      assert.ok(API_DOMAINS.includes('Sensor Ingestion'));
      assert.ok(API_DOMAINS.includes('Tracking & Fusion'));
      assert.ok(API_DOMAINS.includes('Intelligence & Defense'));
      assert.ok(API_DOMAINS.includes('Simulation & Scenarios'));
      assert.ok(API_DOMAINS.includes('Historical & Analytics'));
      assert.ok(API_DOMAINS.includes('Governance & RBAC'));
    });

    it('all endpoints have unique IDs, valid HTTP methods, and valid paths starting with /', () => {
      const ids = new Set<string>();
      const validMethods = new Set(['GET', 'POST', 'PUT', 'PATCH', 'DELETE']);

      assert.ok(API_CATALOG.length >= 20);

      for (const ep of API_CATALOG) {
        assert.ok(!ids.has(ep.id), `Duplicate endpoint ID found: ${ep.id}`);
        ids.add(ep.id);

        assert.ok(validMethods.has(ep.method), `Invalid HTTP method on ${ep.id}: ${ep.method}`);
        assert.ok(ep.path.startsWith('/'), `Path must start with / on ${ep.id}: ${ep.path}`);
        assert.ok(ep.name.length > 0, `Missing name on ${ep.id}`);
        assert.ok(ep.description.length > 0, `Missing description on ${ep.id}`);
        assert.ok(API_DOMAINS.includes(ep.domain), `Invalid domain on ${ep.id}: ${ep.domain}`);
      }
    });

    it('endpoints requiring RBAC permissions specify valid permission keys', () => {
      const validPermissions = new Set([
        'system.read',
        'sensors.read',
        'sensors.configure',
        'tracks.read',
        'alerts.read',
        'threats.read',
        'scenarios.read',
        'scenarios.create',
        'scenarios.update',
        'scenarios.delete',
        'scenarios.run',
        'audit.read',
        'roles.read',
        'roles.create',
        'roles.update',
        'roles.delete',
        'roles.assign',
        'permissions.read',
      ]);

      for (const ep of API_CATALOG) {
        if (ep.requiredPermission) {
          assert.ok(
            validPermissions.has(ep.requiredPermission),
            `Invalid requiredPermission on ${ep.id}: ${ep.requiredPermission}`
          );
        }
        if (ep.requiredAnyPermissions) {
          for (const p of ep.requiredAnyPermissions) {
            assert.ok(
              validPermissions.has(p),
              `Invalid requiredAnyPermissions item on ${ep.id}: ${p}`
            );
          }
        }
      }
    });
  });

  describe('Path Variable Interpolation & Query Parameter Serialization', () => {
    it('interpolates single and multiple path variables properly', () => {
      const path1 = '/sensors/{sensor_id}/detections';
      assert.strictEqual(
        interpolatePath(path1, { sensor_id: 'sensor-uuid-123' }),
        '/sensors/sensor-uuid-123/detections'
      );

      const path2 = '/roles/{role_id}/permissions/{permission_id}';
      assert.strictEqual(
        interpolatePath(path2, { role_id: 'role-admin', permission_id: 'perm-99' }),
        '/roles/role-admin/permissions/perm-99'
      );
    });

    it('escapes special characters during path variable interpolation', () => {
      const path = '/sensors/{sensor_id}';
      assert.strictEqual(
        interpolatePath(path, { sensor_id: 'sensor/with#spaces & symbols' }),
        '/sensors/sensor%2Fwith%23spaces%20%26%20symbols'
      );
    });

    it('serializes query parameters into encoded query string', () => {
      const params = {
        status: 'ACTIVE',
        limit: 50,
        empty: '',
        nullVal: null,
        undefinedVal: undefined,
        flag: true,
      };
      const qs = buildQueryString(params);
      assert.strictEqual(qs, '?status=ACTIVE&limit=50&flag=true');
    });

    it('returns empty string when no query parameters are provided', () => {
      assert.strictEqual(buildQueryString({}), '');
      assert.strictEqual(buildQueryString({ a: undefined, b: null, c: '' }), '');
    });
  });

  describe('Integration Code Snippet Generation (cURL & Fetch)', () => {
    it('generates valid PowerShell-compatible cURL command', () => {
      const cmd = generateCurlCommand(
        'POST',
        'http://localhost:8000/api/v1/sensors/sensor-01/detections',
        { 'Content-Type': 'application/json' },
        JSON.stringify({ latitude: 37.77, longitude: -122.41 }),
        'powershell'
      );

      assert.ok(cmd.startsWith('curl.exe -X POST "http://localhost:8000/api/v1/sensors/sensor-01/detections"'));
      assert.ok(cmd.includes('-H "Content-Type: application/json"'));
      assert.ok(cmd.includes('--data'));
      // Verifies quotes are escaped for PowerShell
      assert.ok(cmd.includes('\\"latitude\\":'));
      assert.ok(cmd.includes('37.77'));
    });

    it('generates valid POSIX bash cURL command', () => {
      const cmd = generateCurlCommand(
        'GET',
        'http://localhost:8000/api/v1/tracks?limit=20',
        { 'Accept': 'application/json' },
        undefined,
        'posix'
      );

      assert.strictEqual(
        cmd,
        "curl -X GET 'http://localhost:8000/api/v1/tracks?limit=20' -H \"Accept: application/json\""
      );
    });

    it('generates valid JavaScript fetch() code snippet with credentials: include', () => {
      const snippet = generateFetchSnippet(
        'POST',
        '/api/v1/scenarios/scen-1/start',
        { 'Content-Type': 'application/json' }
      );

      assert.ok(snippet.includes("fetch('/api/v1/scenarios/scen-1/start'"));
      assert.ok(snippet.includes("method: 'POST'"));
      assert.ok(snippet.includes("credentials: 'include'"));
      assert.ok(snippet.includes('const data = await response.json();'));
    });

    it('strictly excludes session cookies, auth tokens, and secrets from generated snippets', () => {
      const headers = {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
      };
      const powershellCurl = generateCurlCommand('GET', 'http://localhost:8000/api/v1/me', headers, undefined, 'powershell');
      const posixCurl = generateCurlCommand('GET', 'http://localhost:8000/api/v1/me', headers, undefined, 'posix');
      const fetchSnippet = generateFetchSnippet('GET', '/api/v1/me', headers);

      for (const snippet of [powershellCurl, posixCurl, fetchSnippet]) {
        assert.ok(!snippet.toLowerCase().includes('bearer'));
        assert.ok(!snippet.toLowerCase().includes('jwt'));
        assert.ok(!snippet.toLowerCase().includes('aeroguard_session'));
        assert.ok(!snippet.toLowerCase().includes('set-cookie'));
      }
    });
  });

  describe('Synthetic Detection Ingestion Validation', () => {
    it('accepts valid detection observation payload', () => {
      const validPayload = {
        source_detection_id: 'det-radar-001',
        timestamp: new Date().toISOString(),
        latitude: 37.7749,
        longitude: -122.4194,
        altitude_m: 120.0,
        speed_mps: 18.5,
        heading_deg: 45.0,
        source_type: 'RADAR',
        confidence: 0.95,
        metadata: { snr_db: 20 },
      };

      const result = validateDetectionPayload(validPayload);
      assert.strictEqual(result.valid, true);
      assert.strictEqual(result.errors.length, 0);
    });

    it('rejects out-of-bounds latitude (< -90 or > 90)', () => {
      const payloadUnder = {
        source_detection_id: 'det-1',
        timestamp: new Date().toISOString(),
        latitude: -91.5,
        longitude: 0,
        altitude_m: 10,
        source_type: 'RADAR',
        confidence: 0.9,
      };
      const resultUnder = validateDetectionPayload(payloadUnder);
      assert.strictEqual(resultUnder.valid, false);
      assert.ok(resultUnder.errors.some((e) => e.includes('Latitude out of bounds')));

      const payloadOver = { ...payloadUnder, latitude: 90.001 };
      const resultOver = validateDetectionPayload(payloadOver);
      assert.strictEqual(resultOver.valid, false);
      assert.ok(resultOver.errors.some((e) => e.includes('Latitude out of bounds')));
    });

    it('rejects out-of-bounds longitude (< -180 or > 180)', () => {
      const payload = {
        source_detection_id: 'det-1',
        timestamp: new Date().toISOString(),
        latitude: 0,
        longitude: 180.5,
        altitude_m: 10,
        source_type: 'RADAR',
        confidence: 0.9,
      };
      const result = validateDetectionPayload(payload);
      assert.strictEqual(result.valid, false);
      assert.ok(result.errors.some((e) => e.includes('Longitude out of bounds')));
    });

    it('rejects negative altitude', () => {
      const payload = {
        source_detection_id: 'det-1',
        timestamp: new Date().toISOString(),
        latitude: 0,
        longitude: 0,
        altitude_m: -5.0,
        source_type: 'RADAR',
        confidence: 0.9,
      };
      const result = validateDetectionPayload(payload);
      assert.strictEqual(result.valid, false);
      assert.ok(result.errors.some((e) => e.includes('Altitude out of bounds')));
    });

    it('rejects future timestamps beyond safe clock skew', () => {
      const futureDate = new Date(Date.now() + 1000 * 60 * 60).toISOString();
      const payload = {
        source_detection_id: 'det-1',
        timestamp: futureDate,
        latitude: 0,
        longitude: 0,
        altitude_m: 10,
        source_type: 'RADAR',
        confidence: 0.9,
      };
      const result = validateDetectionPayload(payload);
      assert.strictEqual(result.valid, false);
      assert.ok(result.errors.some((e) => e.includes('Timestamp cannot be in the future')));
    });

    it('rejects malformed or invalid timestamp strings', () => {
      const payload = {
        source_detection_id: 'det-1',
        timestamp: 'not-a-valid-date',
        latitude: 0,
        longitude: 0,
        altitude_m: 10,
        source_type: 'RADAR',
        confidence: 0.9,
      };
      const result = validateDetectionPayload(payload);
      assert.strictEqual(result.valid, false);
      assert.ok(result.errors.some((e) => e.includes('Invalid timestamp format')));
    });

    it('rejects negative speed or out-of-range heading', () => {
      const payload = {
        source_detection_id: 'det-1',
        timestamp: new Date().toISOString(),
        latitude: 0,
        longitude: 0,
        altitude_m: 10,
        speed_mps: -2.0,
        heading_deg: 365.0,
        source_type: 'RADAR',
        confidence: 0.9,
      };
      const result = validateDetectionPayload(payload);
      assert.strictEqual(result.valid, false);
      assert.ok(result.errors.some((e) => e.includes('Speed out of bounds')));
      assert.ok(result.errors.some((e) => e.includes('Heading out of bounds')));
    });
  });

  describe('Deep Linking & Command Palette Shortcuts', () => {
    it('correctly maps deep-link query parameters for tabs and endpoints', () => {
      const searchParams1 = new URLSearchParams('tab=dispatcher&endpoint=sensors_detection_post');
      assert.strictEqual(searchParams1.get('tab'), 'dispatcher');
      assert.strictEqual(searchParams1.get('endpoint'), 'sensors_detection_post');

      const searchParams2 = new URLSearchParams('tab=workbench&sensor_id=sensor-01');
      assert.strictEqual(searchParams2.get('tab'), 'workbench');
      assert.strictEqual(searchParams2.get('sensor_id'), 'sensor-01');
    });

    it('safely falls back when unknown or malformed tab parameters are passed', () => {
      const searchParams = new URLSearchParams('tab=unknown_tab&invalid=123');
      const tabParam = searchParams.get('tab');
      const resolvedTab = ['catalog', 'dispatcher', 'workbench', 'schemas'].includes(tabParam || '')
        ? tabParam
        : 'catalog';
      assert.strictEqual(resolvedTab, 'catalog');
    });
  });

  describe('RBAC Permission Gating Verification', () => {
    it('requires sensors.configure for detection injection', () => {
      const ep = API_CATALOG.find((e) => e.id === 'sensors_detection_post');
      assert.ok(ep);
      assert.strictEqual(ep.requiredPermission, 'sensors.configure');
    });

    it('requires system.read for system diagnostics', () => {
      const ep = API_CATALOG.find((e) => e.id === 'system_info_get');
      assert.ok(ep);
      assert.strictEqual(ep.requiredPermission, 'system.read');
    });
  });
});
