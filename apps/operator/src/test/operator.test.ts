import assert from 'node:assert';
import test, { describe, it } from 'node:test';

describe('AeroGuard Operator Console Frontend Unit Tests', () => {
  describe('RBAC Permission Helpers', () => {
    const mockUser = {
      id: 'usr-1',
      username: 'operator',
      display_name: 'Operator Alpha',
      email: 'operator@aeroguard.local',
      status: 'ACTIVE' as const,
      roles: ['OPERATOR'],
      permissions: ['tracks.read', 'alerts.read', 'sensors.read'],
      created_at: '2026-08-26T00:00:00Z',
      updated_at: '2026-08-26T00:00:00Z',
    };

    const hasPermission = (user: typeof mockUser | null, perm: string): boolean => {
      if (!user) return false;
      return user.permissions.includes(perm);
    };

    const hasAnyPermission = (user: typeof mockUser | null, perms: string[]): boolean => {
      if (!user) return false;
      return perms.some((p) => user.permissions.includes(p));
    };

    const hasRole = (user: typeof mockUser | null, role: string): boolean => {
      if (!user) return false;
      return user.roles.includes(role);
    };

    it('correctly evaluates granted permissions', () => {
      assert.strictEqual(hasPermission(mockUser, 'tracks.read'), true);
      assert.strictEqual(hasPermission(mockUser, 'alerts.read'), true);
      assert.strictEqual(hasPermission(mockUser, 'threats.read'), false);
    });

    it('correctly evaluates hasAnyPermission', () => {
      assert.strictEqual(hasAnyPermission(mockUser, ['threats.read', 'tracks.read']), true);
      assert.strictEqual(hasAnyPermission(mockUser, ['threats.read', 'scenarios.run']), false);
    });

    it('correctly checks assigned roles', () => {
      assert.strictEqual(hasRole(mockUser, 'OPERATOR'), true);
      assert.strictEqual(hasRole(mockUser, 'SUPER_ADMIN'), false);
    });

    it('returns false for unauthenticated user across all checks', () => {
      assert.strictEqual(hasPermission(null, 'tracks.read'), false);
      assert.strictEqual(hasAnyPermission(null, ['tracks.read']), false);
      assert.strictEqual(hasRole(null, 'OPERATOR'), false);
    });
  });

  describe('API URL & Query Parameter Serialization', () => {
    const buildUrl = (endpoint: string, params?: Record<string, string | number | boolean | undefined | null>) => {
      let url = endpoint.startsWith('/') ? `/api/v1${endpoint}` : `/api/v1/${endpoint}`;
      if (params) {
        const searchParams = new URLSearchParams();
        for (const [key, value] of Object.entries(params)) {
          if (value !== undefined && value !== null && value !== '') {
            searchParams.append(key, String(value));
          }
        }
        const queryString = searchParams.toString();
        if (queryString) {
          url += (url.includes('?') ? '&' : '?') + queryString;
        }
      }
      return url;
    };

    it('formats basic endpoints without params', () => {
      assert.strictEqual(buildUrl('/tracks'), '/api/v1/tracks');
      assert.strictEqual(buildUrl('sensors'), '/api/v1/sensors');
    });

    it('serializes non-empty query parameters', () => {
      const url = buildUrl('/tracks', { state: 'ACTIVE', limit: 50, offset: 0, classification: undefined });
      assert.strictEqual(url, '/api/v1/tracks?state=ACTIVE&limit=50&offset=0');
    });

    it('omits undefined, null, and empty string params', () => {
      const url = buildUrl('/alerts', { status: 'OPEN', severity: '', track_id: null });
      assert.strictEqual(url, '/api/v1/alerts?status=OPEN');
    });
  });

  describe('Status Badge Semantic Mapping', () => {
    const getBadgeVariant = (status: string) => {
      const norm = (status || 'UNKNOWN').toUpperCase();
      switch (norm) {
        case 'ACTIVE':
        case 'NORMAL':
        case 'OK':
        case 'RESOLVED':
          return 'status-success';
        case 'WARNING':
        case 'STALE':
        case 'MEDIUM':
        case 'ACKNOWLEDGED':
        case 'DEGRADED':
          return 'status-warning';
        case 'CRITICAL':
        case 'HIGH':
        case 'LOST':
        case 'OPEN':
        case 'ERROR':
          return 'status-critical';
        case 'INFO':
        case 'SIMULATION':
        case 'NEW':
        case 'LOW':
          return 'status-info';
        case 'OFFLINE':
        case 'INACTIVE':
        case 'ARCHIVED':
        case 'MAINTENANCE':
        default:
          return 'status-offline';
      }
    };

    it('maps positive operational states to success', () => {
      assert.strictEqual(getBadgeVariant('ACTIVE'), 'status-success');
      assert.strictEqual(getBadgeVariant('RESOLVED'), 'status-success');
    });

    it('maps warnings and degraded states', () => {
      assert.strictEqual(getBadgeVariant('WARNING'), 'status-warning');
      assert.strictEqual(getBadgeVariant('STALE'), 'status-warning');
      assert.strictEqual(getBadgeVariant('DEGRADED'), 'status-warning');
    });

    it('maps critical, high, and open errors', () => {
      assert.strictEqual(getBadgeVariant('CRITICAL'), 'status-critical');
      assert.strictEqual(getBadgeVariant('HIGH'), 'status-critical');
      assert.strictEqual(getBadgeVariant('LOST'), 'status-critical');
      assert.strictEqual(getBadgeVariant('OPEN'), 'status-critical');
    });

    it('defaults unknown and offline to status-offline', () => {
      assert.strictEqual(getBadgeVariant('OFFLINE'), 'status-offline');
      assert.strictEqual(getBadgeVariant('UNKNOWN'), 'status-offline');
    });
  });

  describe('Error Handling & Classification', () => {
    const classifyErrorStatus = (status: number) => {
      if (status === 401) return 'UNAUTHENTICATED';
      if (status === 403) return 'FORBIDDEN';
      if (status === 404) return 'NOT_FOUND';
      if (status >= 500) return 'SERVER_ERROR';
      if (status === 0) return 'NETWORK_ERROR';
      return 'CLIENT_ERROR';
    };

    it('classifies 401 as unauthenticated', () => {
      assert.strictEqual(classifyErrorStatus(401), 'UNAUTHENTICATED');
    });

    it('classifies 403 as forbidden', () => {
      assert.strictEqual(classifyErrorStatus(403), 'FORBIDDEN');
    });

    it('classifies 404 as not found', () => {
      assert.strictEqual(classifyErrorStatus(404), 'NOT_FOUND');
    });

    it('classifies 500 and 503 as server error', () => {
      assert.strictEqual(classifyErrorStatus(500), 'SERVER_ERROR');
      assert.strictEqual(classifyErrorStatus(503), 'SERVER_ERROR');
    });

    it('classifies 0 as network error', () => {
      assert.strictEqual(classifyErrorStatus(0), 'NETWORK_ERROR');
    });
  });
});
