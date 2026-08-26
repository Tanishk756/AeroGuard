import React, { useEffect, useState } from 'react';
import { useAuth } from '../../context/AuthContext';
import { useSystem } from '../../context/SystemContext';
import { CommandPalette } from '../command/CommandPalette';
import { Button } from '../common/Button';
import { StatusBadge } from '../common/StatusBadge';

export const AppHeader: React.FC = () => {
  const { user, logout } = useAuth();
  const { isHealthy, isDbHealthy } = useSystem();
  const [utcTime, setUtcTime] = useState<string>('');
  const [isCommandPaletteOpen, setIsCommandPaletteOpen] = useState<boolean>(false);

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setUtcTime(now.toISOString().substring(11, 19) + ' UTC');
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  // Global Keyboard shortcut listener for Command Palette (Ctrl+K, Cmd+K, /)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const activeElement = document.activeElement;
      const isInput =
        activeElement &&
        (activeElement.tagName === 'INPUT' ||
          activeElement.tagName === 'TEXTAREA' ||
          activeElement.tagName === 'SELECT' ||
          (activeElement as HTMLElement).isContentEditable);

      if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
        e.preventDefault();
        setIsCommandPaletteOpen((prev) => !prev);
      } else if (e.key === '/' && !isInput) {
        e.preventDefault();
        setIsCommandPaletteOpen(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const primaryRole = user?.roles?.[0] || 'VIEWER';

  return (
    <>
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

        {/* Command Palette Trigger & System Telemetry */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          {/* Quick Command Trigger Button */}
          <button
            onClick={() => setIsCommandPaletteOpen(true)}
            className="tactical-btn font-mono"
            style={{
              padding: '3px 10px',
              fontSize: '11px',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              backgroundColor: 'var(--bg-canvas)',
              color: 'var(--text-secondary)',
              border: '1px solid var(--border-subtle)',
            }}
            title="Open Command Palette (Ctrl+K or /)"
          >
            <span>⌘ Command Hub</span>
            <kbd
              style={{
                fontSize: '9px',
                padding: '1px 4px',
                backgroundColor: 'var(--bg-surface)',
                borderRadius: '2px',
                border: '1px solid var(--border-medium)',
                color: 'var(--text-muted)',
              }}
            >
              Ctrl+K
            </kbd>
          </button>

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

      {/* Global Command Palette Modal */}
      <CommandPalette
        isOpen={isCommandPaletteOpen}
        onClose={() => setIsCommandPaletteOpen(false)}
      />
    </>
  );
};
