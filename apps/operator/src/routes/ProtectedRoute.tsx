import React from 'react';
import { Navigate } from 'react-router-dom';
import { Card } from '../components/common/Card';
import { LoadingState } from '../components/common/LoadingState';
import { useAuth } from '../context/AuthContext';

interface ProtectedRouteProps {
  children: React.ReactNode;
  requiredPermission?: string;
  requiredAnyPermissions?: string[];
}

export const ProtectedRoute: React.FC<ProtectedRouteProps> = ({
  children,
  requiredPermission,
  requiredAnyPermissions,
}) => {
  const { user, isLoading, hasPermission, hasAnyPermission } = useAuth();

  if (isLoading) {
    return (
      <div
        style={{
          minHeight: '100vh',
          width: '100vw',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          backgroundColor: 'var(--bg-canvas)',
        }}
      >
        <LoadingState message="Verifying operator authorization session..." />
      </div>
    );
  }

  if (!user) {
    return <Navigate to="/login" replace />;
  }

  if (requiredPermission && !hasPermission(requiredPermission)) {
    return (
      <div style={{ padding: 'var(--space-xl)', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Card title="403 FORBIDDEN • ACCESS DENIED" style={{ maxWidth: '460px', width: '100%' }}>
          <div style={{ padding: 'var(--space-md) 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            <p style={{ color: 'var(--status-critical)', fontSize: 'var(--text-sm)', fontWeight: 600 }}>
              Insufficient Role Authority
            </p>
            <p className="text-muted text-xs">
              Your assigned roles do not grant the required permission: <code className="font-mono">{requiredPermission}</code>.
            </p>
            <p className="font-mono text-xs" style={{ color: 'var(--text-muted)', marginTop: '8px' }}>
              ACTOR: {user.username} • ASSIGNED ROLES: {user.roles.join(', ') || 'NONE'}
            </p>
          </div>
        </Card>
      </div>
    );
  }

  if (requiredAnyPermissions && !hasAnyPermission(requiredAnyPermissions)) {
    return (
      <div style={{ padding: 'var(--space-xl)', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Card title="403 FORBIDDEN • ACCESS DENIED" style={{ maxWidth: '460px', width: '100%' }}>
          <div style={{ padding: 'var(--space-md) 0', display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            <p style={{ color: 'var(--status-critical)', fontSize: 'var(--text-sm)', fontWeight: 600 }}>
              Insufficient Role Authority
            </p>
            <p className="text-muted text-xs">
              Your assigned roles require at least one of: <code className="font-mono">{requiredAnyPermissions.join(', ')}</code>.
            </p>
          </div>
        </Card>
      </div>
    );
  }

  return <>{children}</>;
};
