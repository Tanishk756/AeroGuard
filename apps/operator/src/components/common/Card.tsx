import React from 'react';

interface CardProps {
  title?: React.ReactNode;
  badge?: React.ReactNode;
  actions?: React.ReactNode;
  children: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
  bodyStyle?: React.CSSProperties;
}

export const Card: React.FC<CardProps> = ({
  title,
  badge,
  actions,
  children,
  className = '',
  style,
  bodyStyle,
}) => {
  return (
    <div className={`tactical-panel ${className}`} style={style}>
      {(title || badge || actions) && (
        <div className="panel-header">
          <div className="panel-title">
            {title}
            {badge}
          </div>
          {actions && <div className="panel-actions">{actions}</div>}
        </div>
      )}
      <div className="panel-body" style={bodyStyle}>
        {children}
      </div>
    </div>
  );
};
