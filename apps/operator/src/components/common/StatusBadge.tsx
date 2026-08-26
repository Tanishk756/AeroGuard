import React from 'react';

export type BadgeStatus =
  | 'NORMAL'
  | 'ACTIVE'
  | 'WARNING'
  | 'CRITICAL'
  | 'OFFLINE'
  | 'STALE'
  | 'LOST'
  | 'ARCHIVED'
  | 'OPEN'
  | 'ACKNOWLEDGED'
  | 'RESOLVED'
  | 'HIGH'
  | 'MEDIUM'
  | 'LOW'
  | 'INFO'
  | 'UNKNOWN';

interface StatusBadgeProps {
  status: string | BadgeStatus;
  label?: string;
  className?: string;
}

export const StatusBadge: React.FC<StatusBadgeProps> = ({ status, label, className = '' }) => {
  const norm = (status || 'UNKNOWN').toUpperCase();

  let variant = 'status-offline';
  let symbol = '•';

  switch (norm) {
    case 'ACTIVE':
    case 'NORMAL':
    case 'OK':
    case 'RESOLVED':
      variant = 'status-success';
      symbol = '●';
      break;
    case 'WARNING':
    case 'STALE':
    case 'MEDIUM':
    case 'ACKNOWLEDGED':
    case 'DEGRADED':
      variant = 'status-warning';
      symbol = '▲';
      break;
    case 'CRITICAL':
    case 'HIGH':
    case 'LOST':
    case 'OPEN':
    case 'ERROR':
      variant = 'status-critical';
      symbol = '■';
      break;
    case 'INFO':
    case 'SIMULATION':
    case 'NEW':
    case 'LOW':
      variant = 'status-info';
      symbol = '◆';
      break;
    case 'OFFLINE':
    case 'INACTIVE':
    case 'ARCHIVED':
    case 'MAINTENANCE':
    case 'UNKNOWN':
    default:
      variant = 'status-offline';
      symbol = '○';
      break;
  }

  return (
    <span className={`status-pill ${variant} ${className}`} title={`Status: ${norm}`}>
      <span className="status-dot" aria-hidden="true" />
      <span className="sr-indicator" style={{ marginRight: '3px', fontSize: '9px' }}>{symbol}</span>
      <span>{label || norm}</span>
    </span>
  );
};
