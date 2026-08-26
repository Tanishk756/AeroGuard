import React from 'react';

interface ErrorStateProps {
  title?: string;
  message?: string;
  errorCode?: string;
  correlationId?: string;
  onRetry?: () => void;
}

export const ErrorState: React.FC<ErrorStateProps> = ({
  title = 'Operational Query Failure',
  message = 'An unexpected error occurred while communicating with backend services.',
  errorCode,
  correlationId,
  onRetry,
}) => {
  return (
    <div
      style={{
        padding: 'var(--space-md)',
        backgroundColor: 'var(--status-critical-bg)',
        border: '1px solid var(--status-critical-border)',
        borderRadius: 'var(--radius-sm)',
        color: '#fca5a5',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-xs)',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <strong style={{ fontSize: 'var(--text-sm)', display: 'flex', alignItems: 'center', gap: '6px' }}>
          <span>⚠</span> {title}
        </strong>
        {errorCode && (
          <span className="font-mono" style={{ fontSize: 'var(--text-xs)', opacity: 0.85 }}>
            CODE: {errorCode}
          </span>
        )}
      </div>
      <p style={{ fontSize: 'var(--text-sm)', margin: '4px 0', color: 'var(--text-secondary)' }}>{message}</p>
      {correlationId && (
        <p className="font-mono text-xs" style={{ color: 'var(--text-muted)' }}>
          CORRELATION-ID: {correlationId}
        </p>
      )}
      {onRetry && (
        <div style={{ marginTop: 'var(--space-xs)' }}>
          <button
            onClick={onRetry}
            style={{
              padding: '2px 8px',
              fontSize: 'var(--text-xs)',
              background: 'rgba(239, 68, 68, 0.2)',
              borderColor: 'var(--status-critical)',
              color: '#fca5a5',
              cursor: 'pointer',
            }}
          >
            Retry Request
          </button>
        </div>
      )}
    </div>
  );
};
