import React from 'react';

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost';
  size?: 'sm' | 'md';
  isLoading?: boolean;
}

export const Button: React.FC<ButtonProps> = ({
  children,
  variant = 'secondary',
  size = 'md',
  isLoading = false,
  disabled = false,
  style,
  className = '',
  ...props
}) => {
  const baseStyle: React.CSSProperties = {
    display: 'inline-flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: '6px',
    fontFamily: 'inherit',
    fontWeight: 500,
    borderRadius: 'var(--radius-sm)',
    border: '1px solid transparent',
    cursor: disabled || isLoading ? 'not-allowed' : 'pointer',
    opacity: disabled || isLoading ? 0.6 : 1,
    transition: 'all var(--transition-fast)',
    textTransform: 'uppercase',
    letterSpacing: '0.04em',
  };

  const sizeStyle: React.CSSProperties =
    size === 'sm'
      ? { padding: '4px 8px', fontSize: 'var(--text-xs)' }
      : { padding: '7px 14px', fontSize: 'var(--text-sm)' };

  let variantStyle: React.CSSProperties = {};

  switch (variant) {
    case 'primary':
      variantStyle = {
        backgroundColor: 'var(--color-accent)',
        color: 'var(--text-inverse)',
        borderColor: 'var(--color-accent)',
        fontWeight: 600,
      };
      break;
    case 'danger':
      variantStyle = {
        backgroundColor: 'var(--status-critical-bg)',
        color: '#fca5a5',
        borderColor: 'var(--status-critical-border)',
      };
      break;
    case 'ghost':
      variantStyle = {
        backgroundColor: 'transparent',
        color: 'var(--text-secondary)',
        borderColor: 'transparent',
      };
      break;
    case 'secondary':
    default:
      variantStyle = {
        backgroundColor: 'var(--bg-surface-elevated)',
        color: 'var(--text-primary)',
        borderColor: 'var(--border-medium)',
      };
      break;
  }

  return (
    <button
      disabled={disabled || isLoading}
      style={{ ...baseStyle, ...sizeStyle, ...variantStyle, ...style }}
      className={`tactical-btn ${className}`}
      {...props}
    >
      {isLoading && (
        <span
          style={{
            width: '10px',
            height: '10px',
            border: '2px solid currentColor',
            borderTopColor: 'transparent',
            borderRadius: '50%',
            animation: 'spin 0.8s linear infinite',
            display: 'inline-block',
          }}
        />
      )}
      {children}
    </button>
  );
};
