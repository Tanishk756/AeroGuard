import React from 'react';
import { useDesktopEnvironment } from '../../hooks/useDesktopEnvironment';

export const DesktopTitlebar: React.FC = () => {
  const { isMaximized, isOnline, minimize, toggleMaximize, close } = useDesktopEnvironment();

  return (
    <header
      data-tauri-drag-region
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '32px',
        backgroundColor: '#0a0e17',
        borderBottom: '1px solid var(--border-subtle, #1e293b)',
        userSelect: 'none',
        WebkitUserSelect: 'none',
        zIndex: 9999,
        paddingLeft: 'var(--space-sm, 8px)',
        paddingRight: '0px',
        fontSize: '11px',
        fontFamily: 'monospace',
      }}
    >
      {/* Left: Branding & Status Indicator */}
      <div
        data-tauri-drag-region
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: 'var(--space-sm, 8px)',
          cursor: 'default',
        }}
      >
        <span style={{ fontSize: '13px' }}>🛡️</span>
        <span
          style={{
            fontWeight: 700,
            letterSpacing: '0.08em',
            color: 'var(--text-primary, #f8fafc)',
            textTransform: 'uppercase',
          }}
        >
          AeroGuard
        </span>
        <span style={{ color: 'var(--text-muted, #64748b)' }}>|</span>
        <span style={{ color: 'var(--text-muted, #94a3b8)' }}>Operator Console</span>

        <span
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '4px',
            marginLeft: '8px',
            padding: '1px 6px',
            borderRadius: '4px',
            backgroundColor: isOnline ? 'rgba(16, 185, 129, 0.1)' : 'rgba(244, 63, 94, 0.1)',
            color: isOnline ? 'var(--status-normal, #10b981)' : 'var(--status-critical, #f43f5e)',
            fontSize: '10px',
            fontWeight: 600,
          }}
        >
          <span
            style={{
              display: 'inline-block',
              width: '6px',
              height: '6px',
              borderRadius: '50%',
              backgroundColor: isOnline ? '#10b981' : '#f43f5e',
            }}
          />
          {isOnline ? 'ONLINE' : 'OFFLINE'}
        </span>
      </div>

      {/* Center: Draggable Spacer */}
      <div data-tauri-drag-region style={{ flex: 1, height: '100%' }} />

      {/* Right: Window Controls */}
      <div style={{ display: 'flex', height: '100%' }}>
        <button
          type="button"
          onClick={minimize}
          aria-label="Minimize Window"
          title="Minimize Window"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '42px',
            height: '100%',
            backgroundColor: 'transparent',
            border: 'none',
            color: 'var(--text-muted, #94a3b8)',
            cursor: 'pointer',
            fontSize: '12px',
            transition: 'background-color 0.15s ease, color 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)';
            e.currentTarget.style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--text-muted, #94a3b8)';
          }}
        >
          🗕
        </button>

        <button
          type="button"
          onClick={toggleMaximize}
          aria-label={isMaximized ? 'Restore Window' : 'Maximize Window'}
          title={isMaximized ? 'Restore Window' : 'Maximize Window'}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '42px',
            height: '100%',
            backgroundColor: 'transparent',
            border: 'none',
            color: 'var(--text-muted, #94a3b8)',
            cursor: 'pointer',
            fontSize: '11px',
            transition: 'background-color 0.15s ease, color 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = 'rgba(255, 255, 255, 0.08)';
            e.currentTarget.style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--text-muted, #94a3b8)';
          }}
        >
          {isMaximized ? '🗗' : '🗖'}
        </button>

        <button
          type="button"
          onClick={close}
          aria-label="Close Application"
          title="Close Application"
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            justifyContent: 'center',
            width: '46px',
            height: '100%',
            backgroundColor: 'transparent',
            border: 'none',
            color: 'var(--text-muted, #94a3b8)',
            cursor: 'pointer',
            fontSize: '12px',
            transition: 'background-color 0.15s ease, color 0.15s ease',
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.backgroundColor = '#e11d48';
            e.currentTarget.style.color = '#fff';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.backgroundColor = 'transparent';
            e.currentTarget.style.color = 'var(--text-muted, #94a3b8)';
          }}
        >
          ✕
        </button>
      </div>
    </header>
  );
};
