import React from 'react';
import { Card } from '../components/common/Card';

interface ModulePlaceholderProps {
  moduleName: string;
  plannedStage: string;
  description: string;
}

export const ModulePlaceholder: React.FC<ModulePlaceholderProps> = ({
  moduleName,
  plannedStage,
  description,
}) => {
  return (
    <div style={{ padding: 'var(--space-md)', flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <Card
        title={moduleName.toUpperCase()}
        style={{ maxWidth: '520px', width: '100%', textAlign: 'center' }}
      >
        <div style={{ padding: 'var(--space-lg) var(--space-md)', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <span style={{ fontSize: '32px', color: 'var(--color-accent)' }}>◫</span>
          <h2 style={{ fontSize: 'var(--text-md)', textTransform: 'uppercase', letterSpacing: '0.08em', color: 'var(--text-primary)', margin: 0 }}>
            MODULE NOT AVAILABLE
          </h2>
          <p className="font-mono text-xs" style={{ color: 'var(--status-warning)' }}>
            PLANNED STAGE: {plannedStage}
          </p>
          <p style={{ fontSize: 'var(--text-sm)', color: 'var(--text-muted)', margin: '8px 0 0' }}>
            {description}
          </p>
          <div
            className="font-mono"
            style={{
              marginTop: 'var(--space-md)',
              padding: '6px 12px',
              backgroundColor: 'var(--bg-canvas)',
              borderRadius: 'var(--radius-sm)',
              fontSize: '11px',
              color: 'var(--text-muted)',
              border: '1px solid var(--border-subtle)',
            }}
          >
            AeroGuard Architectural Boundary — No stubbed or fake client-side logic.
          </div>
        </div>
      </Card>
    </div>
  );
};
