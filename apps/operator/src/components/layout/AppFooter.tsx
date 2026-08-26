import React from 'react';
import { useSystem } from '../../context/SystemContext';

export const AppFooter: React.FC = () => {
  const { isHealthy, isDbHealthy, systemInfo } = useSystem();

  return (
    <footer
      style={{
        height: '26px',
        backgroundColor: 'var(--bg-canvas)',
        borderTop: '1px solid var(--border-subtle)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: '0 var(--space-md)',
        fontSize: '11px',
        color: 'var(--text-muted)',
        userSelect: 'none',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <span className="font-mono">
          STATUS: <span style={{ color: isHealthy && isDbHealthy ? 'var(--status-success)' : 'var(--status-warning)' }}>{isHealthy && isDbHealthy ? 'CONNECTED' : 'DISCONNECTED'}</span>
        </span>
        <span className="font-mono">
          DB: <span style={{ color: isDbHealthy ? 'var(--status-success)' : 'var(--status-critical)' }}>{isDbHealthy ? 'OPERATIONAL' : 'OFFLINE'}</span>
        </span>
        {systemInfo && (
          <span className="font-mono">
            VER: {systemInfo.version} ({systemInfo.environment})
          </span>
        )}
      </div>

      <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
        <span style={{ letterSpacing: '0.04em' }}>
          AeroGuard Defensive Research & Counter-UAS Awareness Platform
        </span>
      </div>
    </footer>
  );
};
