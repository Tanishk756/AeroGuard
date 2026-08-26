import React from 'react';
import { NavLink } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';

interface NavItemConfig {
  path: string;
  label: string;
  icon: string;
  requiredPermission?: string;
  requiredAnyPermissions?: string[];
}

export const AppSidebar: React.FC = () => {
  const { hasPermission, hasAnyPermission } = useAuth();

  const primaryNavItems: NavItemConfig[] = [
    {
      path: '/app/overview',
      label: 'Overview',
      icon: '⊞',
    },
    {
      path: '/app/tracks',
      label: 'Tracks',
      icon: '◎',
      requiredPermission: 'tracks.read',
    },
    {
      path: '/app/sensors',
      label: 'Sensors',
      icon: '⋉',
      requiredPermission: 'sensors.read',
    },
    {
      path: '/app/alerts',
      label: 'Alerts',
      icon: '▲',
      requiredPermission: 'alerts.read',
    },
    {
      path: '/app/threats',
      label: 'Threats',
      icon: '⚡',
      requiredPermission: 'threats.read',
    },
    {
      path: '/app/geofences',
      label: 'Defense Zones',
      icon: '⛊',
      requiredAnyPermissions: ['scenarios.read', 'scenarios.create', 'scenarios.update', 'scenarios.delete'],
    },
    {
      path: '/app/scenarios',
      label: 'Scenarios',
      icon: '⚙',
      requiredAnyPermissions: ['scenarios.read', 'scenarios.run', 'scenarios.create'],
    },
  ];

  const analysisNavItems: NavItemConfig[] = [
    {
      path: '/app/history',
      label: 'History & Logs',
      icon: '◷',
      requiredAnyPermissions: ['sensors.read', 'tracks.read', 'alerts.read', 'threats.read'],
    },
    {
      path: '/app/replay',
      label: 'Replay Analysis',
      icon: '⏯',
      requiredAnyPermissions: ['scenarios.read', 'tracks.read', 'scenarios.run'],
    },
    {
      path: '/app/analytics',
      label: 'Analytics',
      icon: '📊',
      requiredAnyPermissions: ['sensors.read', 'tracks.read', 'alerts.read', 'threats.read'],
    },
  ];

  const governanceNavItems: NavItemConfig[] = [
    {
      path: '/app/audit',
      label: 'Security Audit',
      icon: '🔒',
      requiredPermission: 'audit.read',
    },
    {
      path: '/app/rbac',
      label: 'RBAC Roles',
      icon: '🛡',
      requiredAnyPermissions: ['roles.read', 'permissions.read', 'roles.create', 'roles.update', 'roles.delete', 'roles.assign'],
    },
    {
      path: '/app/diagnostics',
      label: 'Diagnostics',
      icon: '🩺',
      requiredPermission: 'system.read',
    },
  ];

  const filterVisible = (item: NavItemConfig) => {
    if (item.requiredPermission && !hasPermission(item.requiredPermission)) {
      return false;
    }
    if (item.requiredAnyPermissions && !hasAnyPermission(item.requiredAnyPermissions)) {
      return false;
    }
    return true;
  };

  return (
    <aside
      style={{
        width: '200px',
        backgroundColor: 'var(--bg-surface)',
        borderRight: '1px solid var(--border-medium)',
        display: 'flex',
        flexDirection: 'column',
        padding: 'var(--space-md) var(--space-xs)',
        gap: 'var(--space-md)',
        userSelect: 'none',
        overflowY: 'auto',
      }}
    >
      {/* Primary Operations */}
      <div>
        <div
          className="uppercase-tracking text-muted"
          style={{ padding: '0 var(--space-sm) var(--space-xs)', fontSize: '10px' }}
        >
          Operations
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {primaryNavItems.filter(filterVisible).map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `tactical-nav-link ${isActive ? 'active' : ''}`
              }
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px var(--space-sm)',
                borderRadius: 'var(--radius-sm)',
                color: isActive ? 'var(--color-accent)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--bg-surface-active)' : 'transparent',
                textDecoration: 'none',
                fontSize: 'var(--text-sm)',
                fontWeight: isActive ? 600 : 400,
                borderLeft: isActive ? '3px solid var(--color-accent)' : '3px solid transparent',
                transition: 'all var(--transition-fast)',
              })}
            >
              <span style={{ fontSize: '14px', width: '16px', textAlign: 'center' }}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Historical & Analytics */}
      <div>
        <div
          className="uppercase-tracking text-muted"
          style={{ padding: '0 var(--space-sm) var(--space-xs)', fontSize: '10px' }}
        >
          Review & Analysis
        </div>
        <nav style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          {analysisNavItems.filter(filterVisible).map((item) => (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `tactical-nav-link ${isActive ? 'active' : ''}`
              }
              style={({ isActive }) => ({
                display: 'flex',
                alignItems: 'center',
                gap: '8px',
                padding: '6px var(--space-sm)',
                borderRadius: 'var(--radius-sm)',
                color: isActive ? 'var(--color-accent)' : 'var(--text-secondary)',
                backgroundColor: isActive ? 'var(--bg-surface-active)' : 'transparent',
                textDecoration: 'none',
                fontSize: 'var(--text-sm)',
                fontWeight: isActive ? 600 : 400,
                borderLeft: isActive ? '3px solid var(--color-accent)' : '3px solid transparent',
                transition: 'all var(--transition-fast)',
              })}
            >
              <span style={{ fontSize: '14px', width: '16px', textAlign: 'center' }}>{item.icon}</span>
              <span>{item.label}</span>
            </NavLink>
          ))}
        </nav>
      </div>

      {/* Governance & Administration */}
      {governanceNavItems.some(filterVisible) && (
        <div>
          <div
            className="uppercase-tracking text-muted"
            style={{ padding: '0 var(--space-sm) var(--space-xs)', fontSize: '10px' }}
          >
            Governance & Admin
          </div>
          <nav style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
            {governanceNavItems.filter(filterVisible).map((item) => (
              <NavLink
                key={item.path}
                to={item.path}
                className={({ isActive }) =>
                  `tactical-nav-link ${isActive ? 'active' : ''}`
                }
                style={({ isActive }) => ({
                  display: 'flex',
                  alignItems: 'center',
                  gap: '8px',
                  padding: '6px var(--space-sm)',
                  borderRadius: 'var(--radius-sm)',
                  color: isActive ? 'var(--color-accent)' : 'var(--text-secondary)',
                  backgroundColor: isActive ? 'var(--bg-surface-active)' : 'transparent',
                  textDecoration: 'none',
                  fontSize: 'var(--text-sm)',
                  fontWeight: isActive ? 600 : 400,
                  borderLeft: isActive ? '3px solid var(--color-accent)' : '3px solid transparent',
                  transition: 'all var(--transition-fast)',
                })}
              >
                <span style={{ fontSize: '14px', width: '16px', textAlign: 'center' }}>{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </div>
      )}
    </aside>
  );
};
