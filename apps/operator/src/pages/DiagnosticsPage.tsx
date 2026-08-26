import React, { useCallback, useEffect, useState } from 'react';
import { getHealth, getSystemInfo } from '../api/system';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { useAuth } from '../context/AuthContext';
import { SystemHealthResponse, SystemInfoResponse } from '../types';

export const DiagnosticsPage: React.FC = () => {
  const { user } = useAuth();
  const [health, setHealth] = useState<SystemHealthResponse | null>(null);
  const [info, setInfo] = useState<SystemInfoResponse | null>(null);
  const [lastChecked, setLastChecked] = useState<Date | null>(null);
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDiagnostics = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [healthRes, infoRes] = await Promise.all([
        getHealth().catch(() => ({ status: 'unhealthy', application: 'AeroGuard', version: '0.1.0', database: 'unhealthy' })),
        getSystemInfo().catch((err) => {
          throw err;
        }),
      ]);
      setHealth(healthRes);
      setInfo(infoRes);
      setLastChecked(new Date());
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query system diagnostics');
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchDiagnostics();
  }, [fetchDiagnostics]);

  const isDbHealthy = health?.database === 'healthy';
  const isSysHealthy = health?.status === 'healthy';

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--status-info)', borderRadius: '1px' }} />
            <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
              Platform Diagnostics & System Health
            </h1>
          </div>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Runtime specifications, database connectivity verification, and active session telemetry.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          {lastChecked && (
            <span className="font-mono text-xs text-muted">
              POLL: {lastChecked.toISOString().substring(11, 19)} UTC
            </span>
          )}
          <Button variant="secondary" size="sm" onClick={fetchDiagnostics} isLoading={isLoading}>
            Run Diagnostic Poll
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchDiagnostics} />}

      {isLoading && !info ? (
        <LoadingState message="Querying platform diagnostics and database connectivity..." />
      ) : (
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {/* Top Status Telemetry KPI Grid */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: 'var(--space-sm)' }}>
            <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
              <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>System Operational Health</div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
                <span className="font-mono" style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>
                  {health?.status ? health.status.toUpperCase() : 'UNKNOWN'}
                </span>
                <StatusBadge status={isSysHealthy ? 'ACTIVE' : 'CRITICAL'} label={isSysHealthy ? 'ONLINE' : 'DEGRADED'} />
              </div>
            </Card>

            <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
              <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Database Connectivity (SELECT 1)</div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
                <span className="font-mono" style={{ fontSize: 'var(--text-lg)', fontWeight: 700 }}>
                  {health?.database ? health.database.toUpperCase() : 'UNKNOWN'}
                </span>
                <StatusBadge status={isDbHealthy ? 'ACTIVE' : 'CRITICAL'} label={isDbHealthy ? 'CONNECTED' : 'DISCONNECTED'} />
              </div>
            </Card>

            <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
              <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Application Version</div>
              <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
                <span className="font-mono" style={{ fontSize: 'var(--text-lg)', fontWeight: 700, color: 'var(--color-accent)' }}>
                  v{info?.version || '0.1.0'}
                </span>
                <span className="font-mono text-xs text-muted">{info?.environment?.toUpperCase() || 'PROD'}</span>
              </div>
            </Card>
          </div>

          {/* Detailed Platform & Runtime Inspection */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 'var(--space-md)' }}>
            {/* Runtime Specifications */}
            <Card title="Backend Runtime Specifications">
              {info ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
                  <div className="kv-row">
                    <span className="kv-key">Application</span>
                    <span className="kv-value font-mono">{info.application}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Version</span>
                    <span className="kv-value font-mono">v{info.version}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Environment</span>
                    <span className="kv-value font-mono uppercase-tracking">{info.environment}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Debug Mode</span>
                    <span className="kv-value font-mono">{info.debug ? 'ENABLED' : 'DISABLED'}</span>
                  </div>
                  <div className="kv-row" style={{ gridColumn: '1 / -1' }}>
                    <span className="kv-key">Python Engine</span>
                    <span className="kv-value font-mono text-xs">{info.python_version}</span>
                  </div>
                  <div className="kv-row" style={{ gridColumn: '1 / -1' }}>
                    <span className="kv-key">Platform Architecture</span>
                    <span className="kv-value font-mono text-xs text-muted" style={{ wordBreak: 'break-all' }}>
                      {info.platform}
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-muted text-xs">Runtime information not available.</p>
              )}
            </Card>

            {/* Active Session Identity */}
            <Card title="Active Operator Session Identity">
              {user ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
                  <div className="kv-row">
                    <span className="kv-key">Username</span>
                    <span className="kv-value font-mono" style={{ fontWeight: 600, color: 'var(--color-accent)' }}>
                      {user.username}
                    </span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Display Name</span>
                    <span className="kv-value">{user.display_name || user.username}</span>
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">Account Status</span>
                    <StatusBadge status={user.status === 'ACTIVE' ? 'ACTIVE' : 'CRITICAL'} label={user.status} />
                  </div>
                  <div className="kv-row">
                    <span className="kv-key">User ID</span>
                    <span className="kv-value font-mono text-xs text-muted" title={user.id}>
                      {user.id.length > 14 ? `${user.id.substring(0, 14)}...` : user.id}
                    </span>
                  </div>
                  <div className="kv-row" style={{ gridColumn: '1 / -1' }}>
                    <span className="kv-key">Assigned Roles</span>
                    <div style={{ display: 'flex', flexWrap: 'wrap', gap: '4px', marginTop: '2px' }}>
                      {user.roles.map((r) => (
                        <span
                          key={r}
                          className="font-mono text-xs"
                          style={{
                            padding: '2px 6px',
                            backgroundColor: 'var(--bg-canvas)',
                            border: '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          {r}
                        </span>
                      ))}
                    </div>
                  </div>
                  <div className="kv-row" style={{ gridColumn: '1 / -1' }}>
                    <span className="kv-key">Authority Count</span>
                    <span className="kv-value font-mono text-xs">
                      {user.permissions.length} granular permissions granted
                    </span>
                  </div>
                </div>
              ) : (
                <p className="text-muted text-xs">Unauthenticated session.</p>
              )}
            </Card>
          </div>

          {/* Security & Confidentiality Notice */}
          <div
            style={{
              padding: '8px 12px',
              backgroundColor: 'var(--bg-surface)',
              border: '1px solid var(--border-subtle)',
              borderRadius: 'var(--radius-sm)',
            }}
          >
            <p className="font-mono text-muted" style={{ margin: 0, fontSize: '11px', lineHeight: 1.4 }}>
              🔒 <strong>Confidentiality Notice</strong>: Diagnostics reflect live server environment properties. Secrets, database connection strings, environment secrets, and credential keys are strictly omitted from diagnostic outputs per AeroGuard security rules.
            </p>
          </div>
        </div>
      )}
    </div>
  );
};
