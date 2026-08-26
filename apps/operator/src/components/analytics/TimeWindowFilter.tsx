import React, { useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';

interface TimeWindowFilterProps {
  /** Optional initial start date in ISO string (YYYY-MM-DD) */
  initialStart?: string;
  /** Optional initial end date in ISO string (YYYY-MM-DD) */
  initialEnd?: string;
  /** Callback when window changes; receives ISO strings or empty strings */
  onChange: (start: string, end: string) => void;
}

/**
 * Tiny UI component for selecting a start / end date window.
 * It validates that start <= end, updates the URL query parameters,
 * and notifies the parent via `onChange`.
 *
 * Accessibility: each input has an associated label and clear focus styles.
 */
export const TimeWindowFilter: React.FC<TimeWindowFilterProps> = ({
  initialStart = '',
  initialEnd = '',
  onChange,
}) => {
  const [searchParams, setSearchParams] = useSearchParams();

  const startParam = searchParams.get('from') ?? '';
  const endParam = searchParams.get('to') ?? '';

  // Initialise from URL if present, otherwise fallback to props.
  const startValue = startParam || initialStart;
  const endValue = endParam || initialEnd;

  // Sync changes back to URL & parent.
  const sync = (s: string, e: string) => {
    const newParams = new URLSearchParams(searchParams);
    if (s) newParams.set('from', s); else newParams.delete('from');
    if (e) newParams.set('to', e); else newParams.delete('to');
    setSearchParams(newParams);
    onChange(s, e);
  };

  const handleStartChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newStart = e.target.value;
    if (newStart && endValue && newStart > endValue) {
      // reject invalid range – keep previous value.
      return;
    }
    sync(newStart, endValue);
  };

  const handleEndChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newEnd = e.target.value;
    if (newEnd && startValue && newEnd < startValue) {
      return;
    }
    sync(startValue, newEnd);
  };

  // Effect to fire on mount in case URL already has params.
  useEffect(() => {
    if (startValue || endValue) {
      onChange(startValue, endValue);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  return (
    <div style={{ display: 'flex', gap: 'var(--space-sm)', alignItems: 'center' }}>
      <label style={{ display: 'flex', flexDirection: 'column', fontSize: 'var(--text-xs)' }}>
        From
        <input
          type="date"
          value={startValue}
          onChange={handleStartChange}
          className="tactical-input"
          style={{
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '4px',
            outline: 'none',
          }}
        />
      </label>
      <label style={{ display: 'flex', flexDirection: 'column', fontSize: 'var(--text-xs)' }}>
        To
        <input
          type="date"
          value={endValue}
          onChange={handleEndChange}
          className="tactical-input"
          style={{
            border: '1px solid var(--border-subtle)',
            borderRadius: 'var(--radius-sm)',
            padding: '4px',
            outline: 'none',
          }}
        />
      </label>
    </div>
  );
};
