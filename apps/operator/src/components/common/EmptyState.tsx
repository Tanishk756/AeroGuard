import React from 'react';

interface EmptyStateProps {
  title?: string;
  description?: string;
  icon?: string;
  action?: React.ReactNode;
}

export const EmptyState: React.FC<EmptyStateProps> = ({
  title = 'No Telemetry Available',
  description = 'No operational records matched the active filter or query parameters.',
  icon = '◻',
  action,
}) => {
  return (
    <div
      style={{
        padding: 'var(--space-xl)',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        textAlign: 'center',
        color: 'var(--text-muted)',
        border: '1px dashed var(--border-subtle)',
        borderRadius: 'var(--radius-sm)',
        margin: 'var(--space-sm) 0',
      }}
    >
      <span style={{ fontSize: '24px', opacity: 0.5, marginBottom: 'var(--space-xs)' }}>{icon}</span>
      <h3 style={{ fontSize: 'var(--text-sm)', fontWeight: 600, color: 'var(--text-secondary)', textTransform: 'uppercase', letterSpacing: '0.04em' }}>
        {title}
      </h3>
      <p style={{ fontSize: 'var(--text-xs)', maxWidth: '360px', marginTop: '4px', color: 'var(--text-muted)' }}>
        {description}
      </p>
      {action && <div style={{ marginTop: 'var(--space-md)' }}>{action}</div>}
    </div>
  );
};
