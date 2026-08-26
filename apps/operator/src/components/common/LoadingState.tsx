import React from 'react';

interface LoadingStateProps {
  message?: string;
  compact?: boolean;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = 'Loading operational telemetry...',
  compact = false,
}) => {
  if (compact) {
    return (
      <div style={{ display: 'inline-flex', alignItems: 'center', gap: '8px', color: 'var(--text-muted)', fontSize: 'var(--text-xs)' }}>
        <span className="technical-spinner" style={{ width: '12px', height: '12px', border: '2px solid var(--border-medium)', borderTopColor: 'var(--color-accent)', borderRadius: '50%', animation: 'spin 0.8s linear infinite', display: 'inline-block' }} />
        <span className="font-mono">{message}</span>
      </div>
    );
  }

  return (
    <div style={{ padding: 'var(--space-xl)', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', gap: 'var(--space-md)', color: 'var(--text-muted)' }}>
      <div
        style={{
          width: '28px',
          height: '28px',
          border: '3px solid var(--border-medium)',
          borderTopColor: 'var(--color-accent)',
          borderRadius: '50%',
          animation: 'spin 0.8s linear infinite',
        }}
      />
      <p className="font-mono text-sm uppercase-tracking">{message}</p>
      <style>{`
        @keyframes spin {
          0% { transform: rotate(0deg); }
          100% { transform: rotate(360deg); }
        }
      `}</style>
    </div>
  );
};
