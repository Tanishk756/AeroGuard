import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';

export interface CommandItem {
  id: string;
  label: string;
  category: 'Navigation' | 'Tactical Map' | 'Operations' | 'Workspace' | 'Analytics' | 'Developer';
  shortcut?: string;
  icon?: string;
  action: () => void;
}

interface CommandPaletteProps {
  isOpen: boolean;
  onClose: () => void;
  onFitMap?: () => void;
  onResetMap?: () => void;
  onRefreshData?: () => void;
  onClearSelection?: () => void;
  onToggleInspector?: () => void;
}

export const CommandPalette: React.FC<CommandPaletteProps> = ({
  isOpen,
  onClose,
  onFitMap,
  onResetMap,
  onRefreshData,
  onClearSelection,
  onToggleInspector,
}) => {
  const navigate = useNavigate();
  const [query, setQuery] = useState('');
  const [selectedIndex, setSelectedIndex] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const listRef = useRef<HTMLDivElement>(null);

  const commands: CommandItem[] = [
    {
      id: 'nav-overview',
      label: 'Go to Overview Workspace',
      category: 'Navigation',
      shortcut: 'g o',
      icon: '⊞',
      action: () => navigate('/app/overview'),
    },
    {
      id: 'nav-tracks',
      label: 'Go to Track Management',
      category: 'Navigation',
      shortcut: 'g t',
      icon: '◎',
      action: () => navigate('/app/tracks'),
    },
    {
      id: 'nav-sensors',
      label: 'Go to Sensor Inventory',
      category: 'Navigation',
      shortcut: 'g s',
      icon: '⋉',
      action: () => navigate('/app/sensors'),
    },
    {
      id: 'nav-alerts',
      label: 'Go to Operational Alerts',
      category: 'Navigation',
      shortcut: 'g a',
      icon: '▲',
      action: () => navigate('/app/alerts'),
    },
    {
      id: 'nav-threats',
      label: 'Go to Threat Triage',
      category: 'Navigation',
      shortcut: 'g h',
      icon: '⚡',
      action: () => navigate('/app/threats'),
    },
    {
      id: 'nav-geofences',
      label: 'Go to Defense Zones Studio',
      category: 'Navigation',
      shortcut: 'g z',
      icon: '⛊',
      action: () => navigate('/app/geofences'),
    },
    {
      id: 'nav-scenarios',
      label: 'Go to Scenario Simulation Hub',
      category: 'Navigation',
      shortcut: 'g c',
      icon: '⚙',
      action: () => navigate('/app/scenarios'),
    },
    {
      id: 'nav-replay',
      label: 'Go to Replay Analysis',
      category: 'Navigation',
      shortcut: 'g r',
      icon: '⏯',
      action: () => navigate('/app/replay'),
    },
    {
      id: 'nav-history',
      label: 'Go to Historical Logs',
      category: 'Navigation',
      shortcut: 'g l',
      icon: '◷',
      action: () => navigate('/app/history'),
    },
    {
      id: 'nav-analytics',
      label: 'Go to Operational Analytics',
      category: 'Navigation',
      shortcut: 'g y',
      icon: '📊',
      action: () => navigate('/app/analytics'),
    },
    // Analytics shortcuts (non-colliding)
    {
      id: 'analytics-dashboard',
      label: 'Analytics Dashboard',
      category: 'Analytics',
      shortcut: 'a',
      icon: '📈',
      action: () => navigate('/app/analytics'),
    },
    {
      id: 'analytics-tracks',
      label: 'Tracks Analytics',
      category: 'Analytics',
      shortcut: 'a t',
      icon: '⧭',
      action: () => navigate('/app/analytics?view=tracks'),
    },
    {
      id: 'analytics-alerts',
      label: 'Alerts Analytics',
      category: 'Analytics',
      shortcut: 'a a',
      icon: '⚠',
      action: () => navigate('/app/analytics?view=alerts'),
    },
    {
      id: 'analytics-threats',
      label: 'Threats Analytics',
      category: 'Analytics',
      shortcut: 'a h',
      icon: '⚡',
      action: () => navigate('/app/analytics?view=threats'),
    },
    {
      id: 'analytics-detections',
      label: 'Detections Analytics',
      category: 'Analytics',
      shortcut: 'a d',
      icon: '🔍',
      action: () => navigate('/app/analytics?view=detections'),
    },
    {
      id: 'nav-audit',
      label: 'Go to Security Audit Explorer',
      category: 'Navigation',
      shortcut: 'g u',
      icon: '🔒',
      action: () => navigate('/app/audit'),
    },
    {
      id: 'nav-rbac',
      label: 'Go to RBAC Role Governance',
      category: 'Navigation',
      shortcut: 'g k',
      icon: '🛡',
      action: () => navigate('/app/rbac'),
    },
    {
      id: 'nav-diagnostics',
      label: 'Go to System Platform Diagnostics',
      category: 'Navigation',
      shortcut: 'g d',
      icon: '🩺',
      action: () => navigate('/app/diagnostics'),
    },
    {
      id: 'nav-developer',
      label: 'Go to Developer & API Console',
      category: 'Navigation',
      shortcut: 'g e',
      icon: '⚡',
      action: () => navigate('/app/developer'),
    },
    {
      id: 'dev-dispatcher',
      label: 'Open Interactive API Request Dispatcher',
      category: 'Developer',
      icon: '⚡',
      action: () => navigate('/app/developer?tab=dispatcher'),
    },
    {
      id: 'dev-workbench',
      label: 'Open Synthetic Sensor Ingestion Workbench',
      category: 'Developer',
      icon: '🛰️',
      action: () => navigate('/app/developer?tab=workbench'),
    },
    {
      id: 'dev-schemas',
      label: 'Open Data Contract & Pydantic Schema Viewer',
      category: 'Developer',
      icon: '📋',
      action: () => navigate('/app/developer?tab=schemas'),
    },
    {
      id: 'map-fit',
      label: 'Fit Tactical Map to All Entities',
      category: 'Tactical Map',
      shortcut: 'f',
      icon: '⛶',
      action: () => onFitMap?.(),
    },
    {
      id: 'map-reset',
      label: 'Reset Tactical Map View Center',
      category: 'Tactical Map',
      shortcut: 'c',
      icon: '⊙',
      action: () => onResetMap?.(),
    },
    {
      id: 'ops-refresh',
      label: 'Refresh Operational Telemetry Data',
      category: 'Operations',
      shortcut: 'r',
      icon: '↻',
      action: () => onRefreshData?.(),
    },
    {
      id: 'ws-inspector',
      label: 'Toggle Workspace Inspector Panel',
      category: 'Workspace',
      shortcut: 'i',
      icon: '⇤',
      action: () => onToggleInspector?.(),
    },
    {
      id: 'ws-clear',
      label: 'Clear Active Entity Selection',
      category: 'Workspace',
      shortcut: 'Esc',
      icon: '✕',
      action: () => onClearSelection?.(),
    },
  ];

  const filtered = commands.filter((cmd) => {
    if (!query.trim()) return true;
    const q = query.toLowerCase();
    return (
      cmd.label.toLowerCase().includes(q) ||
      cmd.category.toLowerCase().includes(q) ||
      (cmd.shortcut && cmd.shortcut.toLowerCase().includes(q))
    );
  });

  useEffect(() => {
    if (isOpen) {
      setQuery('');
      setSelectedIndex(0);
      setTimeout(() => inputRef.current?.focus(), 50);
    }
  }, [isOpen]);

  useEffect(() => {
    setSelectedIndex(0);
  }, [query]);

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    } else if (e.key === 'ArrowDown') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev + 1) % Math.max(1, filtered.length));
    } else if (e.key === 'ArrowUp') {
      e.preventDefault();
      setSelectedIndex((prev) => (prev - 1 + filtered.length) % Math.max(1, filtered.length));
    } else if (e.key === 'Enter') {
      e.preventDefault();
      if (filtered[selectedIndex]) {
        filtered[selectedIndex].action();
        onClose();
      }
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label="Mission Command Palette"
      onClick={onClose}
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 12, 0.75)',
        backdropFilter: 'blur(2px)',
        zIndex: 9999,
        display: 'flex',
        alignItems: 'flex-start',
        justifyContent: 'center',
        paddingTop: '12vh',
      }}
    >
      <div
        onClick={(e) => e.stopPropagation()}
        onKeyDown={handleKeyDown}
        style={{
          width: '100%',
          maxWidth: '560px',
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          overflow: 'hidden',
          display: 'flex',
          flexDirection: 'column',
        }}
      >
        {/* Search Header Input */}
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            gap: '8px',
            padding: '10px 14px',
            borderBottom: '1px solid var(--border-medium)',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
          <span style={{ color: 'var(--color-accent)', fontSize: '14px' }}>⌘</span>
          <input
            ref={inputRef}
            type="text"
            className="tactical-input"
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Type a command or jump to subsystem (e.g. tracks, map, fit)..."
            style={{
              border: 'none',
              backgroundColor: 'transparent',
              padding: '4px',
              fontSize: 'var(--text-sm)',
              outline: 'none',
              boxShadow: 'none',
              width: '100%',
            }}
          />
          <span className="font-mono text-xs text-muted" style={{ padding: '2px 6px', backgroundColor: 'var(--bg-canvas)', borderRadius: '3px' }}>
            ESC to close
          </span>
        </div>

        {/* Results List */}
        <div
          ref={listRef}
          style={{
            maxHeight: '340px',
            overflowY: 'auto',
            padding: '6px',
            display: 'flex',
            flexDirection: 'column',
            gap: '2px',
          }}
        >
          {filtered.length === 0 ? (
            <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
              No matching commands found.
            </div>
          ) : (
            filtered.map((cmd, idx) => {
              const isSelected = idx === selectedIndex;
              return (
                <div
                  key={cmd.id}
                  onClick={() => {
                    cmd.action();
                    onClose();
                  }}
                  onMouseEnter={() => setSelectedIndex(idx)}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    padding: '8px 10px',
                    borderRadius: 'var(--radius-sm)',
                    backgroundColor: isSelected ? 'var(--bg-surface-active)' : 'transparent',
                    borderLeft: isSelected ? '3px solid var(--color-accent)' : '3px solid transparent',
                    cursor: 'pointer',
                    transition: 'all var(--transition-fast)',
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                    <span style={{ fontSize: '14px', width: '16px', textAlign: 'center', color: isSelected ? 'var(--color-accent)' : 'var(--text-muted)' }}>
                      {cmd.icon || '•'}
                    </span>
                    <div style={{ display: 'flex', flexDirection: 'column' }}>
                      <span style={{ fontSize: 'var(--text-sm)', fontWeight: isSelected ? 600 : 400, color: isSelected ? 'var(--text-primary)' : 'var(--text-secondary)' }}>
                        {cmd.label}
                      </span>
                      <span className="uppercase-tracking text-muted" style={{ fontSize: '9px' }}>
                        {cmd.category}
                      </span>
                    </div>
                  </div>

                  {cmd.shortcut && (
                    <kbd
                      className="font-mono"
                      style={{
                        fontSize: '10px',
                        padding: '2px 6px',
                        backgroundColor: 'var(--bg-canvas)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: '3px',
                        color: 'var(--text-muted)',
                      }}
                    >
                      {cmd.shortcut}
                    </kbd>
                  )}
                </div>
              );
            })
          )}
        </div>

        {/* Footer Navigation Hints */}
        <div
          style={{
            padding: '6px 12px',
            borderTop: '1px solid var(--border-subtle)',
            backgroundColor: 'var(--bg-canvas)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            fontSize: '10px',
            color: 'var(--text-muted)',
          }}
        >
          <div style={{ display: 'flex', gap: '12px' }}>
            <span>↑↓ Navigate</span>
            <span>↵ Select</span>
          </div>
          <span className="font-mono">AEROGUARD COMMAND HUB</span>
        </div>
      </div>
    </div>
  );
};
