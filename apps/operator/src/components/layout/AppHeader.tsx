import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useSystem } from '../../context/SystemContext';
import { Button } from '../common/Button';
import { StatusBadge } from '../common/StatusBadge';

export const AppHeader: React.FC = () => {
  const { user, logout } = useAuth();
  const { isHealthy, isDbHealthy } = useSystem();
  const [utcTime, setUtcTime] = useState<string>('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const primaryRole = user?.roles?.[0] || 'VIEWER';

  return (
    <header
      style={{
        height: '48px',
        backgroundColor: 'var(--bg-surface)',
        borderBottom: '1px solid var(--border-medium)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--space-md)',
        zIndex: 50,
      }}
    >
      {/* Brand Identity */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span
            style={{
              width: '10px',
              height: '10px',
              backgroundColor: 'var(--color-accent)',
              borderRadius: '2px',
              display: 'inline-block',
            }}
          />
          <span
            style={{
              fontSize: 'var(--text-base)',
              fontWeight: 700,
              letterSpacing: '0.12em',
              color: 'var(--text-primary)',
              textTransform: 'uppercase',
            }}
          >
            AEROGUARD
          </span>
          <span
            style={{
              fontSize: 'var(--text-xs)',
              color: 'var(--text-muted)',
              borderLeft: '1px solid var(--border-medium)',
              paddingLeft: '8px',
              letterSpacing: '0.06em',
            }}
          >
            OPERATOR CONSOLE
          </span>
        </div>
      </div>

      {/* System Telemetry & UTC Clock */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', fontSize: 'var(--text-xs)' }}>
          <span className="text-muted font-mono">SYS:</span>
          <StatusBadge status={isHealthy && isDbHealthy ? 'ACTIVE' : 'WARNING'} label={isHealthy && isDbHealthy ? 'ONLINE' : 'DEGRADED'} />
        </div>

        <div
          className="font-mono text-xs"
          style={{
            backgroundColor: 'var(--bg-canvas)',
            padding: '3px 8px',
            borderRadius: 'var(--radius-sm)',
            border: '1px solid var(--border-subtle)',
            color: 'var(--color-accent)',
            letterSpacing: '0.05em',
          }}
        >
          {utcTime || '00:00:00 UTC'}
        </div>
      </div>

      {/* User Context & Logout */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        {user ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
            <div style={{ textAlign: 'right', display: 'flex', flexDirection: 'column' }}>
              <span style={{ fontSize: 'var(--text-xs)', fontWeight: 600, color: 'var(--text-primary)' }}>
                {user.display_name || user.username}
              </span>
              <span
                className="font-mono"
                style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}
              >
                ROLE: {primaryRole}
              </span>
            </div>

            <Button
              variant="ghost"
              size="sm"
              onClick={logout}
              title="Sign out of operator session"
              style={{ fontSize: 'var(--text-xs)', padding: '3px 8px' }}
            >
              Sign Out
            </Button>
          </div>
        ) : (
          <span className="text-muted text-xs">Unauthenticated</span>
        )}
      </div>
    </header>
  );
};
