import React, { useState } from 'react';
import { Navigate, useNavigate } from 'react-router-dom';
import { Button } from '../components/common/Button';
import { ErrorState } from '../components/common/ErrorState';
import { useAuth } from '../context/AuthContext';

export const LoginPage: React.FC = () => {
  const { user, login, isLoading } = useAuth();
  const [identifier, setIdentifier] = useState<string>('');
  const [password, setPassword] = useState<string>('');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);
  const navigate = useNavigate();

  // If already authenticated, redirect to operator overview
  if (user && !isLoading) {
    return <Navigate to="/app/overview" replace />;
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!identifier.trim() || !password) {
      setErrorMessage('Please provide both username/email and password.');
      return;
    }

    setIsSubmitting(true);
    setErrorMessage(null);

    try {
      await login({ identifier: identifier.trim(), password });
      navigate('/app/overview', { replace: true });
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Invalid credentials or backend unavailable';
      setErrorMessage(message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        minHeight: '100vh',
        width: '100vw',
        alignItems: 'center',
        justifyContent: 'center',
        backgroundColor: 'var(--bg-canvas)',
        padding: 'var(--space-md)',
      }}
    >
      <div
        className="tactical-panel"
        style={{
          width: '100%',
          maxWidth: '400px',
          border: '1px solid var(--border-medium)',
        }}
      >
        <div
          className="panel-header"
          style={{
            flexDirection: 'column',
            alignItems: 'flex-start',
            padding: 'var(--space-lg)',
            gap: '4px',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                width: '12px',
                height: '12px',
                backgroundColor: 'var(--color-accent)',
                borderRadius: '2px',
                display: 'inline-block',
              }}
            />
            <h1
              style={{
                fontSize: 'var(--text-lg)',
                fontWeight: 700,
                letterSpacing: '0.12em',
                color: 'var(--text-primary)',
                textTransform: 'uppercase',
                margin: 0,
              }}
            >
              AEROGUARD
            </h1>
          </div>
          <p
            className="uppercase-tracking"
            style={{ color: 'var(--text-muted)', fontSize: '10px', margin: 0 }}
          >
            Operator Console Authentication
          </p>
        </div>

        <form onSubmit={handleSubmit} className="panel-body" style={{ padding: 'var(--space-lg)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
          {errorMessage && (
            <ErrorState
              title="Authentication Failure"
              message={errorMessage}
            />
          )}

          <div>
            <label
              htmlFor="identifier"
              className="uppercase-tracking"
              style={{ display: 'block', marginBottom: 'var(--space-xs)', color: 'var(--text-secondary)' }}
            >
              Username or Email
            </label>
            <input
              id="identifier"
              type="text"
              className="tactical-input font-mono"
              value={identifier}
              onChange={(e) => setIdentifier(e.target.value)}
              placeholder="e.g. operator"
              autoComplete="username"
              disabled={isSubmitting}
              required
            />
          </div>

          <div>
            <label
              htmlFor="password"
              className="uppercase-tracking"
              style={{ display: 'block', marginBottom: 'var(--space-xs)', color: 'var(--text-secondary)' }}
            >
              Password
            </label>
            <input
              id="password"
              type="password"
              className="tactical-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="••••••••••••"
              autoComplete="current-password"
              disabled={isSubmitting}
              required
            />
          </div>

          <div style={{ marginTop: 'var(--space-sm)' }}>
            <Button
              type="submit"
              variant="primary"
              isLoading={isSubmitting}
              style={{ width: '100%', padding: '10px 16px' }}
            >
              Sign In to Console
            </Button>
          </div>

          <div
            style={{
              marginTop: 'var(--space-sm)',
              paddingTop: 'var(--space-sm)',
              borderTop: '1px solid var(--border-subtle)',
              textAlign: 'center',
            }}
          >
            <span
              className="font-mono"
              style={{ fontSize: '10px', color: 'var(--text-muted)' }}
            >
              DEFENSIVE COUNTER-UAS AWARENESS PLATFORM
            </span>
          </div>
        </form>
      </div>
    </div>
  );
};
